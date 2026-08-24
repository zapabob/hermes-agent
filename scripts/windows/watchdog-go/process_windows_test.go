//go:build windows

package main

import (
	"os"
	"testing"
)

func TestProcessAliveUsesNativeProcessState(t *testing.T) {
	if !processAlive(os.Getpid()) {
		t.Fatal("current process must be reported alive")
	}
	if processAlive(0) {
		t.Fatal("PID zero must not be reported alive")
	}
}
