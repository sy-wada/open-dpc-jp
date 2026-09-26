$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('open-dpc-ps-test-' + [guid]::NewGuid().ToString('N'))
$source = Join-Path $tempRoot 'source'
[System.IO.Directory]::CreateDirectory($source) | Out-Null
$list = Join-Path $tempRoot 'pt_list.csv'
[System.IO.File]::WriteAllText($list, "pt_id,research_id,data_identifier,event_date,encounter_start_date,encounter_end_date`r`n,r_00001,0000000123,20260102,20260101,20260110`r`n", [System.Text.UTF8Encoding]::new($true))
[System.IO.File]::WriteAllText((Join-Path $source 'EFn_synthetic_2601.txt'), "年月`tデータ識別番号`t値`r`n2601`t0000000123`t合成`r`n2601`t9999999999`t除外`r`n", [System.Text.Encoding]::GetEncoding(932))
$output = Join-Path $tempRoot 'output'
& (Join-Path $root 'extraction/dpc_extractor_fast.ps1') -PathToDir $source -TargetSheet $list -OutputRoot $output -MarginDays 0 | Out-Null
$result = Join-Path $output 'r_00001/2601/EFn_synthetic_2601.txt'
if (-not (Test-Path -LiteralPath $result)) { throw 'missing extracted file' }
$extracted = [System.IO.File]::ReadAllText($result, [System.Text.Encoding]::GetEncoding(932))
if (-not $extracted.Contains("2601`tr_00001`t合成") -or $extracted.Contains('9999999999')) { throw 'identifier replacement or filtering failed' }
$invalid = Join-Path $tempRoot 'invalid.csv'
[System.IO.File]::WriteAllText($invalid, "pt_id,research_id,data_identifier,event_date,encounter_start_date,encounter_end_date`r`n,../escape,0000000123,,20260101,20260110`r`n", [System.Text.UTF8Encoding]::new($true))
$badOutput = Join-Path $tempRoot 'bad-output'
$rejected = $false
try { & (Join-Path $root 'extraction/dpc_extractor_fast.ps1') -PathToDir $source -TargetSheet $invalid -OutputRoot $badOutput -MarginDays 0 | Out-Null }
catch { $rejected = $true }
if (-not $rejected -or (Test-Path -LiteralPath $badOutput)) { throw 'invalid patient list was not rejected before output' }
Write-Host 'PASS PowerShell extraction contract'
