#!/bin/bash
##
## This code and all components (c) Copyright 2006 - 2025, Wowza Media Systems, LLC. All rights reserved.
## This code is licensed pursuant to the Wowza Public License version 1.0, available at www.wowza.com/legal.
##

# usage: whisper_online_server.py 
# [-h] [--host HOST] [--port PORT] [--min-chunk-size MIN_CHUNK_SIZE]
# [--model {tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large-v3,large,large-v3-turbo}]
# [--model_cache_dir MODEL_CACHE_DIR] [--model_dir MODEL_DIR] [--lan LAN] [--task {transcribe,translate}]
# [--backend {faster-whisper,openai-api}] [--vad] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

backend="${BACKEND:-faster-whisper}"
model="${MODEL:-tiny.en}"
language="${LANGUAGE:-auto}"
log_level="${LOG_LEVEL:-INFO}"
min_chunk_size="${MIN_CHUNK_SIZE:-1}"
sampling_rate="${SAMPLING_RATE:-16000}"

disable_flag=""
if [ "${DISABLE_GPU:-}" != "" ]; then
  disable_flag="--disable_gpu"
fi

exec python whisper_online_server.py \
	--backend $backend \
	--model $model \
	--min-chunk-size $min_chunk_size \
	--sampling_rate $sampling_rate \
	$disable_flag \
	--port 3000 \
	--host 0.0.0.0 \
	--log-level $log_level \
	--model_cache_dir /tmp \
	--lan $language