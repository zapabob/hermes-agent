//go:build windows

package main

import (
	"os/exec"
	"syscall"
)

// createNoWindow is CREATE_NO_WINDOW (0x08000000). HideWindow alone only sets
// STARTF_USESHOWWINDOW|SW_HIDE and is insufficient when the parent has no
// console - console-subsystem children (python.exe, Hermes.exe shims) still
// allocate visible windows. CREATE_NO_WINDOW gives the child a hidden console
// descendants inherit. Do NOT combine with DETACHED_PROCESS (CREATE_NO_WINDOW
// is ignored; Wave2 sacred).
const createNoWindow = 0x08000000

func hideWindowsProcess(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow:    true,
		CreationFlags: createNoWindow,
	}
}