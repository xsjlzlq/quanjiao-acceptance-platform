$ErrorActionPreference = "Stop"
Write-Host "Starting Vite server..."
Set-Location frontend
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WindowStyle Hidden -RedirectStandardOutput vite.log -RedirectStandardError vite_err.log
Set-Location ..\backend
Write-Host "Starting FastAPI server..."
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--port", "8081", "--host", "0.0.0.0" -WindowStyle Hidden -RedirectStandardOutput api.log -RedirectStandardError api_err.log
Write-Host "Servers started. Checking ports..."
Start-Sleep -Seconds 3
Get-NetTCPConnection -LocalPort 8081,3000 -ErrorAction SilentlyContinue | Select-Object LocalAddress, LocalPort, State
