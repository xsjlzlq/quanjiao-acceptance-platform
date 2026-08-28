$ErrorActionPreference = "Stop"
Write-Host "Installing frontend dependencies..."
Set-Location frontend
npm install --registry=https://registry.npmmirror.com
Write-Host "Starting Vite server..."
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WindowStyle Hidden
Set-Location ..\backend
Write-Host "Starting FastAPI server..."
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--port", "8000" -WindowStyle Hidden
Write-Host "All servers started!"
