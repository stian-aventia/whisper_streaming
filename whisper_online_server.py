#!/usr/bin/env python3
from whisper_online import *

import sys
import argparse
import os
import logging
import numpy as np
import signal
import datetime
import json

logger = logging.getLogger(__name__)
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
# setting whisper object by args 

SAMPLING_RATE = args.sampling_rate
size = args.model
language = args.lan
asr, online = asr_factory(args)
min_chunk = args.min_chunk_size

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

class Connection:
    '''it wraps conn object'''
    PACKET_SIZE = 32000*5*60 # 5 minutes # was: 65536

    def __init__(self, conn):
        self.conn = conn
        self.last_line = ""

        self.conn.setblocking(True)

    def send(self, line):
        '''it doesn't send the same line twice, because it was problematic in online-text-flow-events'''
        if line == self.last_line:
            return
        line_packet.send_one_line(self.conn, line)
        self.last_line = line

    def non_blocking_receive_audio(self):
        try:
            r = self.conn.recv(self.PACKET_SIZE)
            return r
        except ConnectionResetError:
            return None


import io
import soundfile

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

    def receive_audio_chunk(self):
        global running
        # receive all audio that is available by this time
        # blocks operation if less than self.min_chunk seconds is available
        # unblocks if connection is closed or a chunk is available
        out = []
        minlimit = self.min_chunk*SAMPLING_RATE
        while running and sum(len(x) for x in out) < minlimit:
            raw_bytes = self.connection.non_blocking_receive_audio()
            if not raw_bytes:
                break
#            print("received audio:",len(raw_bytes), "bytes", raw_bytes[:10])
            sf = soundfile.SoundFile(io.BytesIO(raw_bytes), channels=1,endian="LITTLE",samplerate=SAMPLING_RATE, subtype="PCM_16",format="RAW")
            audio, _ = librosa.load(sf,sr=SAMPLING_RATE,dtype=np.float32)
            out.append(audio)
        if not out:
            return None
        conc = np.concatenate(out)
        if self.is_first and len(conc) < minlimit:
            return None
        self.is_first = False
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
            a = self.receive_audio_chunk()
            if a is None:
                if first_time:
                    logger.debug("No audio, exiting")
                else:
                    logger.info("No audio, exiting")
                break
            else:
                if first_time:
                    first_time = False
                    logger.info("Receiving Audio")
                
                self.online_asr_proc.insert_audio_chunk(a)
                o = online.process_iter()
                try:
                    self.send_result(o)
                except BrokenPipeError:
                    logger.info("broken pipe -- connection closed?")
                    break
        #need to send what we have left
        o = online.finish()
        try:
            self.send_result(o)
        except BrokenPipeError:
            logger.info("broken pipe -- connection closed?")

def run_subprocess(*_a, **_kw):
    raise RuntimeError("run_subprocess not available")

def worker_thread(*_a, **_kw):
    raise RuntimeError("worker_thread not available")

def stop(self, signum=None, frame=None):
    global running, server_socket
    running = False
    if server_socket is not None:
        try:
            server_socket.close()
        except OSError:
            pass



# server loop

signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    server_socket = s
    s.bind((args.host, args.port))
    s.listen(1)
    logger.info('Listening on'+str((args.host, args.port)))
    last_client_addr = None
    while running:
        try:
            try:
                conn, addr = s.accept()
            except OSError as e:
                if not running:
                    break  # socket was closed due to shutdown
                logger.error(f"Socket accept error: {e}; continuing")
                continue
            logger.debug('Connected to client on {}'.format(addr))
            last_client_addr = addr
            connection = Connection(conn)
            proc = ServerProcessor(connection, online, args.min_chunk_size)
            proc.process()
            try:
                conn.close()
            except OSError:
                pass
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

logger.info('Server Stopped')
running=False
