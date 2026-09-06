package main

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestRecoveryBackoffAndBudgetPersistAcrossWatchdogRestart(t *testing.T) {
	path := filepath.Join(t.TempDir(), "recovery.json")
	now := time.Date(2026, 9, 6, 1, 0, 0, 0, time.UTC)

	state, allowed, _, err := reserveRecovery(path, "desktop_relaunch", now)
	if err != nil || !allowed || state.Consecutive != 1 {
		t.Fatalf("first reserve = (%+v, %v, %v)", state, allowed, err)
	}
	if _, allowed, wait, err := reserveRecovery(path, "desktop_relaunch", now.Add(time.Second)); err != nil || allowed || wait <= 0 {
		t.Fatalf("backoff was not retained: allowed=%v wait=%v err=%v", allowed, wait, err)
	}

	for _, offset := range []time.Duration{30 * time.Second, 90 * time.Second} {
		if _, allowed, _, err := reserveRecovery(path, "desktop_relaunch", now.Add(offset)); err != nil || !allowed {
			t.Fatalf("reserve at %v: allowed=%v err=%v", offset, allowed, err)
		}
	}
	if _, allowed, wait, err := reserveRecovery(path, "desktop_relaunch", now.Add(3*time.Minute)); err != nil || allowed || wait != recoveryCircuitBreak {
		t.Fatalf("budget circuit = allowed=%v wait=%v err=%v", allowed, wait, err)
	}
	if state, err := readRecoveryState(path, now.Add(3*time.Minute)); err != nil || parseRecoveryTime(state.CircuitOpenUntil).IsZero() {
		t.Fatalf("circuit did not persist: state=%+v err=%v", state, err)
	}
}

func TestHealthyResetClearsBackoffButKeepsRollingBudget(t *testing.T) {
	path := filepath.Join(t.TempDir(), "recovery.json")
	now := time.Date(2026, 9, 6, 1, 0, 0, 0, time.UTC)
	if _, allowed, _, err := reserveRecovery(path, "backend_start", now); err != nil || !allowed {
		t.Fatal(err)
	}
	state, err := markRecoveryHealthy(path, now.Add(time.Second))
	if err != nil || state.Consecutive != 0 || state.NextAllowedAt != "" || len(state.Events) != 1 {
		t.Fatalf("healthy reset = %+v err=%v", state, err)
	}
	if _, allowed, _, err := reserveRecovery(path, "backend_start", now.Add(2*time.Second)); err != nil || !allowed {
		t.Fatalf("healthy state should clear backoff: allowed=%v err=%v", allowed, err)
	}
}

func TestMalformedRecoveryStateFailsClosed(t *testing.T) {
	path := filepath.Join(t.TempDir(), "recovery.json")
	if err := os.WriteFile(path, []byte("{"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, allowed, _, err := reserveRecovery(path, "desktop_relaunch", time.Now()); err == nil || allowed {
		t.Fatalf("malformed state must fail closed: allowed=%v err=%v", allowed, err)
	}
}
