cd 'C:\Users\xnakamura\OneDrive\デスクトップ\broken-link-builder'
& .\.venv\Scripts\Activate.ps1
$env:VERBOSE='1'; $env:ROWS_LIMIT='0'; $env:FLUSH_EVERY='3'
python -u -m src.main *>> 'outputs\run.log'
