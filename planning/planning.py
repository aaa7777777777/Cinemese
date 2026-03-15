"""
planning.py
Top-level orchestrator. Always running.
Watches config, ticks emotion + event engines,
fires skills, injects into dialogue context.
"""

from __future__ import annotations
import os
import sys
import time
import json
import threading
import yaml
from pathlib import Path
from typing import Optional

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from modules.emotion.emotion_engine import EmotionEngine, EmotionState
from modules.events.event_engine import EventEngine, Event


# ─────────────────────────────────────────────
# Config loader (hot-reloads on file change)
# ─────────────────────────────────────────────

class ConfigWatcher:
    def __init__(self, path: Path):
        self.path = path
        self._data: dict = {}
        self._mtime: float = 0.0
        self.reload()

    def reload(self) -> bool:
        mtime = self.path.stat().st_mtime
        if mtime != self._mtime:
            self._data = yaml.safe_load(self.path.read_text()) or {}
            self._mtime = mtime
            return True
        return False

    def get(self) -> dict:
        self.reload()
        return self._data


# ─────────────────────────────────────────────
# Soul doc writer (appends auto-generated nodes)
# ─────────────────────────────────────────────

def make_soul_doc_writer(soul_doc_path: Path):
    def write_node(node: dict):
        try:
            doc = yaml.safe_load(soul_doc_path.read_text()) or {}
            nodes = doc.setdefault("life_nodes", [])
            nodes.append(node)
            soul_doc_path.write_text(yaml.dump(doc, allow_unicode=True))
            print(f"[planning] soul_doc writeback: {node['id']}")
        except Exception as e:
            print(f"[planning] soul_doc write error: {e}")
    return write_node


# ─────────────────────────────────────────────
# Skill dispatcher
# ─────────────────────────────────────────────

class SkillDispatcher:
    """
    In production this calls the mobile push API or local notification system.
    Here it writes to a shared state file that the frontend polls.
    """

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.queue: list[dict] = []

    def dispatch(self, skill_type: str, content: str, emotion: EmotionState, event: Optional[Event] = None):
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "skill_type": skill_type,
            "content": content,
            "emotion_color": emotion.dominant_color,
            "arousal": round(emotion.arousal, 3),
            "valence": round(emotion.valence, 3),
            "event_type": event.type if event else None,
            "event_desc": event.description if event else None,
        }
        self.queue.append(payload)
        self._flush()
        print(f"[skill:{skill_type}] {content[:60]}...")

    def _flush(self):
        try:
            self.output_path.write_text(
                json.dumps(self.queue[-20:], ensure_ascii=False, indent=2)
            )
        except Exception:
            pass


# ─────────────────────────────────────────────
# Planning state — shared across modules
# ─────────────────────────────────────────────

class PlanningState:
    def __init__(self):
        self.emotion: Optional[EmotionState] = None
        self.last_event: Optional[Event] = None
        self.active_scene_injection: str = ""
        self.active_habit_trigger: Optional[str] = None
        self._lock = threading.Lock()

    def update_emotion(self, state: EmotionState):
        with self._lock:
            self.emotion = state

    def update_event(self, event: Event):
        with self._lock:
            self.last_event = event
            self.active_scene_injection = event.scene_injection
            self.active_habit_trigger   = event.habit_trigger

    def to_context_patch(self) -> dict:
        """Returns dict that patches into NowContext for next dialogue call."""
        with self._lock:
            return {
                "recent_event":   self.active_scene_injection or None,
                "emotion_color":  self.emotion.dominant_color if self.emotion else None,
                "emotion_arousal": round(self.emotion.arousal, 3) if self.emotion else None,
                "emotion_valence": round(self.emotion.valence, 3) if self.emotion else None,
                "active_habit":   self.active_habit_trigger,
            }


# ─────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────

class Planning:

    TICK_INTERVAL = 60  # seconds

    def __init__(
        self,
        character_id: str,
        soul_doc_path: Path,
        config_path: Path,
        output_path: Path,
    ):
        self.character_id   = character_id
        self.soul_doc_path  = soul_doc_path
        self.config_watcher = ConfigWatcher(config_path)
        self.state          = PlanningState()
        self.dispatcher     = SkillDispatcher(output_path / "skill_queue.json")

        cfg = self.config_watcher.get()

        self.emotion_engine = EmotionEngine(
            soul_doc_path = soul_doc_path,
            config        = cfg,
            on_writeback  = make_soul_doc_writer(soul_doc_path),
        )

        self.event_engine = EventEngine(
            config   = cfg,
            on_event = self._on_event,
        )

        # Write context patch file so dialogue layer can read it
        self.context_patch_path = output_path / "context_patch.json"

    def start(self):
        print(f"[planning] starting for {self.character_id}")
        try:
            while True:
                self._tick()
                time.sleep(self.TICK_INTERVAL)
        except KeyboardInterrupt:
            print("[planning] stopped.")

    def inject_event(self, event_dict: dict):
        """External call: agent collision, user dashboard, or network episode."""
        event = self.event_engine.inject(event_dict)
        return event

    def inject_emotion_override(self, override: dict):
        """External call: user adjusts emotion via planning UI."""
        self.emotion_engine.receive_planning_override(override)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _tick(self):
        cfg = self.config_watcher.get()

        # Reload engine configs if changed
        self.emotion_engine.config = cfg
        self.event_engine.config   = cfg

        # Check for user-forced overrides in config
        force_emotion = cfg.get("force_emotion")
        if force_emotion:
            self.emotion_engine.receive_planning_override(force_emotion)

        force_event = cfg.get("force_event")
        if force_event:
            self.event_engine.inject(force_event)

        # Tick emotion
        self.emotion_engine.tick()
        emotion = self.emotion_engine.current
        self.state.update_emotion(emotion)

        # Tick events
        event = self.event_engine.tick(emotion)
        if event:
            # Emotion reacts to event
            self.emotion_engine.receive_event(event.to_dict())
            # Update planning state
            self.state.update_event(event)
            # Dispatch a skill
            self._dispatch_skill_for_event(event, emotion)

        # Write context patch for dialogue layer
        patch = self.state.to_context_patch()
        try:
            self.context_patch_path.write_text(
                json.dumps(patch, ensure_ascii=False, indent=2)
            )
        except Exception:
            pass

        # Log
        print(
            f"[tick] emotion={emotion.dominant_color[:30]:<30} "
            f"v={emotion.valence:+.2f} a={emotion.arousal:.2f} "
            f"score={emotion.micro_score:.0f}"
            + (f" | event={event.type}({event.event_score:.0f})" if event else "")
        )

    def _on_event(self, event: Event):
        print(f"[event:{event.type}] {event.description[:60]}")

    def _dispatch_skill_for_event(self, event: Event, emotion: EmotionState):
        """Choose skill type based on event + emotion, dispatch content."""
        cfg = self.config_watcher.get()
        schedule = cfg.get("skill_schedule", {})

        # Choose modality
        if event.type == "quiet_moment" and schedule.get("float_bubble", {}).get("enabled"):
            skill = "float_bubble"
        elif event.type in ("conflict", "internal_shift") and schedule.get("intrusive_thought", {}).get("enabled"):
            if _in_time_window(schedule["intrusive_thought"].get("window", "00:00-23:59")):
                skill = "intrusive_thought"
            else:
                skill = "push_note"
        else:
            skill = "push_note"

        # Content: use event description as raw seed
        # In production: call api.chat.generate_moment() for in-character voice
        content = _voice_event_description(event, emotion)
        self.dispatcher.dispatch(skill, content, emotion, event)


def _in_time_window(window: str) -> bool:
    try:
        start_s, end_s = window.split("-")
        now_h, now_m = time.localtime().tm_hour, time.localtime().tm_min
        now_t = now_h * 60 + now_m
        sh, sm = map(int, start_s.split(":"))
        eh, em = map(int, end_s.split(":"))
        return (sh * 60 + sm) <= now_t <= (eh * 60 + em)
    except Exception:
        return True


def _voice_event_description(event: Event, emotion: EmotionState) -> str:
    """
    Minimal in-character voicing of an event.
    In production: replaced by api.chat.generate_moment() call.
    """
    if event.type == "quiet_moment":
        return event.description
    elif event.type == "internal_shift":
        return f"{event.description} he didn't mention it."
    elif event.type == "conflict":
        return f"something came up. {event.description}"
    else:
        return event.description


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    character_id = sys.argv[1] if len(sys.argv) > 1 else "chandler_bing"

    soul_doc_path = ROOT / "core" / "soul_doc" / f"{character_id}.yaml"
    config_path   = ROOT / "planning" / "planning_config.yaml"
    output_path   = ROOT / "planning"

    # Create a minimal soul_doc yaml if only .ts exists
    if not soul_doc_path.exists():
        soul_doc_path = ROOT / "core" / "soul_doc" / "chandler_base.yaml"
        soul_doc_path.write_text(yaml.dump({
            "character_id": character_id,
            "trait_weights": {
                "deflection_via_humor":  0.88,
                "genuine_vulnerability": 0.31,
                "loyalty":               0.92,
                "self_worth":            0.38,
                "fear_of_permanence":    0.71,
                "warmth_when_safe":      0.64,
                "cynicism":              0.61,
            },
            "life_nodes": [],
        }))

    planner = Planning(character_id, soul_doc_path, config_path, output_path)
    planner.start()
