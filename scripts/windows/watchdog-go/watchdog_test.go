package main

import (
	"errors"
	"testing"
)

func TestShouldLaunchDesktop(t *testing.T) {
	probeFailure := errors.New("WMI unavailable")
	cases := []struct {
		name          string
		manageDesktop bool
		desktopErr    error
		desktopCount  int
		want          bool
	}{
		{"disabled", false, nil, 0, false},
		{"probe failure", true, probeFailure, 0, false},
		{"desktop present", true, nil, 1, false},
		{"operator enabled and absent", true, nil, 0, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := shouldLaunchDesktop(tc.manageDesktop, tc.desktopErr, tc.desktopCount); got != tc.want {
				t.Fatalf("shouldLaunchDesktop(%t, %v, %d) = %t, want %t", tc.manageDesktop, tc.desktopErr, tc.desktopCount, got, tc.want)
			}
		})
	}
}

func TestShouldRestartDesktop(t *testing.T) {
	cases := []struct {
		name          string
		manageDesktop bool
		failCount     int
		failThreshold int
		want          bool
	}{
		{"disabled", false, 2, 2, false},
		{"below threshold", true, 1, 2, false},
		{"at threshold", true, 2, 2, true},
		{"zero threshold is bounded", true, 1, 0, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := shouldRestartDesktop(tc.manageDesktop, tc.failCount, tc.failThreshold); got != tc.want {
				t.Fatalf("shouldRestartDesktop(%t, %d, %d) = %t, want %t", tc.manageDesktop, tc.failCount, tc.failThreshold, got, tc.want)
			}
		})
	}
}
