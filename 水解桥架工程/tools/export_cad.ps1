$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$cadApp = [Runtime.InteropServices.Marshal]::GetActiveObject('AutoCAD.Application.25')
$expectedName = '0241B_二期水解仪表桥架布局_1031.dwg'
if ($cadApp.ActiveDocument.Name -ne $expectedName) { throw "当前图纸不是 $expectedName，请先用T30打开正确图纸。" }
$captureDir = Join-Path $projectRoot ('data/读取记录/重新采集_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $captureDir | Out-Null
$legacy = Join-Path $PSScriptRoot 'source/export_trays.ps1'
$body = Get-Content -LiteralPath $legacy -Raw -Encoding UTF8
$body = $body.Replace('E:\Codex\Codex_3D_Model', $captureDir).Replace('E:/Codex/Codex_3D_Model', $captureDir.Replace('\','/'))
& ([scriptblock]::Create($body))
$paths = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'source/export_paths.lsp') -Raw -Encoding UTF8
$paths = $paths.Replace('E:/Codex/Codex_3D_Model', $captureDir.Replace('\','/'))
$lispPath = Join-Path $captureDir 'export_paths.lsp'
[IO.File]::WriteAllText($lispPath,$paths,[Text.Encoding]::GetEncoding(936))
$cadApp.ActiveDocument.SendCommand('(load "' + $lispPath.Replace('\','/') + '")' + "`n")
Write-Output "已提交采集：$captureDir。等待CAD命令结束后核对文件；不会覆盖基准。"
