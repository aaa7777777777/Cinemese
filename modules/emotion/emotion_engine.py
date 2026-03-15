"""
emotion_engine.py — character-aware
Loads per-character baselines, rhythm params, and thresholds from
modules/emotion/characters/{character_id}.yaml
"""
from __future__ import annotations
import time, yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

ROOT = Path(__file__).parent.parent.parent

RHYTHM_PHASES = [("trough",60),("rising",60),("peak",30),("falling",90)]
RHYTHM_NUDGES = {
    "trough":  {"valence":-0.05,"arousal":-0.08},
    "rising":  {"valence":+0.04,"arousal":+0.06},
    "peak":    {"valence":+0.03,"arousal":+0.05},
    "falling": {"valence":-0.02,"arousal":-0.04},
}
DOMINANT_COLORS = [
    (-1.0,-0.5, 0.0,0.4, "the specific quiet of being alone at night that doesn't have a name"),
    (-1.0,-0.3, 0.5,1.0, "running fast to stay in the same place"),
    (-0.3, 0.1, 0.0,0.35,"low and still, not quite sad"),
    ( 0.1, 0.4, 0.0,0.4, "quietly okay, not pushing it"),
    ( 0.4, 1.0, 0.0,0.5, "something like ease, held loosely"),
    ( 0.1, 1.0, 0.6,1.0, "more present than usual, slightly electric"),
    (-1.0, 1.0, 0.0,1.0, "somewhere in the middle of things"),
]


@dataclass
class EmotionState:
    valence:        float = 0.0
    arousal:        float = 0.3
    dominant_color: str   = "somewhere in the middle of things"
    drift_pressure: float = 0.2
    rhythm_phase:   str   = "trough"
    micro_score:    float = 0.0
    last_updated:   float = field(default_factory=time.time)

    def compute_micro_score(self) -> float:
        return abs(self.valence)*40 + self.arousal*35 + self.drift_pressure*25

    def to_prompt_fragment(self) -> str:
        return f"{self.dominant_color} — rhythm: {self.rhythm_phase}, pressure: {self.drift_pressure:.2f}"


@dataclass
class EmotionDelta:
    valence_delta:    float = 0.0
    arousal_delta:    float = 0.0
    pressure_delta:   float = 0.0
    interrupt_rhythm: bool  = False


class EmotionEngine:

    def __init__(
        self,
        soul_doc_path: Path,
        config: dict,
        on_writeback: Optional[Callable[[dict], None]] = None,
        character_id: Optional[str] = None,
    ):
        self.soul_doc_path = soul_doc_path
        self.config        = config
        self.on_writeback  = on_writeback
        self.state         = EmotionState()
        self._rhythm_timer = time.time()
        self._rhythm_idx   = 0
        self._writeback_timers: dict[str, float] = {}
        self._char_cfg: dict = {}
        self._trait_cache: dict = {}

        # Load character config if available
        cid = character_id or soul_doc_path.stem
        cfg_path = ROOT / "modules" / "emotion" / "characters" / f"{cid}.yaml"
        if cfg_path.exists():
            self._char_cfg = yaml.safe_load(cfg_path.read_text()) or {}

        self._init_from_soul_doc()

    def _init_from_soul_doc(self):
        try:
            raw = yaml.safe_load(self.soul_doc_path.read_text()) or {}
            self._trait_cache = raw.get("trait_weights", {})
        except Exception:
            self._trait_cache = {}

        # Use character-specific baseline if available, else derive from traits
        baseline = self._char_cfg.get("baseline", {})
        t = self._trait_cache

        self.state.valence = baseline.get("valence",
            t.get("self_worth",0.5)*0.4 + t.get("warmth_when_safe",0.5)*0.3
            - t.get("cynicism",0.3)*0.2 - t.get("fear_of_permanence",0.5)*0.1
        )
        self.state.arousal = baseline.get("arousal",
            t.get("deflection_via_humor",0.5)*0.3 + t.get("genuine_vulnerability",0.3)*0.2
        )
        self.state.drift_pressure = baseline.get("pressure", 0.20)

        self._clamp()
        self._refresh_color()
        self.state.micro_score = self.state.compute_micro_score()

    # ── Public ────────────────────────────────────────────────────────────────

    def tick(self):
        self._advance_rhythm()
        self._check_writebacks()
        self._refresh_color()
        self.state.micro_score = self.state.compute_micro_score()
        self.state.last_updated = time.time()

    def receive_event(self, event: dict) -> EmotionDelta:
        intensity = event.get("intensity", 0.3)
        delta = EmotionDelta(
            valence_delta    = event.get("valence_push", 0.0) * intensity,
            arousal_delta    = event.get("arousal_push", 0.0) * intensity,
            pressure_delta   = intensity * 0.4,
            interrupt_rhythm = intensity > 0.7,
        )
        self._apply_delta(delta)
        return delta

    def receive_planning_override(self, override: dict):
        if "valence"  in override: self.state.valence        = float(override["valence"])
        if "arousal"  in override: self.state.arousal        = float(override["arousal"])
        if "pressure" in override: self.state.drift_pressure = float(override["pressure"])
        self._clamp()
        self._refresh_color()

    @property
    def current(self) -> EmotionState:
        return self.state

    # ── Internal ──────────────────────────────────────────────────────────────

    def _advance_rhythm(self):
        phase, duration = RHYTHM_PHASES[self._rhythm_idx]
        rhy = self._char_cfg.get("rhythm", {})
        scale = rhy.get("period_scale", 1.0)

        # Flatten peaks for high-deflection chars
        flatten_trait = rhy.get("peak_flatten_trait")
        if flatten_trait:
            scale *= (1 + self._trait_cache.get(flatten_trait, 0.5) * 0.3)

        if (time.time() - self._rhythm_timer) / 60.0 >= duration * scale:
            self._rhythm_idx = (self._rhythm_idx + 1) % len(RHYTHM_PHASES)
            self._rhythm_timer = time.time()
            self._apply_rhythm_nudge()
        self.state.rhythm_phase = RHYTHM_PHASES[self._rhythm_idx][0]

    def _apply_rhythm_nudge(self):
        phase = RHYTHM_PHASES[self._rhythm_idx][0]
        nudge = RHYTHM_NUDGES[phase]
        rhy   = self._char_cfg.get("rhythm", {})

        # Deepen trough for high-vulnerability chars
        deepen_trait = rhy.get("trough_deepen_trait")
        scale = 1.0
        if phase == "trough" and deepen_trait:
            scale = 1.0 + (self._trait_cache.get(deepen_trait, 0.3) - 0.3) * 0.5

        self.state.valence  += nudge["valence"]  * scale
        self.state.arousal  += nudge["arousal"]  * scale
        self._clamp()

    def _apply_delta(self, delta: EmotionDelta):
        self.state.valence        += delta.valence_delta
        self.state.arousal        += delta.arousal_delta
        self.state.drift_pressure += delta.pressure_delta
        if delta.interrupt_rhythm:
            self._rhythm_timer = time.time()
        self._clamp()

    def _clamp(self):
        self.state.valence        = max(-1.0, min(1.0, self.state.valence))
        self.state.arousal        = max(0.0,  min(1.0, self.state.arousal))
        self.state.drift_pressure = max(0.0,  min(1.0, self.state.drift_pressure))

    def _refresh_color(self):
        v, a = self.state.valence, self.state.arousal
        for vmin, vmax, amin, amax, color in DOMINANT_COLORS:
            if vmin <= v <= vmax and amin <= a <= amax:
                self.state.dominant_color = color
                return

    def _check_writebacks(self):
        if not self.on_writeback:
            return
        thresholds = (self._char_cfg.get("writeback") or
                      self.config.get("emotion_writeback_thresholds") or {})
        now = time.time()
        checks = {
            "low_valence":  (self.state.valence < thresholds.get("valence_low",-0.6),
                             thresholds.get("valence_low_minutes",20)*60,
                             {"closest_trait":"self_worth","delta":-0.02}),
            "high_arousal": (self.state.arousal > thresholds.get("arousal_high",0.8),
                             thresholds.get("arousal_high_minutes",10)*60,
                             {"closest_trait":"deflection_via_humor","delta":+0.01}),
            "high_pressure":(self.state.drift_pressure > thresholds.get("pressure_high",0.75),
                             thresholds.get("pressure_high_minutes",15)*60,
                             {"closest_trait":"fear_of_permanence","delta":+0.01}),
        }
        for key, (cond, dur, meta) in checks.items():
            if cond:
                self._writeback_timers.setdefault(key, now)
                if now - self._writeback_timers[key] >= dur:
                    max_d = thresholds.get("auto_node_max_delta", 0.04)
                    self.on_writeback({
                        "id":    f"auto_{key}_{int(now)}",
                        "ts":    time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "event": f"sustained {self.state.dominant_color}",
                        "delta": {meta["closest_trait"]: min(abs(meta["delta"]), max_d) * (1 if meta["delta"]>0 else -1)},
                        "locked": False,
                        "note":  f"emotion_engine auto-write — {key}",
                    })
                    del self._writeback_timers[key]
            else:
                self._writeback_timers.pop(key, None)
