"""
event_engine.py  — character-aware
Loads per-character templates and weights from
modules/events/characters/{character_id}.yaml
"""
from __future__ import annotations
import time, random, uuid, yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

ROOT = Path(__file__).parent.parent.parent

DEFAULT_WEIGHTS = {
    "quiet_moment":   0.35,
    "interaction":    0.25,
    "discovery":      0.18,
    "conflict":       0.12,
    "internal_shift": 0.10,
}

DEFAULT_TEMPLATES = {
    "quiet_moment":   ["it's been quiet for a few hours. the kind of quiet that has a texture."],
    "interaction":    ["someone said something. it landed."],
    "discovery":      ["something became clear that wasn't before."],
    "conflict":       ["something that had been avoided surfaced."],
    "internal_shift": ["something shifted. quietly."],
}


@dataclass
class Event:
    id:              str
    ts:              str
    type:            str
    source:          str
    description:     str
    intensity:       float
    valence_push:    float
    arousal_push:    float
    event_score:     float = 0.0
    scene_injection: str   = ""
    habit_trigger:   Optional[str] = None
    outcome:         Optional[str] = None

    def compute_score(self) -> float:
        self.event_score = (
            self.intensity * 50 +
            abs(self.valence_push) * 30 +
            abs(self.arousal_push) * 20
        )
        return self.event_score

    def to_dict(self) -> dict:
        self.compute_score()
        return {k: v for k, v in self.__dict__.items()}


class EventEngine:

    def __init__(
        self,
        config: dict,
        on_event: Optional[Callable[[Event], None]] = None,
        character_id: Optional[str] = None,
    ):
        self.config          = config
        self.on_event        = on_event
        self.character_id    = character_id
        self._last_event_time = time.time()
        self._current_event: Optional[Event] = None
        self._char_cfg: dict = {}

        if character_id:
            self._load_character_config(character_id)

    def _load_character_config(self, character_id: str):
        path = ROOT / "modules" / "events" / "characters" / f"{character_id}.yaml"
        if path.exists():
            self._char_cfg = yaml.safe_load(path.read_text()) or {}

    @property
    def _weights(self) -> dict:
        w = self._char_cfg.get("weights", DEFAULT_WEIGHTS)
        total = sum(w.values())
        return {k: v / total for k, v in w.items()}

    @property
    def _intensity_range(self) -> list:
        return self._char_cfg.get("intensity_range",
            self.config.get("event_intensity_range", [0.1, 0.6]))

    @property
    def _templates(self) -> dict:
        return self._char_cfg.get("templates", DEFAULT_TEMPLATES)

    def tick(self, emotion_state) -> Optional[Event]:
        interval = self.config.get("event_interval_minutes", 90)
        pressure_factor = 1.0 - emotion_state.drift_pressure * 0.3
        effective = interval * pressure_factor
        if (time.time() - self._last_event_time) / 60.0 >= effective:
            event = self._generate(emotion_state)
            self._last_event_time = time.time()
            self._current_event = event
            if self.on_event:
                self.on_event(event)
            return event
        return None

    def inject(self, event_dict: dict) -> Event:
        event = Event(
            id           = event_dict.get("id", str(uuid.uuid4())[:8]),
            ts           = time.strftime("%Y-%m-%dT%H:%M:%S"),
            type         = event_dict.get("type", "interaction"),
            source       = event_dict.get("source", "user_inject"),
            description  = event_dict["description"],
            intensity    = float(event_dict.get("intensity", 0.4)),
            valence_push = float(event_dict.get("valence_push", 0.0)),
            arousal_push = float(event_dict.get("arousal_push", 0.0)),
            scene_injection = event_dict.get("scene_injection", event_dict["description"]),
            habit_trigger   = event_dict.get("habit_trigger"),
        )
        event.compute_score()
        self._current_event = event
        if self.on_event:
            self.on_event(event)
        return event

    @property
    def current_score(self) -> float:
        return self._current_event.event_score if self._current_event else 0.0

    def _generate(self, emotion_state) -> Event:
        weights = self._weights.copy()

        # Emotion-state adjustments to weights
        if emotion_state.arousal < 0.35:
            weights["quiet_moment"] = weights.get("quiet_moment", 0.35) + 0.10
            weights["conflict"]     = max(0.02, weights.get("conflict", 0.12) - 0.05)
        if emotion_state.valence < -0.3:
            weights["internal_shift"] = weights.get("internal_shift", 0.10) + 0.08

        # Normalise
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        event_type = random.choices(list(weights.keys()), weights=list(weights.values()))[0]

        templates  = self._templates.get(event_type, DEFAULT_TEMPLATES.get(event_type, ["something happened."]))
        desc       = random.choice(templates)

        imin, imax = self._intensity_range
        pressure_boost = emotion_state.drift_pressure * 0.15
        intensity = max(imin, min(imax + pressure_boost,
                                   (imin + imax) / 2 + random.uniform(-0.08, 0.08)))

        # Valence/arousal push: infer from event type
        vp_map = {"quiet_moment":-0.04,"interaction":0.05,"discovery":0.08,"conflict":-0.18,"internal_shift":0.10}
        ap_map = {"quiet_moment":-0.12,"interaction":0.08,"discovery":0.10,"conflict":0.28,"internal_shift":0.05}
        vp = vp_map.get(event_type, 0.0) * (1 + random.uniform(-0.2, 0.2))
        ap = ap_map.get(event_type, 0.0) * (1 + random.uniform(-0.2, 0.2))

        event = Event(
            id           = str(uuid.uuid4())[:8],
            ts           = time.strftime("%Y-%m-%dT%H:%M:%S"),
            type         = event_type,
            source       = "scheduled",
            description  = desc,
            intensity    = intensity,
            valence_push = round(vp, 3),
            arousal_push = round(ap, 3),
            scene_injection = desc,
        )
        event.compute_score()
        return event
