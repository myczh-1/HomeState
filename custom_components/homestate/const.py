"""HomeState constants."""

DOMAIN = "homestate"

CONF_RUN_MODE = "run_mode"
CONF_ROOMS = "rooms"
CONF_ENTITIES = "entities"
CONF_AI_BASE_URL = "ai_base_url"
CONF_AI_API_KEY = "ai_api_key"
CONF_AI_MODEL = "ai_model"

RUN_MODE_OBSERVE = "observe"
RUN_MODE_SUGGEST = "suggest"
RUN_MODE_AUTO = "auto"

DEFAULT_RUN_MODE = RUN_MODE_OBSERVE
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_AI_MODEL = "gpt-4o-mini"

DEFAULT_ROOMS = ["study", "bedroom", "living_room", "kitchen"]
