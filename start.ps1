$Root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "$Root\.venv\Scripts\python.exe"

Write-Host "Starting FastAPI on :8000 ..."
$api = Start-Process -NoNewWindow -PassThru -FilePath $Python `
    -ArgumentList "-m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload" `
    -WorkingDirectory $Root

Write-Host "Starting React dev server on :5173 ..."
$web = Start-Process -NoNewWindow -PassThru -FilePath "cmd" `
    -ArgumentList "/c npm run dev" `
    -WorkingDirectory "$Root\web"

Write-Host ""
Write-Host "  Backend  -> http://localhost:8000"
Write-Host "  Frontend -> http://localhost:5173"
Write-Host ""
Write-Host "Press Ctrl-C to stop both servers."

try { Wait-Process -Id $api.Id, $web.Id }
finally { Stop-Process -Id $api.Id, $web.Id -ErrorAction SilentlyContinue }
