# Biweekly pmem health reminder. On issues: write flag + balloon tip.
# Then in Cursor say: 按 pmem-consolidate 收口
param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [int]$Days = 60
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

if (-not (Get-Command pmem -ErrorAction SilentlyContinue)) {
    throw "pmem not found in PATH"
}

$mem = Join-Path $Root ".memory"
$cache = Join-Path $mem "cache"
New-Item -ItemType Directory -Force -Path $cache | Out-Null
$reportPath = Join-Path $cache "health-latest.txt"
$jsonPath = Join-Path $cache "health-latest.json"
$flagPath = Join-Path $cache "health-action-needed.txt"

function Invoke-PmemRedirect([string[]]$PmemArgs, [string]$OutFile) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = (Get-Command pmem).Source
    # Quote each arg for ProcessStartInfo.Arguments
    $psi.Arguments = ($PmemArgs | ForEach-Object {
        if ($_ -match '\s') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
    }) -join ' '
    $psi.WorkingDirectory = $Root
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $p = [System.Diagnostics.Process]::Start($psi)
    $stdout = $p.StandardOutput.ReadToEnd()
    $stderr = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    if ($p.ExitCode -ne 0) {
        throw "pmem $($PmemArgs -join ' ') failed ($($p.ExitCode)): $stderr$stdout"
    }
    [System.IO.File]::WriteAllText($OutFile, $stdout, (New-Object System.Text.UTF8Encoding $false))
}

Invoke-PmemRedirect @("health", "--days", "$Days", "--json", "--root", $Root) $jsonPath
Invoke-PmemRedirect @("health", "--days", "$Days", "--root", $Root) $reportPath
$h = [System.IO.File]::ReadAllText($jsonPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json

function Count-OrZero($x) {
    if ($null -eq $x) { return 0 }
    if ($x -is [System.Array]) { return $x.Length }
    if ($null -ne $x.PSObject.Properties["Count"]) { return [int]$x.Count }
    return 1
}

$bits = New-Object System.Collections.Generic.List[string]
if (Count-OrZero $h.unregistered) { [void]$bits.Add("unregistered $(Count-OrZero $h.unregistered)") }
if (Count-OrZero $h.duplicates) { [void]$bits.Add("duplicates $(Count-OrZero $h.duplicates)") }
if (Count-OrZero $h.contradictions) { [void]$bits.Add("contradictions $(Count-OrZero $h.contradictions)") }
if (($null -ne $h.stale) -and ([int]$h.stale.total -gt 0)) { [void]$bits.Add("stale $($h.stale.total)") }
if (Count-OrZero $h.hot_returns) { [void]$bits.Add("hot_returns $(Count-OrZero $h.hot_returns)") }
if (Count-OrZero $h.compact) { [void]$bits.Add("compact $(Count-OrZero $h.compact)") }
if (Count-OrZero $h.seeds) { [void]$bits.Add("seeds $(Count-OrZero $h.seeds)") }
if (Count-OrZero $h.misses) { [void]$bits.Add("misses $(Count-OrZero $h.misses)") }

function Show-Balloon([string]$Title, [string]$Body) {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue | Out-Null
    Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue | Out-Null
    $ni = New-Object System.Windows.Forms.NotifyIcon
    $ni.Icon = [System.Drawing.SystemIcons]::Information
    $ni.Visible = $true
    $ni.BalloonTipTitle = $Title
    $ni.BalloonTipText = $Body
    $ni.ShowBalloonTip(12000)
    Start-Sleep -Seconds 1
    $ni.Dispose()
}

if ($bits.Count -eq 0) {
    if (Test-Path $flagPath) { Remove-Item $flagPath -Force }
    Show-Balloon "pmem health" "OK. Report: $reportPath"
    Write-Host "OK: no actionable issues"
    exit 0
}

$summary = [string]::Join("; ", $bits)
$when = Get-Date -Format "yyyy-MM-dd HH:mm"
$flag = @(
    "time: $when"
    "root: $Root"
    "found: $summary"
    ""
    "next: open Cursor and say:"
    "pmem-consolidate"
    ""
    "report:"
    $reportPath
)
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllLines($flagPath, $flag, $utf8)
Show-Balloon "pmem needs consolidate" "$summary. Cursor: pmem-consolidate"
Write-Host "ACTION NEEDED: $summary"
exit 0
