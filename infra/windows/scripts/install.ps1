[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$InstallDir = "$env:LOCALAPPDATA\CoCounselNexus",

    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/NinthOctopusMitten/NinthOctopusMitten.git",

    [Parameter(Mandatory = $false)]
    [string]$Branch = "main",

    [Parameter(Mandatory = $false)]
    [switch]$Interactive,

    [Parameter(Mandatory = $false)]
    [switch]$LaunchOnComplete
)

$ErrorActionPreference = "Stop"

$script:InstallLogFile = $null
$script:HostIsInteractive = [Environment]::UserInteractive

function Resolve-InstallDirectory {
    param(
        [string]$DefaultPath,
        [bool]$ParameterProvided,
        [switch]$AllowPrompt
    )

    $normalizedDefault = if ([string]::IsNullOrWhiteSpace($DefaultPath)) {
        "$env:LOCALAPPDATA\CoCounselNexus"
    } else {
        $DefaultPath
    }

    if ($ParameterProvided -or -not $AllowPrompt.IsPresent) {
        return $normalizedDefault
    }

    try {
        $state = [hashtable]::Synchronized(@{
            DefaultPath = $normalizedDefault
            Result = $null
            SelectedPath = $null
            Error = $null
        })

        $threadScript = {
            param($threadState)

            try {
                Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
                try { Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue } catch { }
                [System.Windows.Forms.Application]::EnableVisualStyles()

                $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
                try {
                    $dialog.Description = "Select the folder where Co-Counsel Nexus should be installed."
                    $dialog.SelectedPath = $threadState.DefaultPath
                    $dialog.ShowNewFolderButton = $true

                    $threadState.Result = $dialog.ShowDialog()
                    $threadState.SelectedPath = $dialog.SelectedPath
                }
                finally {
                    $dialog.Dispose()
                }
            }
            catch {
                $threadState.Error = $_.Exception
            }
        }

        $thread = [System.Threading.Thread]::new([System.Threading.ParameterizedThreadStart]$threadScript)
        $thread.SetApartmentState([System.Threading.ApartmentState]::STA)
        $thread.Start($state)
        $thread.Join()

        if ($state.Error) {
            throw $state.Error
        }

        if ($state.Result -eq [System.Windows.Forms.DialogResult]::OK -and $state.SelectedPath) {
            return $state.SelectedPath
        }

        if ($state.Result -eq [System.Windows.Forms.DialogResult]::Cancel) {
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
        [string]$Message,
        [ValidateSet('Info','Warn','Error')]
        [string]$Level = 'Info'
    )
    $timestamp = (Get-Date).ToString("u")
    $line = "[$timestamp] [$Level] $Message"

    $color = switch ($Level) {
        'Warn'  { 'Yellow' }
        'Error' { 'Red' }
        default { 'Cyan' }
    }

    if ($script:HostIsInteractive) {
        Write-Host $line -ForegroundColor $color
    }

    if ($script:InstallLogFile) {
        Add-Content -Path $script:InstallLogFile -Value $line
    }
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
        [string]$WorkingDirectory = $null,
        [string]$Description = $null
    )

    $displayName = if ($Description) { $Description } else { "$FilePath $($Arguments -join ' ')" }
    Write-InstallStep "Running $displayName"

    $previousLocation = (Get-Location).Path
    if ($WorkingDirectory) {
        Push-Location $WorkingDirectory
    }

    try {
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE

        if ($output) {
            if ($script:InstallLogFile) {
                Add-Content -Path $script:InstallLogFile -Value $output
            }
            Write-Verbose ($output -join [Environment]::NewLine)
        }

        if ($exitCode -ne 0) {
            throw "Command '$FilePath' exited with code $exitCode"
        }
    }
    finally {
        if ($WorkingDirectory) {
            Pop-Location
        }
        Set-Location -Path $previousLocation
    }
}

function Show-MessageBox {
    param(
        [string]$Message,
        [string]$Title,
        [ValidateSet('Information','Error')]
        [string]$Icon = 'Information'
    )

    if (-not [Environment]::UserInteractive) {
        return
    }

    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
        $iconEnum = [System.Windows.Forms.MessageBoxIcon]::$Icon
        [System.Windows.Forms.MessageBox]::Show($Message, $Title, [System.Windows.Forms.MessageBoxButtons]::OK, $iconEnum) | Out-Null
    }
    catch {
        # Swallow errors when message box support is unavailable (e.g., server core).
    }
}

Write-InstallStep "Preparing Co-Counsel Nexus installation..."

$installDirParamProvided = $PSBoundParameters.ContainsKey('InstallDir')
try {
    $InstallDir = Resolve-InstallDirectory -DefaultPath $InstallDir -ParameterProvided:$installDirParamProvided -AllowPrompt:$Interactive
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
$script:InstallLogFile = $logFile
"Installation started at $(Get-Date -Format u)" | Out-File -FilePath $logFile -Encoding utf8

try {
    if (Test-Path $repoDir) {
        Write-InstallStep "Repository already exists. Pulling latest changes..."
        Push-Location $repoDir
        try {
            Invoke-Process -FilePath "git" -Arguments @("fetch", "origin") -Description "git fetch origin"
            Invoke-Process -FilePath "git" -Arguments @("checkout", $Branch) -Description "git checkout $Branch"
            Invoke-Process -FilePath "git" -Arguments @("pull", "origin", $Branch) -Description "git pull origin $Branch"
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-InstallStep "Cloning repository from $RepoUrl (branch $Branch)"
        Invoke-Process -FilePath "git" -Arguments @("clone", "--depth", "1", "--branch", $Branch, $RepoUrl, $repoDir) -Description "git clone $RepoUrl"
    }

    $pythonExe = (Get-Command python).Source
    Write-InstallStep "Bootstrapping Python virtual environment"
    Invoke-Process -FilePath $pythonExe -Arguments @("-m", "venv", $venvDir) -Description "python -m venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"

    Write-InstallStep "Upgrading pip and installing backend dependencies"
    Invoke-Process -FilePath $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "wheel", "uv") -Description "pip install tooling"
    Invoke-Process -FilePath $venvPython -Arguments @("-m", "uv", "pip", "install", "-r", "backend/requirements.txt") -WorkingDirectory $repoDir -Description "uv pip install -r backend/requirements.txt"

    $frontendDir = Join-Path $repoDir "frontend"
    Write-InstallStep "Installing frontend dependencies"
    Invoke-Process -FilePath "npm" -Arguments @("install") -WorkingDirectory $frontendDir -Description "npm install"

    Write-InstallStep "Building frontend bundle"
    Invoke-Process -FilePath "npm" -Arguments @("run", "build") -WorkingDirectory $frontendDir -Description "npm run build"

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

    if ($LaunchOnComplete) {
        Write-InstallStep "Launching Co-Counsel Nexus per request."
        Start-Process -FilePath powershell.exe -ArgumentList @('-ExecutionPolicy','Bypass','-File',$startScriptPath) | Out-Null
    }

    Show-MessageBox -Message "Co-Counsel Nexus installed successfully. A desktop shortcut is now available." -Title "Co-Counsel Nexus" -Icon Information
}
catch {
    $message = "Installation failed: $($_.Exception.Message). Review the log at $logFile for details."
    Write-InstallStep $message -Level Error
    Show-MessageBox -Message $message -Title "Co-Counsel Nexus" -Icon Error
    throw
}
