package model

import "time"

// FactEvent represents a raw event from Home Assistant.
type FactEvent struct {
	EntityID  string    `json:"entity_id"`
	State     string    `json:"state"`
	OldState  string    `json:"old_state,omitempty"`
	Attrs     Attrs     `json:"attributes,omitempty"`
	Timestamp time.Time `json:"timestamp"`
}

type Attrs map[string]any

// SemanticMapping maps an HA entity to a human-readable semantic meaning.
type SemanticMapping struct {
	EntityID   string   `json:"entity_id"`
	Room       string   `json:"room"`
	Semantic   string   `json:"semantic"`
	Meaning    []string `json:"meaning,omitempty"`
	Confidence float64  `json:"confidence"`
	Role       string   `json:"role,omitempty"`           // e.g. "main_light", "ambient_light"
	Policy     string   `json:"control_policy,omitempty"` // "auto", "manual_protected"
}

// RoomState holds the current context state for a room.
type RoomState struct {
	Occupancy  bool    `json:"occupancy"`
	Confidence float64 `json:"confidence"`
	LastMotion time.Time `json:"last_motion,omitempty"`
	Activity   string  `json:"activity,omitempty"`
}

// ContextState is the full home context snapshot.
type ContextState struct {
	HouseMode  string               `json:"house_mode"`
	CurrentRoom string              `json:"current_room"`
	Rooms      map[string]RoomState `json:"rooms"`
	Activity   ActivityState        `json:"activity"`
	UpdatedAt  time.Time            `json:"updated_at"`
}

type ActivityState struct {
	Working bool `json:"working"`
	Sleeping bool `json:"sleeping"`
}

// Decision represents an action decision made by the engine.
type Decision struct {
	Action           string  `json:"action"`
	Entity           string  `json:"entity"`
	Allowed          bool    `json:"allowed"`
	Confidence       float64 `json:"confidence"`
	Reason           string  `json:"reason"`
	GuardrailsPassed bool    `json:"guardrails_passed"`
	Timestamp        time.Time `json:"timestamp"`
}

// RunMode defines the operating mode of HomeState.
type RunMode string

const (
	RunModeObserve RunMode = "observe"
	RunModeSuggest RunMode = "suggest"
	RunModeAuto    RunMode = "auto"
)

// HouseMode defines the household mode.
type HouseMode string

const (
	HouseModeSingle  HouseMode = "single_person"
	HouseModeMulti   HouseMode = "multi_person"
	HouseModeEmpty   HouseMode = "empty"
	HouseModeUnknown HouseMode = "unknown"
)
