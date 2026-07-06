package guardrails

import (
	"sync"
	"time"

	"github.com/huanghe/HomeState/internal/model"
)

// Rule represents a hard guardrail rule.
type Rule struct {
	ID       string
	Condition func(ctx model.ContextState) bool
	Effect    Effect
}

// Effect describes what happens when a rule triggers.
type Effect struct {
	Deny               []string `json:"deny,omitempty"`
	SetMode            string   `json:"set_mode,omitempty"`
	RequireConfirmation bool   `json:"require_confirmation,omitempty"`
}

// Engine evaluates guardrail rules against the current context.
type Engine struct {
	mu    sync.RWMutex
	rules []Rule
}

func New() *Engine {
	e := &Engine{}
	e.loadDefaults()
	return e
}

func (e *Engine) loadDefaults() {
	e.rules = []Rule{
		{
			ID: "night_no_auto_light",
			Condition: func(ctx model.ContextState) bool {
				hour := time.Now().Hour()
				minute := time.Now().Minute()
				t := hour*60 + minute
				return t >= 23*60+30 || t < 7*60
			},
			Effect: Effect{Deny: []string{"auto_turn_on_main_light"}},
		},
		{
			ID: "multi_room_disable_auto",
			Condition: func(ctx model.ContextState) bool {
				count := 0
				for _, rs := range ctx.Rooms {
					if rs.Occupancy {
						count++
					}
				}
				return count >= 2
			},
			Effect: Effect{SetMode: "safe_mode"},
		},
		{
			ID: "low_confidence_block",
			Condition: func(ctx model.ContextState) bool {
				for _, rs := range ctx.Rooms {
					if rs.Occupancy && rs.Confidence < 0.75 {
						return true
					}
				}
				return false
			},
			Effect: Effect{RequireConfirmation: true},
		},
	}
}

// Evaluate checks all rules against the context and returns triggered effects.
func (e *Engine) Evaluate(ctx model.ContextState) []TriggeredRule {
	e.mu.RLock()
	defer e.mu.RUnlock()

	var triggered []TriggeredRule
	for _, rule := range e.rules {
		if rule.Condition(ctx) {
			triggered = append(triggered, TriggeredRule{
				RuleID: rule.ID,
				Effect: rule.Effect,
			})
		}
	}
	return triggered
}

// IsAllowed checks if a specific action is permitted by the guardrails.
func (e *Engine) IsAllowed(ctx model.ContextState, action string) (bool, string) {
	triggered := e.Evaluate(ctx)
	for _, tr := range triggered {
		for _, denied := range tr.Effect.Deny {
			if denied == action {
				return false, "blocked by rule: " + tr.RuleID
			}
		}
		if tr.Effect.RequireConfirmation {
			return false, "requires confirmation due to rule: " + tr.RuleID
		}
	}
	return true, ""
}

// TriggeredRule pairs a rule ID with its effect.
type TriggeredRule struct {
	RuleID string
	Effect Effect
}

// AddRule adds a custom rule.
func (e *Engine) AddRule(r Rule) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.rules = append(e.rules, r)
}
