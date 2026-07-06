package haclient

import (
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
	"github.com/huanghe/HomeState/internal/model"
)

// Client is a Home Assistant WebSocket API client.
type Client struct {
	url       string
	token     string
	conn      *websocket.Conn
	mu        sync.Mutex
	msgID     atomic.Int64
	connected bool
	handlers  []func(model.FactEvent)
}

func New(url, token string) *Client {
	return &Client{url: url, token: token}
}

// OnEvent registers a handler for incoming HA state change events.
func (c *Client) OnEvent(fn func(model.FactEvent)) {
	c.handlers = append(c.handlers, fn)
}

// Connect establishes the WebSocket connection and authenticates.
func (c *Client) Connect() error {
	conn, _, err := websocket.DefaultDialer.Dial(c.url, nil)
	if err != nil {
		return fmt.Errorf("websocket dial: %w", err)
	}
	c.conn = conn

	// Read hello message
	_, msg, err := conn.ReadMessage()
	if err != nil {
		return fmt.Errorf("read hello: %w", err)
	}
	var hello haMessage
	if err := json.Unmarshal(msg, &hello); err != nil || hello.Type != "auth_required" {
		return fmt.Errorf("unexpected hello: %s", string(msg))
	}

	// Send auth
	auth := map[string]any{
		"type":         "auth",
		"access_token": c.token,
	}
	if err := conn.WriteJSON(auth); err != nil {
		return fmt.Errorf("send auth: %w", err)
	}

	// Read auth result
	_, msg, err = conn.ReadMessage()
	if err != nil {
		return fmt.Errorf("read auth result: %w", err)
	}
	var authResult haMessage
	if err := json.Unmarshal(msg, &authResult); err != nil || authResult.Type != "auth_ok" {
		return fmt.Errorf("auth failed: %s", string(msg))
	}

	c.connected = true
	log.Println("[haclient] connected to", c.url)
	return nil
}

// SubscribeEvents subscribes to state_changed events and processes them.
func (c *Client) SubscribeEvents() error {
	c.mu.Lock()
	id := c.msgID.Add(1)
	c.mu.Unlock()

	sub := map[string]any{
		"id":   id,
		"type": "subscribe_events",
		"event_type": "state_changed",
	}
	if err := c.conn.WriteJSON(sub); err != nil {
		return fmt.Errorf("subscribe: %w", err)
	}

	// Read subscription result
	_, msg, err := c.conn.ReadMessage()
	if err != nil {
		return fmt.Errorf("read sub result: %w", err)
	}
	var result haMessage
	if err := json.Unmarshal(msg, &result); err != nil || result.Type != "result" || !result.Success {
		return fmt.Errorf("subscribe failed: %s", string(msg))
	}

	log.Println("[haclient] subscribed to state_changed")
	return nil
}

// Listen processes incoming messages. Blocks until disconnection.
func (c *Client) Listen() error {
	for {
		_, msg, err := c.conn.ReadMessage()
		if err != nil {
			c.connected = false
			return fmt.Errorf("read message: %w", err)
		}

		var event haEventMessage
		if err := json.Unmarshal(msg, &event); err != nil {
			continue
		}
		if event.Type != "event" || event.Event.EventType != "state_changed" {
			continue
		}

		newState := event.Event.Data.NewState
		if newState.EntityID == "" {
			continue
		}

		fact := model.FactEvent{
			EntityID:  newState.EntityID,
			State:     newState.State,
			OldState:  event.Event.Data.OldState.State,
			Attrs:     newState.Attributes,
			Timestamp: time.Now(),
		}

		for _, h := range c.handlers {
			h(fact)
		}
	}
}

// IsConnected returns whether the client is currently connected.
func (c *Client) IsConnected() bool {
	return c.connected
}

// Close closes the connection.
func (c *Client) Close() {
	if c.conn != nil {
		c.conn.Close()
	}
	c.connected = false
}

// HA WebSocket message types

type haMessage struct {
	Type    string `json:"type"`
	Success bool   `json:"success,omitempty"`
}

type haEventMessage struct {
	Type  string `json:"type"`
	Event struct {
		EventType string `json:"event_type"`
		Data      struct {
			OldState haState `json:"old_state"`
			NewState haState `json:"new_state"`
		} `json:"data"`
	} `json:"event"`
}

type haState struct {
	EntityID   string         `json:"entity_id"`
	State      string         `json:"state"`
	Attributes map[string]any `json:"attributes"`
}
