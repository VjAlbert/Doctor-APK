; Make sure no engine process is left from a previous run: a running apkguard-engine.exe locks its own
; file, and the installer would then keep the old engine next to the new interface.

!macro NSIS_HOOK_PREINSTALL
  nsExec::Exec 'taskkill /F /T /IM apkguard-engine.exe'
  Pop $0
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::Exec 'taskkill /F /T /IM apkguard-engine.exe'
  Pop $0
!macroend
