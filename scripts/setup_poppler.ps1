# Download and setup Poppler for Windows

$popplerUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
$downloadPath = "$env:TEMP\poppler.zip"
$extractPath = "C:\poppler"

Write-Host "Downloading Poppler..." -ForegroundColor Green
Invoke-WebRequest -Uri $popplerUrl -OutFile $downloadPath

Write-Host "Extracting Poppler..." -ForegroundColor Green
Expand-Archive -Path $downloadPath -DestinationPath $extractPath -Force

Write-Host "Poppler installed to: $extractPath" -ForegroundColor Green
Write-Host "Binaries location: $extractPath\poppler-24.08.0\Library\bin" -ForegroundColor Yellow

# Add to PATH for current session
$env:PATH += ";$extractPath\poppler-24.08.0\Library\bin"

Write-Host "`nVerifying installation..." -ForegroundColor Green
& "$extractPath\poppler-24.08.0\Library\bin\pdftoppm.exe" -v

Write-Host "`nPoppler is ready to use!" -ForegroundColor Green
Write-Host "Note: This PATH change is temporary. Restart your terminal to use the permanent PATH." -ForegroundColor Yellow
