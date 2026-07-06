package decision

import (
	"fmt"
	"time"

	"github.com/huanghe/HomeState/internal/context"
	"github.com/huanghe/HomeState/internal/guardrails"
	"github.com/huanghe/HomeState/internal/model"
	"github.com/huanghe/HomeState/internal/semantic"
)

// Engine makes action decisions based on context + guardrails.
type Engine struct {
	ctx      *context.Engine
	guard    *guardrails.Engine
	semantic *semantic.Registry
	mode     model.RunMode
}

func New(ctxEngine *context.Engine, guardEngine *guardrails.Engine, sem *semantic.Registry, mode model.RunMode) *Engine {
	return &Engine{
		ctx:      ctxEngine,
		guard:    guardEngine,
		semantic: sem,
		mode:     mode,
	}
}

// SetMode changes the run mode.
func (e *Engine) SetMode(m model.RunMode) {
	e.mode = m
}

// GetMode returns the current run mode.
func (e *Engine) GetMode() model.RunMode {
	return e.mode
}

// ShouldAct evaluates whether an action should be taken on an entity.
func (e *Engine) ShouldAct(action, entityID string) model.Decision {
	ctx := e.ctx.Snapshot()
	dec := model.Decision{
		Action:    action,
		Entity:    entityID,
		Timestamp: time.Now(),
	}

	sem := e.semantic.Get(entityID)
	if sem == nil {
		dec.Allowed = false
		dec.Reason = "no semantic mapping for entity"
		dec.Confidence = 0
		return dec
	}

	// Check guardrails
	allowed, reason := e.guard.IsAllowed(ctx, action)
	dec.GuardrailsPassed = allowed

	if !allowed {
		dec.Allowed = false
		dec.Reason = reason
		dec.Confidence = ctx.Rooms[sem.Room].Confidence
		return dec
	}

	// In observe mode, never allow actions
	if e.mode == model.RunModeObserve {
		dec.Allowed = false
		dec.Reason = "observe mode — context updated but no action taken"
		dec.Confidence = ctx.Rooms[sem.Room].Confidence
		return dec
	}

	// In suggest mode, mark as needs confirmation
	if e.mode == model.RunModeSuggest {
		dec.Allowed = false
		dec.Reason = "suggested — awaiting user confirmation"
		dec.Confidence = ctx.Rooms[sem.Room].Confidence
		return dec
	}

	// Auto mode
	dec.Allowed = true
	dec.Confidence = ctx.Rooms[sem.Room].Confidence
	dec.Reason = e.buildReason(ctx, sem)
	return dec
}

func (e *Engine) buildReason(ctx model.ContextState, sem *model.SemanticMapping) string {
	rs := ctx.Rooms[sem.Room]
	if rs.Occupancy {
		return fmt.Sprintf("%s occupied (confidence: %.2f)", sem.Room, rs.Confidence)
	}
	return fmt.Sprintf("%s unoccupied (confidence: %.2f)", sem.Room, rs.Confidence)
}
