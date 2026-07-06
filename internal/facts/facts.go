package facts

import (
	"sync"
	"time"

	"github.com/huanghe/HomeState/internal/model"
)

// Store holds the raw fact events as a time-series buffer.
type Store struct {
	mu     sync.RWMutex
	events []model.FactEvent
	limit  int
}

func New(limit int) *Store {
	if limit <= 0 {
		limit = 10000
	}
	return &Store{
		events: make([]model.FactEvent, 0, limit),
		limit:  limit,
	}
}

// Record stores a new fact event.
func (s *Store) Record(ev model.FactEvent) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if ev.Timestamp.IsZero() {
		ev.Timestamp = time.Now()
	}
	s.events = append(s.events, ev)
	if len(s.events) > s.limit {
		s.events = s.events[len(s.events)-s.limit:]
	}
}

// Latest returns the most recent event for an entity, or nil.
func (s *Store) Latest(entityID string) *model.FactEvent {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for i := len(s.events) - 1; i >= 0; i-- {
		if s.events[i].EntityID == entityID {
			return &s.events[i]
		}
	}
	return nil
}

// Recent returns the last N events for an entity.
func (s *Store) Recent(entityID string, n int) []model.FactEvent {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var result []model.FactEvent
	for i := len(s.events) - 1; i >= 0 && len(result) < n; i-- {
		if s.events[i].EntityID == entityID {
			result = append([]model.FactEvent{s.events[i]}, result...)
		}
	}
	return result
}

// AllSince returns all events after the given time.
func (s *Store) AllSince(since time.Time) []model.FactEvent {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var result []model.FactEvent
	for _, ev := range s.events {
		if ev.Timestamp.After(since) {
			result = append(result, ev)
		}
	}
	return result
}

// Count returns the total number of stored events.
func (s *Store) Count() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.events)
}
