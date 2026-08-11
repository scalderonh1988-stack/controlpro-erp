Set WShell = CreateObject("WScript.Shell")
WShell.Run chr(34) & "iniciar_erp.bat" & chr(34), 0, False
Set WShell = Nothing