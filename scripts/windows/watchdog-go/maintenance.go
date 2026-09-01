package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"
)

const (
	maintenanceNormal        = "NORMAL"
	maintenanceUnknown       = "UNKNOWN"
	malformedStateFailClosed = 4 * time.Hour
)

type maintenanceState struct {
	State          string `json:"state"`
	Owner          string `json:"owner"`
	Nonce          string `json:"nonce"`
	Epoch          int64  `json:"epoch"`
	Timestamp      string `json:"timestamp"`
	Reason         string `json:"reason"`
	LeaseSeconds   int    `json:"leaseSeconds"`
	LeaseExpiresAt string `json:"leaseExpiresAt"`
}

func maintenanceMode(path string, now time.Time) (maintenanceState, bool, error) {
	if strings.TrimSpace(path) == "" {
		return maintenanceState{State: maintenanceNormal}, false, nil
	}
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return maintenanceState{State: maintenanceNormal}, false, nil
	}
	if err != nil {
		return maintenanceState{State: maintenanceUnknown}, true, err
	}

	var state maintenanceState
	if err := json.Unmarshal(raw, &state); err != nil {
		info, statErr := os.Stat(path)
		if statErr == nil && now.Sub(info.ModTime()) > malformedStateFailClosed {
			return maintenanceState{State: maintenanceNormal}, false, err
		}
		return maintenanceState{State: maintenanceUnknown}, true, err
	}
	state.State = strings.ToUpper(strings.TrimSpace(state.State))
	if state.State == "" || state.State == maintenanceNormal {
		return state, false, nil
	}

	expiresAt, err := time.Parse(time.RFC3339, state.LeaseExpiresAt)
	if err != nil {
		return state, true, fmt.Errorf("invalid watchdog maintenance lease: %w", err)
	}
	if !expiresAt.After(now) {
		return state, false, nil
	}
	return state, true, nil
}
