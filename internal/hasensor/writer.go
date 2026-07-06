package hasensor

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/huanghe/HomeState/internal/context"
	"github.com/huanghe/HomeState/internal/model"
)

// Writer pushes HomeState's context state back to Home Assistant as virtual sensors.
type Writer struct {
	haURL   string
	haToken string
	ctx     *context.Engine
}

func New(haURL, haToken string, ctxEngine *context.Engine) *Writer {
	return &Writer{
		haURL:   strings.TrimRight(haURL, "/"),
		haToken: haToken,
		ctx:     ctxEngine,
	}
}

// Push updates all virtual sensor states in HA.
func (w *Writer) Push() {
	state := w.ctx.Snapshot()

	sensors := []sensorUpdate{
		{
			State:      state.CurrentRoom,
			Attributes: map[string]any{"friendly_name": "HomeState Current Room", "icon": "mdi:map-marker"},
			EntityID:   "sensor.homestate_current_room",
		},
		{
			State:      boolState(state.Activity.Working),
			Attributes: map[string]any{"friendly_name": "HomeState Working", "icon": "mdi:laptop"},
			EntityID:   "binary_sensor.homestate_working",
		},
		{
			State:      boolState(state.Activity.Sleeping),
			Attributes: map[string]any{"friendly_name": "HomeState Sleeping", "icon": "mdi:sleep"},
			EntityID:   "binary_sensor.homestate_sleeping",
		},
		{
			State:      houseModeDisplay(state.HouseMode),
			Attributes: map[string]any{"friendly_name": "HomeState House Mode", "icon": "mdi:home"},
			EntityID:   "sensor.homestate_house_mode",
		},
	}

	for room, rs := range state.Rooms {
		sensors = append(sensors, sensorUpdate{
			State: boolState(rs.Occupancy),
			Attributes: map[string]any{
				"friendly_name": fmt.Sprintf("HomeState %s Occupancy", capitalize(room)),
				"confidence":    rs.Confidence,
				"icon":          "mdi:account-check",
			},
			EntityID: fmt.Sprintf("binary_sensor.homestate_%s_occupancy", room),
		})
	}

	for _, s := range sensors {
		if err := w.setSensor(s); err != nil {
			log.Printf("[hasensor] push %s: %v", s.EntityID, err)
		}
	}
}

// RunPushLoop periodically pushes state to HA.
func (w *Writer) RunPushLoop(interval time.Duration, stop <-chan struct{}) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			w.Push()
		case <-stop:
			return
		}
	}
}

type sensorUpdate struct {
	State      string         `json:"state"`
	Attributes map[string]any `json:"attributes"`
	EntityID   string         `json:"-"`
}

func (w *Writer) setSensor(s sensorUpdate) error {
	url := fmt.Sprintf("%s/api/states/%s", w.haURL, s.EntityID)
	body, _ := json.Marshal(s)
	req, err := http.NewRequest(http.MethodPost, url, strings.NewReader(string(body)))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+w.haToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("HA returned %d", resp.StatusCode)
	}
	return nil
}

func boolState(b bool) string {
	if b {
		return "on"
	}
	return "off"
}

func houseModeDisplay(mode string) string {
	switch model.HouseMode(mode) {
	case model.HouseModeSingle:
		return "single_person"
	case model.HouseModeMulti:
		return "multi_person"
	case model.HouseModeEmpty:
		return "empty"
	default:
		return "unknown"
	}
}

func capitalize(s string) string {
	if len(s) == 0 {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}
