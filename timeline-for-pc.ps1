[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TimelineForPCArgs
)

$ErrorActionPreference = "Stop"

$ProductRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceRoot = Join-Path $ProductRoot "src"
$PreviousPythonPath = $env:PYTHONPATH

if ([string]::IsNullOrWhiteSpace($PreviousPythonPath)) {
    $env:PYTHONPATH = $SourceRoot
}
else {
    $env:PYTHONPATH = "$SourceRoot;$PreviousPythonPath"
}

$PythonCommand = $null
$PythonPrefixArgs = @()
$VenvPython = Join-Path $ProductRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonCommand = $VenvPython
}
elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
    $PythonCommand = "python.exe"
}
elseif (Get-Command py.exe -ErrorAction SilentlyContinue) {
    $PythonCommand = "py.exe"
    $PythonPrefixArgs = @("-3.11")
}
else {
    Write-Error "Python 3.11 or newer was not found. Install Python, then run this command again."
    exit 1
}

try {
    & $PythonCommand @PythonPrefixArgs -m timeline_for_pc @TimelineForPCArgs
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
