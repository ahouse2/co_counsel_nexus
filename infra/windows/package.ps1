[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$Output = "CoCounselInstaller.exe",

    [Parameter(Mandatory = $false)]
    [string]$IconPath = "$PSScriptRoot\\assets\\cocounsel.ico"
)

$ErrorActionPreference = "Stop"

$installScript = Join-Path $PSScriptRoot "scripts\install.ps1"
if (-not (Test-Path $installScript)) {
    throw "Unable to locate install.ps1 under $PSScriptRoot/scripts."
}

if (-not (Get-Module -ListAvailable -Name PS2EXE)) {
    Write-Host "Installing PS2EXE module..." -ForegroundColor Cyan
    Install-Module -Name PS2EXE -Scope CurrentUser -Force -AllowClobber
}

Import-Module PS2EXE -ErrorAction Stop

$outputPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Output))
$iconPath = if (Test-Path $IconPath) { [System.IO.Path]::GetFullPath($IconPath) } else { $null }

$arguments = @{
    InputFile  = $installScript
    OutputFile = $outputPath
    NoConsole  = $true
    Title      = "Co-Counsel Nexus Installer"
    Product    = "Co-Counsel Nexus"
    Company    = "Co-Counsel Labs"
}

if ($iconPath) {
    $arguments.IconFile = $iconPath
}

Write-Host "Packaging installer to $outputPath..." -ForegroundColor Cyan
Invoke-PS2EXE @arguments
Write-Host "Installer packaged successfully." -ForegroundColor Green
