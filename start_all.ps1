$ErrorActionPreference = "Stop"
Write-Host "Installing frontend dependencies..."
Set-Location frontend
npm install --registry=https://registry.npmmirror.com
Write-Host "Starting Vite server..."
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WindowStyle Hidden
Set-Location ..\backend
Write-Host "Starting FastAPI server..."
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--port", "8081", "--host", "0.0.0.0" -WindowStyle Hidden
Write-Host "All servers started!"
