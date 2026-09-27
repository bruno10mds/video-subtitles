Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = base & "\.venv\Scripts\pythonw.exe"
script = base & "\gui.py"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = base
shell.Run """" & pythonw & """ """ & script & """", 0, False
