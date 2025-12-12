# Setup Script for Docker Volume Directories
# Run this before `docker compose up` on fresh installations

Write-Host "Creating required directories for Docker volumes..." -ForegroundColor Cyan

$directories = @(
    ".\var\models\huggingface",
    ".\var\models\whisper",
    ".\var\models\tts",
    ".\var\storage\documents",
    ".\var\storage\graphs",
    ".\var\storage\telemetry",
    ".\var\backups"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "✓ Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "✓ Exists: $dir" -ForegroundColor Gray
    }
}

Write-Host "`nAll directories ready! You can now run: docker compose up" -ForegroundColor Cyan
