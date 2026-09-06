//go:build windows

package main

import (
	"os/exec"
	"testing"
)

func TestHideWindowsProcessSetsCreateNoWindow(t *testing.T) {
	cmd := exec.Command("python.exe", "-c", "pass")
	hideWindowsProcess(cmd)
	if cmd.SysProcAttr == nil {
		t.Fatal("SysProcAttr nil")
	}
	if !cmd.SysProcAttr.HideWindow {
		t.Fatal("HideWindow not set")
	}
	if cmd.SysProcAttr.CreationFlags&createNoWindow == 0 {
		t.Fatalf("CREATE_NO_WINDOW missing: flags=%#x", cmd.SysProcAttr.CreationFlags)
	}
	if cmd.SysProcAttr.CreationFlags&0x00000008 != 0 {
		t.Fatalf("DETACHED_PROCESS must not be set: flags=%#x", cmd.SysProcAttr.CreationFlags)
	}
}