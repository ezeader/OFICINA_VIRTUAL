param([ValidateSet('editor','biblioteca','audios')][string]$Carpeta='editor')
$ErrorActionPreference='Stop'
$root='C:\Users\ezead\OneDrive\Documentos\URBE MARKETING'
if($Carpeta -ne 'editor') {
 $folder=if($Carpeta -eq 'biblioteca'){'01_BIBLIOTECA_ORIGINALES'}else{'05_AUDIOS'}
 $target=Join-Path $root $folder
 if(!(Test-Path -LiteralPath $target)){throw "No se encuentra $target"}
 Start-Process explorer.exe -ArgumentList ('"'+$target+'"')
 return
}
$existing='C:\Users\ezead\Documents\Codex\2026-10-06\quiero-que-trabajes-directamente-sobre-mi\outputs\Abrir_Storyboard_Urbetrack.ps1'
if(!(Test-Path -LiteralPath $existing)){throw 'No se encuentra el iniciador original en esta computadora.'}
& $existing
