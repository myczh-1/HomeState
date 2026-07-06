package context

import (
	"sync"
	"time"

	"github.com/huanghe/HomeState/internal/model"
)

const (
	motionTimeout    = 5 * time.Minute
	confidenceDecay  = 0.02 // per minute after last motion
)

// Engine maintains the current home context state.
type Engine struct {
	mu    sync.RWMutex
	state model.ContextState
}

func New() *Engine {
	return &Engine{
		state: model.ContextState{
			HouseMode: string(model.HouseModeUnknown),
			Rooms:     make(map[string]model.RoomState),
			UpdatedAt: time.Now(),
		},
	}
}

// Snapshot returns a copy of the current context state.
func (e *Engine) Snapshot() model.ContextState {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.state
}

// ProcessFact updates context based on a new fact event and its semantic mapping.
func (e *Engine) ProcessFact(ev model.FactEvent, sem *model.SemanticMapping) {
	e.mu.Lock()
	defer e.mu.Unlock()

	if sem == nil {
		return
	}

	room := sem.Room
	rs := e.state.Rooms[room]

	switch sem.Semantic {
	case "desk_presence", "room_motion", "presence":
		if ev.State == "on" || ev.State == "detected" || ev.State == "occupied" {
			rs.Occupancy = true
			rs.Confidence = 0.95
			rs.LastMotion = ev.Timestamp
			if sem.Semantic == "desk_presence" {
				e.state.Activity.Working = true
			}
		} else if ev.State == "off" || ev.State == "clear" || ev.State == "not_occupied" {
			// Don't immediately mark as empty — wait for timeout
			rs.LastMotion = ev.Timestamp
		}
	case "door":
		// Door events update room context indirectly
		rs.LastMotion = ev.Timestamp
	}

	e.state.Rooms[room] = rs
	e.recalculate()
	e.state.UpdatedAt = time.Now()
}

// Tick performs periodic maintenance: decay confidence, mark rooms empty.
func (e *Engine) Tick() {
	e.mu.Lock()
	defer e.mu.Unlock()
	now := time.Now()

	for room, rs := range e.state.Rooms {
		if rs.Occupancy && now.Sub(rs.LastMotion) > motionTimeout {
			rs.Occupancy = false
			rs.Confidence = 0.3
			e.state.Rooms[room] = rs
		} else if rs.Occupancy {
			elapsed := now.Sub(rs.LastMotion).Minutes()
			decay := elapsed * confidenceDecay
			rs.Confidence = clamp01(0.95 - decay)
			e.state.Rooms[room] = rs
		}
	}

	e.recalculate()
	e.state.UpdatedAt = now
}

// recalculate assumes lock is held.
func (e *Engine) recalculate() {
	occupied := 0
	var currentRoom string
	maxConf := 0.0

	for room, rs := range e.state.Rooms {
		if rs.Occupancy {
			occupied++
			if rs.Confidence > maxConf {
				maxConf = rs.Confidence
				currentRoom = room
			}
		}
	}

	e.state.CurrentRoom = currentRoom

	switch {
	case occupied == 0:
		e.state.HouseMode = string(model.HouseModeEmpty)
		e.state.Activity.Working = false
		e.state.Activity.Sleeping = false
	case occupied == 1:
		e.state.HouseMode = string(model.HouseModeSingle)
	default:
		e.state.HouseMode = string(model.HouseModeMulti)
	}

	// Sleeping heuristic: bedroom occupied, no other activity
	bedroom, hasBedroom := e.state.Rooms["bedroom"]
	if hasBedroom && bedroom.Occupancy && !e.state.Activity.Working {
		// If bedroom is the only active room and it's late, mark sleeping
		if occupied == 1 {
			e.state.Activity.Sleeping = true
		}
	}
}

// SetRoomState allows external override of a room's state.
func (e *Engine) SetRoomState(room string, rs model.RoomState) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.state.Rooms[room] = rs
	e.recalculate()
	e.state.UpdatedAt = time.Now()
}

func clamp01(v float64) float64 {
	if v < 0 {
		return 0
	}
	if v > 1 {
		return 1
	}
	return v
}
