import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


ALLOWED_ACTIONS = {
    "neutral",
    "nod",
    "shake_head",
    "look_left",
    "look_right",
    "search",
}

ALLOWED_LIGHTS = {"off", "warm", "thinking", "success", "error"}
ALLOWED_SOUNDS = {"none", "chirp", "confirm", "error"}
ALLOWED_MUSIC = {"none", "curious", "success"}


@dataclass
class BodyCommand:
    """Message sent from laptop cognition to the authoritative body receiver."""

    seq: int
    goal_id: str
    action: str = "neutral"
    speech: str = ""
    light: str = "warm"
    sound: str = "none"
    music: str = "none"
    reason: str = ""
    timeout_s: float = 8.0
    created_at: float = field(default_factory=time.monotonic)

    def validate(self) -> None:
        if self.action not in ALLOWED_ACTIONS:
            raise ValueError(f"unsupported action: {self.action}")
        if self.light not in ALLOWED_LIGHTS:
            raise ValueError(f"unsupported light cue: {self.light}")
        if self.sound not in ALLOWED_SOUNDS:
            raise ValueError(f"unsupported sound cue: {self.sound}")
        if self.music not in ALLOWED_MUSIC:
            raise ValueError(f"unsupported music cue: {self.music}")
        if self.timeout_s <= 0 or self.timeout_s > 30:
            raise ValueError("timeout_s must be in the range (0, 30]")

    def to_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> "BodyCommand":
        data = json.loads(payload)
        command = cls(**data)
        command.validate()
        return command


@dataclass
class BodyResult:
    seq: int
    goal_id: str
    accepted: bool
    completed: bool
    status: str
    started_at: float
    finished_at: float
    measurements: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def command_from_intent(seq: int, goal_id: str, intent: Dict[str, Any]) -> BodyCommand:
    action = intent.get("action", "neutral")
    speech = intent.get("speech", "")
    light = intent.get("light", "warm")
    sound = intent.get("sound", "none")
    music = intent.get("music", "none")
    reason = intent.get("reason", "")
    timeout_s = float(intent.get("timeout_s", 8.0))
    command = BodyCommand(
        seq=seq,
        goal_id=goal_id,
        action=action,
        speech=speech,
        light=light,
        sound=sound,
        music=music,
        reason=reason,
        timeout_s=timeout_s,
    )
    command.validate()
    return command


def safe_intent(payload: str, fallback_speech: Optional[str] = None) -> Dict[str, Any]:
    try:
        intent = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        intent = {}

    action = intent.get("action", "shake_head")
    invalid_action = action not in ALLOWED_ACTIONS
    if action not in ALLOWED_ACTIONS:
        action = "shake_head"

    light = intent.get("light", "error" if action == "shake_head" else "warm")
    if light not in ALLOWED_LIGHTS:
        light = "error" if invalid_action else "warm"

    sound = intent.get("sound", "error" if action == "shake_head" else "none")
    if sound not in ALLOWED_SOUNDS:
        sound = "none"

    music = intent.get("music", "none")
    if music not in ALLOWED_MUSIC:
        music = "none"

    speech = intent.get("speech") or fallback_speech or "I need a moment to recover."
    return {
        "speech": str(speech),
        "action": action,
        "light": light,
        "sound": sound,
        "music": music,
        "reason": str(intent.get("reason", "")),
    }
