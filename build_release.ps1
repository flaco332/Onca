# Uses the active Python environment. Never removes existing distributions.
param([string]$OutputDirectory = "dist")
$ErrorActionPreference = "Stop"
& python (Join-Path $PSScriptRoot "build_release.py") --output $OutputDirectory
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
