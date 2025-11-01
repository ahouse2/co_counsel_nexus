[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$InstallDir = "$env:LOCALAPPDATA\CoCounselNexus",

    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/NinthOctopusMitten/NinthOctopusMitten.git",

    [Parameter(Mandatory = $false)]
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

function Resolve-InstallDirectory {
    param(
        [string]$DefaultPath,
        [bool]$ParameterProvided
    )

    $normalizedDefault = if ([string]::IsNullOrWhiteSpace($DefaultPath)) {
        "$env:LOCALAPPDATA\CoCounselNexus"
    } else {
        $DefaultPath
    }

    if ($ParameterProvided -or -not [Environment]::UserInteractive) {
        return $normalizedDefault
    }

    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        try { Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue } catch { }
        [System.Windows.Forms.Application]::EnableVisualStyles()

        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = "Select the folder where Co-Counsel Nexus should be installed."
        $dialog.SelectedPath = $normalizedDefault
        $dialog.ShowNewFolderButton = $true

        $result = $dialog.ShowDialog()
        if ($result -eq [System.Windows.Forms.DialogResult]::OK -and $dialog.SelectedPath) {
            return $dialog.SelectedPath
        }

        if ($result -eq [System.Windows.Forms.DialogResult]::Cancel) {
            throw [System.OperationCanceledException]::new("Installation cancelled by user.")
        }
    }
    catch {
        Write-Verbose "Falling back to default install directory: $($_.Exception.Message)"
    }

    return $normalizedDefault
}

function Write-InstallStep {
    param(
        [string]$Message
    )
    $timestamp = (Get-Date).ToString("u")
    Write-Host "[$timestamp] $Message" -ForegroundColor Cyan
}

function Ensure-CommandExists {
    param(
        [string]$Command,
        [string]$WingetId,
        [string]$PackageName
    )

    if (Get-Command $Command -ErrorAction SilentlyContinue) {
        return
    }

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is required to install $PackageName automatically. Please install winget and rerun the installer."
    }

    Write-InstallStep "Installing $PackageName via winget..."
    $wingetArgs = @(
        "install",
        "--id", $WingetId,
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--silent"
    )
    winget @wingetArgs
}

function Invoke-Process {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $null
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = [string]::Join(' ', $Arguments)
    if ($WorkingDirectory) {
        $psi.WorkingDirectory = $WorkingDirectory
    }
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi

    $null = $process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    if ($process.ExitCode -ne 0) {
        throw "Command '$FilePath $($Arguments -join ' ') ' failed with exit code $($process.ExitCode). Error: $stderr"
    }

    if ($stdout) {
        Write-Verbose $stdout
    }
    if ($stderr) {
        Write-Verbose $stderr
    }
}

Write-InstallStep "Preparing Co-Counsel Nexus installation..."

$installDirParamProvided = $PSBoundParameters.ContainsKey('InstallDir')
try {
    $InstallDir = Resolve-InstallDirectory -DefaultPath $InstallDir -ParameterProvided:$installDirParamProvided
}
catch [System.OperationCanceledException] {
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    return
}

$requiredPackages = @(
    @{ Command = "git"; WingetId = "Git.Git"; Name = "Git" },
    @{ Command = "python"; WingetId = "Python.Python.3.11"; Name = "Python 3.11" },
    @{ Command = "npm"; WingetId = "OpenJS.NodeJS.LTS"; Name = "Node.js 20 LTS" }
)

foreach ($pkg in $requiredPackages) {
    Ensure-CommandExists -Command $pkg.Command -WingetId $pkg.WingetId -PackageName $pkg.Name
}

$resolvedInstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$repoDir = Join-Path $resolvedInstallDir "NinthOctopusMitten"
$venvDir = Join-Path $resolvedInstallDir "venv"
$logDir = Join-Path $resolvedInstallDir "logs"

Write-InstallStep "Creating installation directories under $resolvedInstallDir"
New-Item -ItemType Directory -Path $resolvedInstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$logFile = Join-Path $logDir "install.log"
"Installation started at $(Get-Date -Format u)" | Out-File -FilePath $logFile -Encoding utf8

if (Test-Path $repoDir) {
    Write-InstallStep "Repository already exists. Pulling latest changes..."
    Push-Location $repoDir
    try {
        Invoke-Process -FilePath "git" -Arguments @("fetch", "origin")
        Invoke-Process -FilePath "git" -Arguments @("checkout", $Branch)
        Invoke-Process -FilePath "git" -Arguments @("pull", "origin", $Branch)
    }
    finally {
        Pop-Location
    }
}
else {
    Write-InstallStep "Cloning repository from $RepoUrl (branch $Branch)"
    Invoke-Process -FilePath "git" -Arguments @("clone", "--depth", "1", "--branch", $Branch, $RepoUrl, $repoDir)
}

$pythonExe = (Get-Command python).Source
Write-InstallStep "Bootstrapping Python virtual environment"
Invoke-Process -FilePath $pythonExe -Arguments @("-m", "venv", $venvDir)
$venvPython = Join-Path $venvDir "Scripts\python.exe"

Write-InstallStep "Upgrading pip and installing backend dependencies"
Invoke-Process -FilePath $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "wheel", "uv")
Invoke-Process -FilePath $venvPython -Arguments @("-m", "uv", "pip", "install", "-r", "backend/requirements.txt") -WorkingDirectory $repoDir

$frontendDir = Join-Path $repoDir "frontend"
Write-InstallStep "Installing frontend dependencies"
Invoke-Process -FilePath "npm" -Arguments @("install") -WorkingDirectory $frontendDir

Write-InstallStep "Building frontend bundle"
Invoke-Process -FilePath "npm" -Arguments @("run", "build") -WorkingDirectory $frontendDir

$startScriptPath = Join-Path $resolvedInstallDir "Start-CoCounsel.ps1"
$backendScript = "`"$venvDir\Scripts\Activate.ps1`"; Set-Location `"$repoDir\backend`"; uvicorn app.main:app --host 127.0.0.1 --port 8000"
$frontendScript = "Set-Location `"$frontendDir`"; npm run dev -- --host 127.0.0.1 --port 5173"
$startScript = @"
Write-Host "Launching Co-Counsel Nexus services..." -ForegroundColor Cyan
Start-Process -FilePath powershell.exe -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-Command',"$backendScript"
Start-Sleep -Seconds 5
Start-Process -FilePath powershell.exe -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-Command',"$frontendScript"
Start-Sleep -Seconds 10
Start-Process "http://localhost:5173"
"@
$startScript | Out-File -FilePath $startScriptPath -Encoding utf8 -Force

Write-InstallStep "Creating desktop shortcut"
$shortcutPath = Join-Path ([Environment]::GetFolderPath('CommonDesktopDirectory')) "Co-Counsel Nexus.lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$startScriptPath`""
$shortcut.WorkingDirectory = $resolvedInstallDir
$shortcut.WindowStyle = 1
$shortcut.IconLocation = "powershell.exe,0"
$shortcut.Description = "Launch Co-Counsel Nexus"
$shortcut.Save()

Write-InstallStep "Writing uninstall helper"
$uninstallScriptPath = Join-Path $resolvedInstallDir "Uninstall-CoCounsel.ps1"
$uninstallScript = @"
Write-Host "Removing Co-Counsel Nexus installation..." -ForegroundColor Yellow
if (Test-Path "$shortcutPath") { Remove-Item "$shortcutPath" -ErrorAction SilentlyContinue }
if (Test-Path "$resolvedInstallDir") { Remove-Item "$resolvedInstallDir" -Recurse -Force }
Write-Host "Co-Counsel Nexus removed."
"@
$uninstallScript | Out-File -FilePath $uninstallScriptPath -Encoding utf8 -Force

"Installation completed successfully at $(Get-Date -Format u)" | Out-File -FilePath $logFile -Append -Encoding utf8
Write-InstallStep "Installation complete. Use the desktop shortcut to launch Co-Counsel Nexus."
