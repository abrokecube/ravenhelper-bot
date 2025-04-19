from enum import Enum

class AlertType(Enum):
    DESYNC = "desync"
    TITLE = "title"
    CATEGORY = "category"
    # POLL = "poll"
    # PREDICTION = "prediction"
    LIVE = "live"
    OFFLINE = "offline"
    PINS = "pins"
