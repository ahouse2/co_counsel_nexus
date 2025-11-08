# 2025-11-27 — Windows installer one-click refresh

## Summary
- Removed mandatory folder selection to deliver a true one-click experience that defaults to `%LOCALAPPDATA%\\CoCounselNexus` while keeping an optional interactive picker for advanced operators.
- Hardened the installer logging and process invocation pipeline so every dependency/bootstrap step is logged and resilient to spaces in paths.
- Added UX niceties including completion message boxes and optional post-install auto-launch to reduce friction for non-technical users.

## Validation
- Static review of `infra/windows/scripts/install.ps1` updates (PowerShell script execution not available in CI container).

## Follow-ups
- When feasible, exercise the packaged installer on a Windows VM to confirm the message box and shortcut creation behaviors under `PS2EXE`.
