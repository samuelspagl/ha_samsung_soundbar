from enum import Enum


class SpeakerIdentifier(Enum):
    CENTER = "Spk_Center"
    SIDE = "Spk_Side"
    WIDE = "Spk_Wide"
    FRONT_TOP = "Spk_Front_Top"
    REAR = "Spk_Rear"
    REAR_TOP = "Spk_Rear_Top"


class RearSpeakerMode(Enum):
    FRONT = "Front"
    REAR = "Rear"
