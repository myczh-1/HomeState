package api

import (
	"encoding/json"
	"log"
	"net/http"

	"github.com/huanghe/HomeState/internal/context"
	"github.com/huanghe/HomeState/internal/decision"
	"github.com/huanghe/HomeState/internal/facts"
	"github.com/huanghe/HomeState/internal/model"
	"github.com/huanghe/HomeState/internal/semantic"
)

// Server exposes the HomeState HTTP API.
type Server struct {
	ctx  *context.Engine
	fact *facts.Store
	sem  *semantic.Registry
	dec  *decision.Engine
}

func New(ctx *context.Engine, fact *facts.Store, sem *semantic.Registry, dec *decision.Engine) *Server {
	return &Server{ctx: ctx, fact: fact, sem: sem, dec: dec}
}

// Handler returns the configured HTTP handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/context", s.handleContext)
	mux.HandleFunc("/api/semantic", s.handleSemantic)
	mux.HandleFunc("/api/semantic/set", s.handleSetSemantic)
	mux.HandleFunc("/api/mode", s.handleMode)
	mux.HandleFunc("/api/health", s.handleHealth)
	return mux
}

// GET /api/context — returns current context state
func (s *Server) handleContext(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, s.ctx.Snapshot())
}

// GET /api/semantic — returns all semantic mappings
func (s *Server) handleSemantic(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, s.sem.All())
}

// POST /api/semantic/set — sets a semantic mapping
func (s *Server) handleSetSemantic(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var m model.SemanticMapping
	if err := json.NewDecoder(r.Body).Decode(&m); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	s.sem.Set(m)
	writeJSON(w, map[string]string{"status": "ok"})
}

// GET/POST /api/mode — get or set run mode
func (s *Server) handleMode(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, map[string]string{"mode": string(s.dec.GetMode())})
	case http.MethodPost:
		var body struct {
			Mode string `json:"mode"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		s.dec.SetMode(model.RunMode(body.Mode))
		writeJSON(w, map[string]string{"mode": body.Mode})
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

// GET /api/health
func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]any{
		"status": "ok",
		"facts":  s.fact.Count(),
	})
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("[api] write error: %v", err)
	}
}
