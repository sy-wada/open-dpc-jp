
@echo off
setlocal

if "%~1"=="" (
    echo Drag and drop a folder onto this BAT file.
    pause
    exit /b 1
)

if not exist "%~1\" (
    echo Invalid folder path.
    pause
    exit /b 1
)

set "TARGET=%~f1"
set "OUTPUT=%~dp1%~n1_tree.txt"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = $env:TARGET; $out = $env:OUTPUT;" ^
  "$lines = New-Object 'System.Collections.Generic.List[string]';" ^
  "$lines.Add($root);" ^
  "function Walk($path, $prefix) {" ^
  "  $items = @(Get-ChildItem -LiteralPath $path -Force -ErrorAction SilentlyContinue | Sort-Object @{Expression={-not $_.PSIsContainer}}, Name);" ^
  "  for ($i = 0; $i -lt $items.Count; $i++) {" ^
  "    $item = $items[$i];" ^
  "    $last = ($i -eq $items.Count - 1);" ^
  "    $branch = if ($last) { '\-- ' } else { '+-- ' };" ^
  "    if ($item.PSIsContainer) {" ^
  "      $lines.Add($prefix + $branch + $item.Name + '\');" ^
  "      $next = if ($last) { '    ' } else { '|   ' };" ^
  "      Walk $item.FullName ($prefix + $next);" ^
  "    } else {" ^
  "      $size = '{0:N0} bytes' -f $item.Length;" ^
  "      $lines.Add($prefix + $branch + $item.Name + ' (' + $size + ')');" ^
  "    }" ^
  "  }" ^
  "};" ^
  "Walk $root '';" ^
  "$lines | Out-File -LiteralPath $out -Encoding UTF8"

if errorlevel 1 (
    echo Export failed.
    pause
    exit /b 1
)

echo.
echo Export completed:
echo %OUTPUT%
pause
