$url = "http://localhost:8001/health"
$ingestUrl = "http://localhost:8001/api/documents/ingestion/local"
$timeout = 600
$startTime = Get-Date

Write-Host "Waiting for API at $url..."

while ($true) {
    try {
        $response = Invoke-WebRequest -Uri $url -Method Get -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "API is healthy!"
            break
        }
    }
    catch {
        # Write-Host "Waiting..."
    }
    
    if (((Get-Date) - $startTime).TotalSeconds -gt $timeout) {
        Write-Host "Timeout waiting for API."
        exit 1
    }
    Start-Sleep -Seconds 5
}

Write-Host "Triggering ingestion..."
try {
    $response = Invoke-RestMethod -Uri $ingestUrl -Method Post -Body @{case_id = "default_case"; directory_path = "test_ingest" }
    Write-Host "Ingestion triggered successfully."
    Write-Host ($response | ConvertTo-Json -Depth 5)
}
catch {
    Write-Host "Failed to trigger ingestion: $_"
    exit 1
}
