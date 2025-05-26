from enum import Enum

class AlertType(Enum):
    DESYNC = "desync"
    TITLE = "title"
    CATEGORY = "category"
    POLLS = "polls"
    LIVE = "live"
    OFFLINE = "offline"
    PINS = "pins"
    UNPINS = "unpins"
    RAIDS = "raids"
    PREDICTIONS = "predictions"
