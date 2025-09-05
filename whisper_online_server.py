#!/usr/bin/env python3
from whisper_online import *

import sys
import argparse
import os
import logging
import warnings
import numpy as np
import signal
import datetime
import json
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Suppress noisy pkg_resources deprecation warning (ctranslate2 dependency path)
# Toggle with SUPPRESS_PKG_RES_WARN=0 to re-enable.
if os.environ.get("SUPPRESS_PKG_RES_WARN", "1") == "1":
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"pkg_resources"
    )
parser = argparse.ArgumentParser()

# server options
parser.add_argument("--host", type=str, default='localhost')
parser.add_argument("--port", type=int, default=3000)

# options from whisper_online
add_shared_args(parser)
args = parser.parse_args()

set_logging(args,logger,other="")

running=True
server_socket = None  # will be set after socket creation
shutdown_logged = False
# setting whisper object by args 

SAMPLING_RATE = args.sampling_rate
# Removed unused local aliases (size, min_chunk) to reduce namespace noise.
language = args.lan
asr, online = asr_factory(args)

# Sanity warning: if min_chunk_size exceeds fixed segment trim window (15s),
# initial transcripts may be delayed indefinitely. Log once.
try:
    from whisper_online import SEGMENT_TRIM_SEC as _SEGMENT_TRIM_SEC
except Exception:
    _SEGMENT_TRIM_SEC = 15  # fallback (should not differ)
if args.min_chunk_size > _SEGMENT_TRIM_SEC:
    logger.warning(
        f"Configured --min-chunk-size ({args.min_chunk_size}s) exceeds internal segment trim window "
        f"({_SEGMENT_TRIM_SEC}s); this can delay first transcript emission. Consider lowering it."
    )

# Warm-up: run a short silent buffer through model so first real chunk is faster
try:
    if args.backend == 'faster-whisper':
        silent = np.zeros(int(SAMPLING_RATE * 0.5), dtype=np.float32)  # 0.5s silence
        asr.transcribe(silent)
        logger.info("Model warm-up with generated silence complete.")
    else:
        logger.debug("Skipping local warm-up for non local backend.")
except Exception as e:
    logger.warning(f"Warm-up failed (continuing without): {e}")


######### Server objects

import line_packet
import socket

# ---- Phase 6 internal constants & sentinels (no external behaviour change) ----
NO_DATA_YET = object()       # temporary absence of data (timeout)
STREAM_ENDED = object()      # client closed connection / reset
# CONN_RECV_TIMEOUT_SEC:
#  - Per-connection socket timeout used only to periodically break out of a blocking recv()
#    so we can check the global 'running' flag (Ctrl+C / SIGTERM) and then continue waiting for audio.
#  - On timeout we return the NO_DATA_YET sentinel and DO NOT close or alter the connection.
#    This is NOT an inactivity threshold and will never end the client session by itself.
#  - Actual end-of-stream is only when recv() returns b'' (orderly close) or raises ConnectionResetError,
#    which we map to STREAM_ENDED.
#  - Lower values give faster shutdown responsiveness but increase wakeups; higher values delay Ctrl+C.
#    1.0s is a compromise (≤1s worst-case shutdown delay) without unnecessary CPU spin.
CONN_RECV_TIMEOUT_SEC = 1.0  # per-connection recv timeout (responsiveness only; no auto-shutdown)

# Oversized packet guard (Phase 5): configurable threshold (default 5MB)
MAX_SINGLE_RECV_BYTES = int(os.environ.get("MAX_SINGLE_RECV_BYTES", str(5 * 1024 * 1024)))

# Packet size override (micro-improvement): allow tuning recv buffer without code change.
# Default keeps prior behaviour (5 minutes @ 16kHz 32000 bytes/sec * 5 * 60).
DEFAULT_PACKET_SIZE_BYTES = 32000 * 5 * 60
PACKET_SIZE_BYTES = int(os.environ.get("PACKET_SIZE_BYTES", str(DEFAULT_PACKET_SIZE_BYTES)))

class Connection:
    '''it wraps conn object'''
    # Previously fixed at 32000*5*60; now overridable via PACKET_SIZE_BYTES env (same default).
    PACKET_SIZE = PACKET_SIZE_BYTES  # 5 minutes buffer @16kHz (was hard-coded 32000*5*60)

    def __init__(self, conn):
        self.conn = conn
        self.last_line = ""
        # Use timeout to distinguish inactivity from shutdown; keeps loop responsive
        self.conn.settimeout(CONN_RECV_TIMEOUT_SEC)

    def send(self, line):
        '''it doesn't send the same line twice, because it was problematic in online-text-flow-events'''
        if line == self.last_line:
            return
        line_packet.send_one_line(self.conn, line)
        self.last_line = line

    def non_blocking_receive_audio(self):
        """Receive up to PACKET_SIZE bytes.
        Returns:
          bytes: normal data (len>0)
          NO_DATA_YET: timeout with no data (socket still open)
          STREAM_ENDED: remote closed/reset
        """
        try:
            r = self.conn.recv(self.PACKET_SIZE)
            if r == b"":  # remote orderly shutdown
                return STREAM_ENDED
            if r and len(r) > MAX_SINGLE_RECV_BYTES:
                logger.warning(
                    f"Oversized audio packet received: {len(r)/1024/1024:.2f} MB (threshold {MAX_SINGLE_RECV_BYTES/1024/1024:.2f} MB)"
                )
            return r
        except socket.timeout:
            return NO_DATA_YET
        except ConnectionResetError:
            return STREAM_ENDED


# (Removed unused legacy 'io' import.)

# Direct PCM16LE -> float32 decoder (Phase 5 optimization)
def pcm16le_bytes_to_float32(raw_bytes: Optional[Union[bytes, bytearray, memoryview]]) -> Optional[np.ndarray]:
    """Convert little-endian signed 16-bit PCM bytes to float32 array in [-1,1].
    - Accepts bytes-like object; returns np.ndarray or None if empty/invalid.
    - Drops trailing odd byte (logs at DEBUG level per occurrence).
    """
    if not raw_bytes:
        return None
    ln = len(raw_bytes)
    if ln % 2 == 1:  # odd length – drop last byte
        logger.debug(f"Dropping trailing odd byte in audio packet len={ln}")
        raw_bytes = raw_bytes[:-1]
    if not raw_bytes:
        return None
    # astype produces a float32 copy; in-place scaling avoids an extra temporary from division
    audio = np.frombuffer(raw_bytes, dtype='<i2').astype(np.float32)
    audio *= (1.0/32768.0)
    return audio

# wraps socket and ASR object, and serves one client connection. 
# next client should be served by a new instance of this object
class ServerProcessor:

    def timedelta_to_webvtt(self,delta):
    #Format this:0:00:00
    #Format this:0:00:09.480000
      parts = delta.split(":")
      parts2 = parts[2].split(".")

      final_data  = "{:02d}".format(int(parts[0])) + ":"
      final_data += "{:02d}".format(int(parts[1])) + ":"
      final_data += "{:02d}".format(int(parts2[0])) + "."
      if(len(parts2) == 1):
        final_data += "000"
      else:
        final_data += "{:03d}".format(int(int(parts2[1])/1000))
      return final_data

    def __init__(self, c, online_asr_proc, min_chunk):
        self.connection = c
        self.online_asr_proc = online_asr_proc
        self.min_chunk = min_chunk

        self.last_end = None

        self.is_first = True

    def receive_audio_chunk(self) -> Union[np.ndarray, object, None]:
        """Accumulate enough audio to meet min_chunk (except when stream ends).

        Returns:
          np.ndarray: ready chunk
          NO_DATA_YET: temporary lack of data (keep looping)
          STREAM_ENDED: remote closed and no more audio
        """
        global running
        out = []
        minlimit = self.min_chunk * SAMPLING_RATE
        samples_accum = 0
        while running and samples_accum < minlimit:
            raw_bytes = self.connection.non_blocking_receive_audio()
            if raw_bytes is NO_DATA_YET:
                # Only return NO_DATA_YET if we have accumulated nothing.
                if not out:
                    return NO_DATA_YET
                else:
                    # Wait again; continue loop to try fill minlimit.
                    continue
            if raw_bytes is STREAM_ENDED:
                # If we have partial audio, process it even if below minlimit (end of stream)
                if out:
                    break
                return STREAM_ENDED
            # Normal bytes path
            if not raw_bytes:  # defensive (should be handled above)
                return NO_DATA_YET if not out else np.concatenate(out)
            audio = pcm16le_bytes_to_float32(raw_bytes)
            if audio is None or audio.size == 0:
                if not out:
                    return NO_DATA_YET
                break
            out.append(audio)
            samples_accum += audio.shape[0]

        if not out:
            return NO_DATA_YET
        # For first chunk, enforce minlimit unless stream ended (handled above)
        if self.is_first and samples_accum < minlimit:
            return NO_DATA_YET
        self.is_first = False
        if len(out) == 1:
            return out[0]
        return np.concatenate(out)

    def format_output_transcript(self,o):
        # This function differs from whisper_online.output_transcript in the following:
        # succeeding [beg,end] intervals are not overlapping because ELITR protocol (implemented in online-text-flow events) requires it.
        # Therefore, beg, is max of previous end and current beg outputed by Whisper.
        # Usually it differs negligibly, by appx 20 ms.

        if o[0] is not None:
            beg, end = o[0],o[1]
            if self.last_end is not None:
                beg = max(beg, self.last_end)

            self.last_end = end
            beg_webvtt = self.timedelta_to_webvtt(str(datetime.timedelta(seconds=beg)))
            end_webvtt = self.timedelta_to_webvtt(str(datetime.timedelta(seconds=end)))
            logger.info("%s -> %s %s" % (beg_webvtt, end_webvtt, o[2].strip()))

            data = {}
            # language field: use provided --lan unless 'auto', then fallback to 'en'
            if language and language != 'auto':
                data['language'] = language
            else:
                data['language'] = 'en'
            data['start'] = "%1.3f" % datetime.timedelta(seconds=beg).total_seconds()
            data['end'] = "%1.3f" % datetime.timedelta(seconds=end).total_seconds()
            data['text'] = o[2].strip()

            #return "%1.0f %1.0f %s" % (beg,end,o[2])
            return json.dumps(data)
        else:
            logger.debug("No text in this segment")
            return None

    def send_result(self, o):
        msg = self.format_output_transcript(o)
        if msg is not None:
            self.connection.send(msg)

    def process(self):
        global running
        # handle one client connection
        self.online_asr_proc.init()
        first_time = True
        while running:
            result = self.receive_audio_chunk()
            if result is NO_DATA_YET:
                continue  # remain in loop waiting for more audio
            if result is STREAM_ENDED:
                logger.info("Client stream ended")
                break
            # got usable audio chunk
            if first_time:
                first_time = False
                logger.info("Receiving Audio")
            self.online_asr_proc.insert_audio_chunk(result)
            o = online.process_iter()
            try:
                self.send_result(o)
            except BrokenPipeError:
                logger.info("broken pipe -- connection closed?")
                break
        # Flush remaining segments
        o = online.finish()
        try:
            self.send_result(o)
        except BrokenPipeError:
            logger.info("broken pipe -- connection closed?")

def run_subprocess(*_a, **_kw):
    raise RuntimeError("run_subprocess not available")

def worker_thread(*_a, **_kw):
    raise RuntimeError("worker_thread not available")

def stop(signum, frame):
    """Signal handler for graceful shutdown (Ctrl+C / SIGTERM)."""
    global running, server_socket, shutdown_logged
    if not running:  # already shutting down
        return
    running = False
    sig_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
    logger.info(f'Shutdown signal received ({sig_name}); finishing current operation...')
    if server_socket is not None:
        try:
            server_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            server_socket.close()
        except Exception:
            pass



# server loop

signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

def handle_client(conn, addr):
    """Process a single client connection (serial, no concurrency)."""
    connection = Connection(conn)
    proc = ServerProcessor(connection, online, args.min_chunk_size)
    proc.process()
    try:
        conn.close()
    except OSError:
        pass

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    server_socket = s
    s.bind((args.host, args.port))
    s.listen(5)  # increased backlog (Phase 6); still serial accept/process
    # Set a timeout so accept() wakes up periodically to observe running flag on Windows
    s.settimeout(1.0)
    logger.info('Listening on'+str((args.host, args.port)))
    last_client_addr = None
    while running:
        try:
            try:
                conn, addr = s.accept()
            except socket.timeout:
                if not running:
                    break
                continue
            except OSError as e:
                if not running:
                    break  # socket was closed due to shutdown
                logger.error(f"Socket accept error: {e}; continuing")
                continue
            logger.debug('Connected to client on {}'.format(addr))
            last_client_addr = addr
            handle_client(conn, addr)
            logger.debug('Connection to client closed {}'.format(addr))
        except Exception as e:
            if not running:
                break
            import errno
            # Normalize common connection reset scenarios (Windows WinError 10054 / POSIX ECONNRESET)
            win_err = getattr(e, 'winerror', None)
            err_no = getattr(e, 'errno', None)
            msg = str(e)
            if win_err == 10054 or err_no == errno.ECONNRESET or '10054' in msg or 'ECONNRESET' in msg:
                if last_client_addr:
                    logger.info(f"Unexpected client disconnect (connection reset) peer={last_client_addr[0]}:{last_client_addr[1]}")
                else:
                    logger.info("Unexpected client disconnect (connection reset)")
            else:
                if last_client_addr:
                    logger.error(f"Unexpected server loop error: {e} peer={last_client_addr[0]}:{last_client_addr[1]}; continuing")
                else:
                    logger.error(f"Unexpected server loop error: {e}; continuing")
            continue

if not shutdown_logged:
    logger.info('Server stopped gracefully')
running=False
