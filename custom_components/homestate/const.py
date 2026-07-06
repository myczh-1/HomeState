"""HomeState constants."""

DOMAIN = "homestate"

CONF_RUN_MODE = "run_mode"
CONF_ROOMS = "rooms"
CONF_ENTITIES = "entities"

RUN_MODE_OBSERVE = "observe"
RUN_MODE_SUGGEST = "suggest"
RUN_MODE_AUTO = "auto"

DEFAULT_RUN_MODE = RUN_MODE_OBSERVE
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Default rooms for initial setup
DEFAULT_ROOMS = ["study", "bedroom", "living_room", "kitchen"]
