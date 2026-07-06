package config

import (
	"encoding/json"
	"os"

	"github.com/huanghe/HomeState/internal/model"
)

// Config holds the application configuration.
type Config struct {
	HAURL      string `json:"ha_url"`       // e.g. "ws://homeassistant.local:8123/api/websocket"
	HAToken    string `json:"ha_token"`      // Long-lived access token
	APIPort    int    `json:"api_port"`      // HTTP API port, default 8099
	DBPath     string `json:"db_path"`       // SQLite path
	RunMode    string `json:"run_mode"`      // "observe", "suggest", "auto"
	AIBaseURL  string `json:"ai_base_url"`   // OpenAI-compatible endpoint
	AIAPIKey   string `json:"ai_api_key"`    // API key
	AIModel    string `json:"ai_model"`      // model name
}

func Default() *Config {
	return &Config{
		HAURL:   "ws://homeassistant.local:8123/api/websocket",
		APIPort: 8099,
		DBPath:  "homestate.db",
		RunMode: string(model.RunModeObserve),
	}
}

func Load(path string) (*Config, error) {
	cfg := Default()
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return cfg, nil
		}
		return nil, err
	}
	if err := json.Unmarshal(data, cfg); err != nil {
		return nil, err
	}
	return cfg, nil
}

func (c *Config) RunModeEnum() model.RunMode {
	switch c.RunMode {
	case "suggest":
		return model.RunModeSuggest
	case "auto":
		return model.RunModeAuto
	default:
		return model.RunModeObserve
	}
}
