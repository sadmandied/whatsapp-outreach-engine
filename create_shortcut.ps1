$WshShell = New-Object -ComObject WScript.Shell
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatPath = Join-Path $BaseDir "run_gui.bat"
$IconPath = (Join-Path $BaseDir "assets\icon.ico") + ", 0"

# 1. Project Directory Shortcut
$ProjShortcutPath = Join-Path $BaseDir "WhatsApp Outreach Engine.lnk"
$Shortcut1 = $WshShell.CreateShortcut($ProjShortcutPath)
$Shortcut1.TargetPath = $BatPath
$Shortcut1.WorkingDirectory = $BaseDir
$Shortcut1.IconLocation = $IconPath
$Shortcut1.Description = "WhatsApp Outreach Engine - Modern Desktop Client"
$Shortcut1.Save()
Write-Host "[OK] Project shortcut created: $ProjShortcutPath"

# 2. Desktop Shortcut
$DesktopDir = [Environment]::GetFolderPath('Desktop')
if (Test-Path $DesktopDir) {
    $DeskShortcutPath = Join-Path $DesktopDir "WhatsApp Outreach Engine.lnk"
    $Shortcut2 = $WshShell.CreateShortcut($DeskShortcutPath)
    $Shortcut2.TargetPath = $BatPath
    $Shortcut2.WorkingDirectory = $BaseDir
    $Shortcut2.IconLocation = $IconPath
    $Shortcut2.Description = "WhatsApp Outreach Engine - Modern Desktop Client"
    $Shortcut2.Save()
    Write-Host "[OK] Desktop shortcut created: $DeskShortcutPath"
}
