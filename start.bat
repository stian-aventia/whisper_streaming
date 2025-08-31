:: model large
:: python .\whisper_online_server.py --backend faster-whisper --model large --source-stream none --report-language no --min-chunk-size 1 --sampling_rate 16000 --buffer_trimming segment --buffer_trimming_sec 15 --use_gpu True --port 8000 --host 0.0.0.0 --log-level DEBUG --warmup-file samples_jfk.wav --model_cache_dir .\tmp --lan no

:: nbailab\large
python .\whisper_online_server.py ^
--backend faster-whisper ^
--model_dir .\models\nbailab-large ^
--model_cache_dir .\tmp ^
--language no ^
--use_gpu True ^
--host 0.0.0.0 ^
--port 8000 ^
--log-level INFO ^
--warmup-file samples_jfk.wav ^
--vad ^
--vac ^
--vac-chunk-size 0.04 ^
--buffer_trimming segment ^
--buffer_trimming_sec 25 ^
--min-chunk-size 0.8


::--vac True ^
::--buffer_trimming segment ^
::--buffer_trimming_sec 15 ^
::--sampling_rate 16000 ^
::--min-chunk-size 1 ^
::--source-stream none ^
::--report-language no ^
::--vad True ^
