package semantic

import (
	"encoding/json"
	"os"
	"sync"

	"github.com/huanghe/HomeState/internal/model"
)

// Registry manages semantic mappings from HA entities to human-readable meanings.
type Registry struct {
	mu       sync.RWMutex
	mappings map[string]model.SemanticMapping // keyed by entity_id
}

func New() *Registry {
	return &Registry{
		mappings: make(map[string]model.SemanticMapping),
	}
}

// LoadFile loads semantic mappings from a JSON file.
func (r *Registry) LoadFile(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	var list []model.SemanticMapping
	if err := json.Unmarshal(data, &list); err != nil {
		return err
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, m := range list {
		r.mappings[m.EntityID] = m
	}
	return nil
}

// SaveFile persists current mappings to a JSON file.
func (r *Registry) SaveFile(path string) error {
	r.mu.RLock()
	defer r.mu.RUnlock()
	list := make([]model.SemanticMapping, 0, len(r.mappings))
	for _, m := range r.mappings {
		list = append(list, m)
	}
	data, err := json.MarshalIndent(list, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

// Set adds or updates a semantic mapping.
func (r *Registry) Set(m model.SemanticMapping) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.mappings[m.EntityID] = m
}

// Get returns the semantic mapping for an entity, or nil.
func (r *Registry) Get(entityID string) *model.SemanticMapping {
	r.mu.RLock()
	defer r.mu.RUnlock()
	if m, ok := r.mappings[entityID]; ok {
		return &m
	}
	return nil
}

// All returns all registered mappings.
func (r *Registry) All() []model.SemanticMapping {
	r.mu.RLock()
	defer r.mu.RUnlock()
	list := make([]model.SemanticMapping, 0, len(r.mappings))
	for _, m := range r.mappings {
		list = append(list, m)
	}
	return list
}

// RoomEntities returns all entity IDs belonging to a room.
func (r *Registry) RoomEntities(room string) []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	var ids []string
	for _, m := range r.mappings {
		if m.Room == room {
			ids = append(ids, m.EntityID)
		}
	}
	return ids
}
