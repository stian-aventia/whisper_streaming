:: model large
:: python .\whisper_online_server.py --backend faster-whisper --model large --source-stream none --report-language no --min-chunk-size 1 --sampling_rate 16000 --buffer_trimming segment --buffer_trimming_sec 15 --use_gpu True --port 8000 --host 0.0.0.0 --log-level DEBUG --warmup-file samples_jfk.wav --model_cache_dir .\tmp --lan no

:: nbailab\large
@REM python .\whisper_online_server.py ^
@REM --backend faster-whisper ^
@REM --model_dir .\models\nbailab-medium ^
@REM --model_cache_dir .\tmp ^
@REM --language no ^
@REM --use_gpu True ^
@REM --host 0.0.0.0 ^
@REM --port 8000 ^
@REM --log-level INFO ^
@REM --warmup-file samples_jfk.wav ^
@REM --vad ^
@REM --vac ^
@REM --vac-chunk-size 0.04 ^
@REM --buffer_trimming segment ^
@REM --buffer_trimming_sec 25 ^
@REM --min-chunk-size 0.8

python .\whisper_online_server.py ^
--backend faster-whisper ^
--model large-v3 ^
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
