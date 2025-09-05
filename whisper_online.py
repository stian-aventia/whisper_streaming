#!/usr/bin/env python3
##
## This code and all components (c) Copyright 2006 - 2025, Wowza Media Systems, LLC. All rights reserved.
## This code is licensed pursuant to the Wowza Public License version 1.0, available at www.wowza.com/legal.
##
import io
import logging
import math
import os
import sys
import time

import numpy as np
import soundfile as sf  # still needed for OpenAI API buffer encoding

logger = logging.getLogger(__name__)
SAMPLING_RATE = 16000  # default

"""Core ASR backend classes and streaming processor (server usage)."""

# Whisper backend


class ASRBase:

    transcription_separator = " "  # join transcribe words with this character (" " for whisper_timestamped,
    # "" for faster-whisper because it emits the spaces when neeeded)

    def __init__(self, lan, model=None, cache_dir=None, logfile=sys.stderr, use_gpu=False):
        self.logfile = logfile

        self.transcribe_kargs = {}
        if lan == "auto":
            self.original_language = None
        else:
            self.original_language = lan

        self.model = self.load_model(model, cache_dir, use_gpu)

    def load_model(self, model, cache_dir, use_gpu):
        raise NotImplementedError("must be implemented in the child class")

    def transcribe(self, audio, init_prompt=""):
        raise NotImplementedError("must be implemented in the child class")

    def use_vad(self):
        raise NotImplementedError("must be implemented in the child class")


class FasterWhisperASR(ASRBase):
    """Uses faster-whisper library as the backend. Works much faster, appx 4-times (in offline mode). For GPU, it requires installation with a specific CUDNN version."""

    transcription_separator = ""

    def load_model(self, model=None, cache_dir=None, use_gpu=False):
        from faster_whisper import WhisperModel

        if model is None:
            raise ValueError("--model must be specified (builtin size, path, or HF repo id)")

        if use_gpu:
            # this worked fast and reliably on NVIDIA L40
            model = WhisperModel(model, device="cuda", compute_type="float16", download_root=cache_dir)

            # or run on GPU with INT8
            # tested: the transcripts were different, probably worse than with FP16, and it was slightly (appx 20%) slower
            # model = WhisperModel(model_size_or_path, device="cuda", compute_type="int8_float16", download_root=cache_dir)
        else:
            # or run on CPU with INT8
            # tested: works, but slow, appx 10-times than cuda FP16
            model = WhisperModel(model, device="cpu", compute_type="int8", download_root=cache_dir)
        return model

    def transcribe(self, audio, init_prompt=""):

        # tested: beam_size=5 is faster and better than 1 (on one 200 second document from En ESIC, min chunk 0.01)
        segments, info = self.model.transcribe(
            audio,
            language=self.original_language,
            initial_prompt=init_prompt,
            beam_size=5,
            word_timestamps=True,
            condition_on_previous_text=True,
            **self.transcribe_kargs,
        )
        # print(info)  # info contains language detection result

        return list(segments)

    def ts_words(self, segments):
        o = []
        for segment in segments:
            for word in segment.words:
                if segment.no_speech_prob > 0.9:
                    continue
                # not stripping the spaces -- should not be merged with them!
                w = word.word
                t = (word.start, word.end, w)
                o.append(t)
        return o

    def segments_end_ts(self, res):
        return [s.end for s in res]

    def use_vad(self):
        self.transcribe_kargs["vad_filter"] = True

    def set_translate_task(self):
        self.transcribe_kargs["task"] = "translate"


class OpenaiApiASR(ASRBase):
    """Uses OpenAI's Whisper API for audio transcription."""

    def __init__(self, lan=None, temperature=0, logfile=sys.stderr):
        self.logfile = logfile

        self.modelname = "whisper-1"
        self.original_language = None if lan == "auto" else lan  # ISO-639-1 language code
        self.response_format = "verbose_json"
        self.temperature = temperature

        self.load_model()

        self.use_vad_opt = False

        # reset the task in set_translate_task
        self.task = "transcribe"

    def load_model(self, *args, **kwargs):
        from openai import OpenAI

        self.client = OpenAI()

        self.transcribed_seconds = 0  # for logging how many seconds were processed by API, to know the cost

    def ts_words(self, segments):
        no_speech_segments = []
        if self.use_vad_opt:
            for segment in segments.segments:
                # TODO: threshold can be set from outside
                if segment["no_speech_prob"] > 0.8:
                    no_speech_segments.append((segment.get("start"), segment.get("end")))

        o = []
        for word in segments.words:
            start = word.start
            end = word.end
            if any(s[0] <= start <= s[1] for s in no_speech_segments):
                # print("Skipping word", word.get("word"), "because it's in a no-speech segment")
                continue
            o.append((start, end, word.word))
        return o

    def segments_end_ts(self, res):
        return [s.end for s in res.words]

    def transcribe(self, audio_data, prompt=None, *args, **kwargs):
        # Write the audio data to a buffer
        buffer = io.BytesIO()
        buffer.name = "temp.wav"
        sf.write(buffer, audio_data, samplerate=SAMPLING_RATE, format="WAV", subtype="PCM_16")
        buffer.seek(0)  # Reset buffer's position to the beginning

        self.transcribed_seconds += math.ceil(len(audio_data) / SAMPLING_RATE)  # it rounds up to the whole seconds

        params = {
            "model": self.modelname,
            "file": buffer,
            "response_format": self.response_format,
            "temperature": self.temperature,
            "timestamp_granularities": ["word", "segment"],
        }
        if self.task != "translate" and self.original_language:
            params["language"] = self.original_language
        if prompt:
            params["prompt"] = prompt

        if self.task == "translate":
            proc = self.client.audio.translations
        else:
            proc = self.client.audio.transcriptions

        # Process transcription/translation
        transcript = proc.create(**params)
        logger.debug(f"OpenAI API processed accumulated {self.transcribed_seconds} seconds")

        return transcript

    def use_vad(self):
        self.use_vad_opt = True

    def set_translate_task(self):
        self.task = "translate"


class HypothesisBuffer:

    def __init__(self, logfile=sys.stderr):
        self.commited_in_buffer = []
        self.buffer = []
        self.new = []

        self.last_commited_time = 0
        self.last_commited_word = None

        self.logfile = logfile

    def insert(self, new, offset):
        # compare self.commited_in_buffer and new. It inserts only the words in new that extend the commited_in_buffer, it means they are roughly behind last_commited_time and new in content
        # the new tail is added to self.new

        new = [(a + offset, b + offset, t) for a, b, t in new]
        self.new = [(a, b, t) for a, b, t in new if a > self.last_commited_time - 0.1]

        if len(self.new) >= 1:
            a, b, t = self.new[0]
            if abs(a - self.last_commited_time) < 1:
                if self.commited_in_buffer:
                    # it's going to search for 1, 2, ..., 5 consecutive words (n-grams) that are identical in commited and new. If they are, they're dropped.
                    cn = len(self.commited_in_buffer)
                    nn = len(self.new)
                    for i in range(1, min(min(cn, nn), 5) + 1):  # 5 is the maximum
                        c = " ".join([self.commited_in_buffer[-j][2] for j in range(1, i + 1)][::-1])
                        tail = " ".join(self.new[j - 1][2] for j in range(1, i + 1))
                        if c == tail:
                            words = []
                            for j in range(i):
                                words.append(repr(self.new.pop(0)))
                            words_msg = " ".join(words)
                            logger.debug(f"removing last {i} words: {words_msg}")
                            break

    def flush(self):
        # returns commited chunk = the longest common prefix of 2 last inserts.

        commit = []
        while self.new:
            na, nb, nt = self.new[0]

            if len(self.buffer) == 0:
                break

            if nt == self.buffer[0][2]:
                commit.append((na, nb, nt))
                self.last_commited_word = nt
                self.last_commited_time = nb
                self.buffer.pop(0)
                self.new.pop(0)
            else:
                break
        self.buffer = self.new
        self.new = []
        self.commited_in_buffer.extend(commit)
        return commit

    def pop_commited(self, time):
        while self.commited_in_buffer and self.commited_in_buffer[0][1] <= time:
            self.commited_in_buffer.pop(0)

    def complete(self):
        return self.buffer


# Fixed trimming threshold (seconds) for completed segments.
# Rationale: 15s provides a stable context window larger than the target end-to-end latency (~10s delay use case)
# while keeping memory low (< ~1MB float32 PCM) and limiting re-transcription span. This stays internal and
# unconfigurable to preserve deterministic behaviour / protocol timing semantics.
SEGMENT_TRIM_SEC = 15  # DO NOT expose as CLI/env without explicit approval.


class OnlineASRProcessor:

    def __init__(self, asr, logfile=sys.stderr):
        """Simplified processor: always segment-based trimming with fixed 15s window.
        asr: backend ASR instance
        logfile: stream for logging
        """
        self.asr = asr
        self.logfile = logfile
        self.init()

    def init(self, offset=None):
        """run this when starting or restarting processing"""
        self.audio_buffer = np.array([], dtype=np.float32)
        self.transcript_buffer = HypothesisBuffer(logfile=self.logfile)
        self.buffer_time_offset = 0
        if offset is not None:
            self.buffer_time_offset = offset
        self.transcript_buffer.last_commited_time = self.buffer_time_offset
        self.commited = []

    def insert_audio_chunk(self, audio):
        self.audio_buffer = np.append(self.audio_buffer, audio)

    def prompt(self):
        """Returns a tuple: (prompt, context), where "prompt" is a 200-character suffix of commited text that is inside of the scrolled away part of audio buffer.
        "context" is the commited text that is inside the audio buffer. It is transcribed again and skipped. It is returned only for debugging and logging reasons.
        """
        k = max(0, len(self.commited) - 1)
        while k > 0 and self.commited[k - 1][1] > self.buffer_time_offset:
            k -= 1

        p = self.commited[:k]
        p = [t for _, _, t in p]
        prompt = []
        l = 0
        while p and l < 200:  # 200 characters prompt size
            x = p.pop(-1)
            l += len(x) + 1
            prompt.append(x)
        non_prompt = self.commited[k:]
        return self.asr.transcription_separator.join(prompt[::-1]), self.asr.transcription_separator.join(
            t for _, _, t in non_prompt
        )

    def process_iter(self):
        """Runs on the current audio buffer.
        Returns: a tuple (beg_timestamp, end_timestamp, "text"), or (None, None, "").
        The non-emty text is confirmed (committed) partial transcript.
        """

        prompt, non_prompt = self.prompt()
        logger.debug(f"PROMPT: {prompt}")
        logger.debug(f"CONTEXT: {non_prompt}")
        logger.debug(
            f"transcribing {len(self.audio_buffer)/SAMPLING_RATE:2.2f} seconds from {self.buffer_time_offset:2.2f}"
        )
        res = self.asr.transcribe(self.audio_buffer, init_prompt=prompt)

        # transform to [(beg,end,"word1"), ...]
        tsw = self.asr.ts_words(res)

        self.transcript_buffer.insert(tsw, self.buffer_time_offset)
        o = self.transcript_buffer.flush()
        self.commited.extend(o)
        completed = self.to_flush(o)
        logger.debug(f">>>>COMPLETE NOW: {completed}")
        the_rest = self.to_flush(self.transcript_buffer.complete())
        logger.debug(f"INCOMPLETE: {the_rest}")

        # segment-based trimming only
        if len(self.audio_buffer) / SAMPLING_RATE > SEGMENT_TRIM_SEC:
            self.chunk_completed_segment(res)
            logger.debug("chunking segment")

        logger.debug(f"len of buffer now: {len(self.audio_buffer)/SAMPLING_RATE:2.2f}")
        return self.to_flush(o)

    def chunk_completed_segment(self, res):
        if self.commited == []:
            return

        ends = self.asr.segments_end_ts(res)

        t = self.commited[-1][1]

        if len(ends) > 1:

            e = ends[-2] + self.buffer_time_offset
            while len(ends) > 2 and e > t:
                ends.pop(-1)
                e = ends[-2] + self.buffer_time_offset
            if e <= t:
                logger.debug(f"--- segment chunked at {e:2.2f}")
                self.chunk_at(e)
            else:
                logger.debug(f"--- last segment not within commited area")
        else:
            logger.debug(f"--- not enough segments to chunk")

    def chunk_at(self, time):
        """trims the hypothesis and audio buffer at "time" """
        self.transcript_buffer.pop_commited(time)
        cut_seconds = time - self.buffer_time_offset
        self.audio_buffer = self.audio_buffer[int(cut_seconds * SAMPLING_RATE) :]
        self.buffer_time_offset = time

    def finish(self):
        """Flush the incomplete text when the whole processing ends.
        Returns: the same format as self.process_iter()
        """
        o = self.transcript_buffer.complete()
        f = self.to_flush(o)
        logger.debug(f"last, noncommited: {f}")
        self.buffer_time_offset += len(self.audio_buffer) / SAMPLING_RATE
        return f

    def to_flush(
        self,
        sentences,
        separator=None,
        offset=0,
    ):
        # concatenates the timestamped words or sentences into one sequence that is flushed in one line
        # sents: [(beg1, end1, "sentence1"), ...] or [] if empty
        # return: (beg1,end-of-last-sentence,"concatenation of sentences") or (None, None, "") if empty
        if separator is None:
            separator = self.asr.transcription_separator
        t = separator.join(s[2] for s in sentences)
        if len(sentences) == 0:
            b = None
            e = None
        else:
            b = offset + sentences[0][0]
            e = offset + sentences[-1][1]
        return (b, e, t)


def add_shared_args(parser):
    """Shared args for server.
    parser: argparse.ArgumentParser object
    """
    parser.add_argument(
        "--min-chunk-size",
        type=float,
        default=1.0,
        help="Minimum audio chunk size in seconds. It waits up to this time to do processing. If the processing takes shorter time, it waits, otherwise it processes the whole segment that was received by this time.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="large-v2",
        help="Model identifier: builtin size (tiny, base, small, medium, large-*), local filesystem path, OR HuggingFace repo id (e.g. NbAiLab/nb-whisper-large).",
    )
    parser.add_argument(
        "--model_cache_dir",
        type=str,
        default=None,
        help="Cache directory for downloaded models (HuggingFace / faster-whisper).",
    )
    parser.add_argument(
        "--lan",
        "--language",
        type=str,
        default="auto",
        help="Source language code, e.g. en,de,cs, or 'auto' for language detection.",
    )
    parser.add_argument(
        "--task", type=str, default="transcribe", choices=["transcribe", "translate"], help="Transcribe or translate."
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="faster-whisper",
        choices=["faster-whisper", "openai-api"],
        help="Backend: faster-whisper (local) or openai-api (remote).",
    )
    parser.add_argument(
        "--vad", action="store_true", default=True, help="Use VAD = voice activity detection (default: enabled)."
    )
    parser.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the log level",
        default="DEBUG",
    )
    parser.add_argument("--sampling_rate", type=int, default=16000)
    parser.add_argument(
        "--disable_gpu", action="store_true", default=False, help="Force disable GPU even if USE_GPU env is set"
    )


def asr_factory(args, logfile=sys.stderr):
    """
    Creates and configures an ASR and ASR Online instance based on the specified backend and arguments.
    """
    backend = args.backend
    if backend == "openai-api":
        asr = OpenaiApiASR(lan=args.lan)
    else:  # faster-whisper
        model = args.model
        # Auto GPU: if --disable_gpu set -> CPU; else detect CUDA device count.
        if args.disable_gpu:
            use_gpu = False
            logger.info("GPU disabled (flag)")
        else:
            use_gpu = False
            try:
                import ctranslate2

                count = ctranslate2.get_cuda_device_count()
            except Exception:
                count = 0
                logger.info("CUDA detection failed; using CPU")
            if count > 0:
                use_gpu = True
                plural = "s" if count != 1 else ""
                logger.info(f"GPU auto-detected ({count} CUDA device{plural})")
            else:
                logger.info("No CUDA devices detected; using CPU")
        t = time.time()
        cache_note = f" (cache: {args.model_cache_dir})" if args.model_cache_dir else ""
        logger.info(f"Loading Whisper {model} model for {args.lan}{cache_note}...")
        asr = FasterWhisperASR(model=model, lan=args.lan, cache_dir=args.model_cache_dir, use_gpu=use_gpu)
        e = time.time()
        logger.info(f"done. It took {round(e-t,2)} seconds.")

    # Apply common configurations
    if getattr(args, "vad", False):  # Checks if VAD argument is present and True
        logger.info("Setting VAD filter")
        asr.use_vad()

    language = args.lan
    if args.task == "translate":
        asr.set_translate_task()
        tgt_language = "en"  # Whisper translates into English
    else:
        tgt_language = language  # Whisper transcribes in this language

    # Create the OnlineASRProcessor
    online = OnlineASRProcessor(asr, logfile=logfile)

    return asr, online


def set_logging(args, logger, other="_server"):
    logging.basicConfig(format="%(levelname)s\t%(message)s")  # format='%(name)s
    logger.setLevel(args.log_level)
    logging.getLogger("whisper_online" + other).setLevel(args.log_level)
