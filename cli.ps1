[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TimelineForPCArgs
)

$ErrorActionPreference = "Stop"
$ProductRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontDoor = Join-Path $ProductRoot "timeline-for-pc.ps1"

& $FrontDoor @TimelineForPCArgs
exit $LASTEXITCODE
