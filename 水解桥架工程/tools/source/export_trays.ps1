$ErrorActionPreference = 'Stop'
$a=[Runtime.InteropServices.Marshal]::GetActiveObject('AutoCAD.Application.25')
$d=$a.ActiveDocument
$s=$d.SelectionSets.Add('CODEX_TRAY_EXPORT')
try {
 $s.Select(5,$null,$null,[int16[]]@(8),[object[]]@('CABLETRAY_WEAK*'))
 $rows=foreach($e in $s){
  $row=[ordered]@{handle=$e.Handle;type=$e.ObjectName;layer=$e.Layer;properties=@{}}
  foreach($p in @('StartEl','EndEl','Width','Height','Type','Style','LRotation','SegLen','CWidth','EWidth','CWeight','EWeight','ChannelA','ChannelB')){
   try {$row.properties[$p]=$e.$p} catch {}
  }
  try {$lo=$null;$hi=$null;$e.GetBoundingBox([ref]$lo,[ref]$hi);$row.bounds=@($lo,$hi)} catch {}
  $row
 }
 $rows | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 'E:\Codex\Codex_3D_Model\tray_objects.json'
 $rows | Group-Object type | Select-Object Count,Name | Format-Table
} finally {$s.Delete()}
$d.SendCommand('(progn (setq f (open "E:/Codex/Codex_3D_Model/tray_entget.txt" "w") ss (ssget "_X" (list (cons 8 "CABLETRAY_WEAK*"))) i 0) (repeat (sslength ss) (prin1 (entget (ssname ss i) (list "*")) f) (write-line "" f) (setq i (1+ i))) (close f) (princ))' + "`n")
