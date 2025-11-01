# Co-Counsel Nexus Windows Installer

This directory provides the assets required to create a "one click" Windows installer that
retrieves the latest Co-Counsel Nexus code from GitHub, provisions dependencies, and
creates a desktop shortcut that launches the experience.

## Contents

- `scripts/install.ps1` — idempotent bootstrapper that installs dependencies, clones the
  repository, builds the backend/frontend, writes launch/uninstall helpers, and
  can optionally auto-launch the experience once installation completes.
- `package.ps1` — helper that packages the installer script into a standalone `.exe`
  using the [`PS2EXE`](https://github.com/MScholtes/PS2EXE) tool.
- `assets/` — optional icons for the packaged installer (create `cocounsel.ico` to
  customize branding).

## Running the Installer Script Directly

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
powershell -File .\infra\windows\scripts\install.ps1 -RepoUrl "https://github.com/NinthOctopusMitten/NinthOctopusMitten.git"
```

Key behaviors:

1. Ensures `git`, `python` (3.11), and `npm` are present. Missing tools are installed via `winget`.
2. Uses `%LOCALAPPDATA%\CoCounselNexus` as the default installation directory. Pass
   `-Interactive` to surface a folder picker for advanced scenarios.
3. Creates a Python virtual environment and installs backend requirements via `uv`.
4. Installs and builds the Vite/React frontend.
5. Generates a `Start-CoCounsel.ps1` launcher that opens the backend API, frontend UI,
   and browser tab automatically.
6. Places a desktop shortcut and an `Uninstall-CoCounsel.ps1` helper alongside the
   installation.
7. Writes a timestamped log under `%LOCALAPPDATA%\CoCounselNexus\logs\install.log`
   and shows a completion dialog when run from the packaged installer.

Override parameters as needed:

```powershell
powershell -File .\infra\windows\scripts\install.ps1 -InstallDir "D:\Apps\CoCounsel" -RepoUrl "https://github.com/example/NinthOctopusMitten.git" -Branch "develop" -LaunchOnComplete
```

When packaged as a `.exe`, double-clicking the installer uses the default location silently and
surfaces a completion toast. Advanced users can still pass `-InstallDir`, `-Interactive`,
`-LaunchOnComplete`, and the other parameters from an elevated PowerShell prompt by invoking the
generated executable with standard command-line arguments.

## Building a Single-File `.exe`

On a Windows workstation with PowerShell 5.1+ or PowerShell 7+, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
powershell -File .\infra\windows\package.ps1 -Output "CoCounselNexusInstaller.exe"
```

The script will install the `PS2EXE` module (if missing) and emit a fully packaged
installer executable. Distribute the resulting `.exe` to deliver a true one-click setup
experience. When executed, the `.exe` runs `install.ps1` silently and guides the user through
installation via console status messages.

## Post-Install Launch

The desktop shortcut invokes `Start-CoCounsel.ps1`, which opens two PowerShell windows:

- Backend service running `uvicorn app.main:app --port 8000` within the virtual environment.
- Frontend service running `npm run dev -- --host 127.0.0.1 --port 5173`.

After a short warm-up, the default browser is opened at `http://localhost:5173`.

For production deployments, pair the installer with the existing Docker/Helm charts found in
`infra/` to run the services under process managers such as NSSM or Windows Service Wrapper.
