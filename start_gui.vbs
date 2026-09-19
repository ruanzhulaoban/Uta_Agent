Option Explicit
Dim shell, fso, root, python, prefix, version, install, command, candidate, folder
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
python = ""
' Official Python installers register this path, even without Add to PATH.
For Each prefix In Array("HKCU\Software\Python\PythonCore\", "HKLM\Software\Python\PythonCore\")
    For Each version In Array("3.14", "3.13", "3.12", "3.11", "3.10")
        On Error Resume Next
        Err.Clear
        install = shell.RegRead(prefix & version & "\InstallPath\")
        If Err.Number = 0 Then
            candidate = fso.BuildPath(install, "pythonw.exe")
            If fso.FileExists(candidate) And python = "" Then python = candidate
        End If
        On Error GoTo 0
    Next
Next
If python = "" Then
    For Each folder In Split(shell.ExpandEnvironmentStrings("%PATH%"), ";")
        folder = Replace(folder, Chr(34), "")
        If folder <> "" Then
            candidate = fso.BuildPath(folder, "pythonw.exe")
            If fso.FileExists(candidate) And python = "" Then python = candidate
        End If
    Next
End If
If python <> "" Then
    command = Chr(34) & python & Chr(34)
Else
    command = "pyw.exe -3"
End If
On Error Resume Next
shell.Run command & " " & Chr(34) & root & "\gui.pyw" & Chr(34), 0, False
If Err.Number <> 0 Then
    MsgBox "Install standard 64-bit Python 3.10-3.14, then open start_gui.bat again." & vbCrLf & "Alternatively run: python gui.py" & vbCrLf & Err.Description, vbCritical, "utaagent"
    WScript.Quit 1
End If
