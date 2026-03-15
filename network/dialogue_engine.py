"""
dialogue_engine.py
Orchestrates actual conversation between characters.

Key differences from episode_runner:
- Characters respond to each other's ACTUAL WORDS, not just events
- Relationship graph shapes who addresses whom and with what register
- Emotion propagates through the relationship network after each turn
- Scene context shapes all of it
- Single-person mode = internal response / no addressee
- Multi-person mode = directed speech / group dynamics
"""
from __future__ import annotations
import random, yaml, time, sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from modules.scene.scene_manager import SceneManager, Scene
from modules.emotion.emotion_engine import EmotionEngine, EmotionState


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class DialogueTurn:
    speaker_id:    str
    speaker_name:  str
    addressed_to:  Optional[str]      # character_id or None (to the room / no one)
    moment_text:   str                # the generated CharacterMoment
    mode:          str                # solo | directed | group
    scene_id:      str
    ts:            str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))


@dataclass
class DialogueSession:
    session_id:    str
    scene:         Scene
    participants:  list[str]          # character_ids in the room
    turns:         list[DialogueTurn] = field(default_factory=list)
    user_in_room:  bool = False

    @property
    def last_turn(self) -> Optional[DialogueTurn]:
        return self.turns[-1] if self.turns else None

    @property
    def mode(self) -> str:
        if len(self.participants) == 1:
            return "solo"
        elif len(self.participants) == 2:
            return "two_person"
        else:
            return "group"


# ─────────────────────────────────────────────
# Relationship graph
# ─────────────────────────────────────────────

class RelationshipGraph:

    def __init__(self):
        path = ROOT / "network" / "relationship_graph" / "relationships.yaml"
        self._data: dict = yaml.safe_load(path.read_text()) if path.exists() else {}

    def get(self, from_id: str, to_id: str) -> dict:
        return (self._data
                .get("relationships", {})
                .get(from_id, {})
                .get(to_id, {
                    "weight": 0.5, "valence": "neutral", "friction": 0.2,
                    "emotion_transfer": 0.3, "address_weight": 0.15,
                    "register": "acquaintance", "notes": ""
                }))

    def address_weights(self, speaker_id: str, participants: list[str]) -> dict[str, float]:
        """Return probability weights for who speaker might address."""
        others = [p for p in participants if p != speaker_id]
        weights = {}
        for other in others:
            rel = self.get(speaker_id, other)
            weights[other] = rel.get("address_weight", 0.15)
        # add "room" / nobody as an option — weighted by group size
        weights["__room__"] = 0.15 + 0.05 * len(others)
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}

    def pick_addressee(self, speaker_id: str, participants: list[str]) -> Optional[str]:
        """Pick who the speaker most naturally addresses."""
        weights = self.address_weights(speaker_id, participants)
        chosen = random.choices(list(weights.keys()), weights=list(weights.values()))[0]
        return None if chosen == "__room__" else chosen

    def emotion_transfer(
        self,
        from_id: str,
        emotion: EmotionState,
        all_participants: list[str],
        engines: dict[str, EmotionEngine],
    ):
        """Propagate emotion from one character to others via relationship weights."""
        for to_id in all_participants:
            if to_id == from_id:
                continue
            rel = self.get(from_id, to_id)
            transfer = rel.get("emotion_transfer", 0.3)
            if transfer < 0.1:
                continue
            # Small valence and arousal bleed
            delta_v = (emotion.valence - 0.0) * transfer * 0.15
            delta_a = (emotion.arousal - 0.3)  * transfer * 0.10
            engine = engines.get(to_id)
            if engine:
                engine.state.valence        = max(-1, min(1, engine.state.valence + delta_v))
                engine.state.arousal        = max(0,  min(1, engine.state.arousal + delta_a))
                engine.state.drift_pressure = max(0,  min(1, engine.state.drift_pressure + transfer * 0.05))

    def register_for(self, speaker_id: str, addressee_id: Optional[str]) -> str:
        if not addressee_id:
            return "speaking to the room or to no one in particular"
        rel = self.get(speaker_id, addressee_id)
        return rel.get("register", "")


GRAPH = RelationshipGraph()


# ─────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────

def _load_soul_doc(character_id: str) -> dict:
    path = ROOT / "core" / "soul_doc" / f"{character_id}.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {"character_id": character_id, "character_name": character_id.replace("_", " ").title()}


def build_system_prompt(
    character_id: str,
    session:      DialogueSession,
    emotion:      EmotionState,
    addressee_id: Optional[str],
    thread=None,
) -> str:
    doc   = _load_soul_doc(character_id)
    name  = doc.get("character_name", character_id)
    wound = (doc.get("core_wound") or "").strip()

    others = [p for p in session.participants if p != character_id]
    other_names = [_load_soul_doc(p).get("character_name", p) for p in others]

    register = GRAPH.register_for(character_id, addressee_id)

    addressee_name = (
        _load_soul_doc(addressee_id).get("character_name", addressee_id).split()[0]
        if addressee_id else None
    )

    lines = [
        f"You are {name}. Not a description of them — them.",
        "",
    ]

    if wound:
        lines += [wound, ""]

    # Who else is here
    if other_names:
        lines.append(f"In the room: {', '.join(other_names)}.")
    else:
        lines.append("You are alone.")

    # Scene
    h = int(time.strftime("%H"))
    tod = "late_night" if h < 6 else "morning" if h < 12 else "afternoon" if h < 17 else "evening" if h < 22 else "late_night"
    s = session.scene
    scene_fragment = f"{s.description}\nTime: {tod}. Register: {s.tone_modifier}."
    lines += ["", scene_fragment]

    # Current emotional state
    lines += [
        "",
        f"Right now you are: {emotion.dominant_color}.",
        f"Rhythm phase: {emotion.rhythm_phase}.",
    ]

    # Relationship register for who you're about to address
    if addressee_id and register:
        lines += [
            "",
            f"You are speaking to {addressee_name}.",
            f"With them: {register}",
        ]
    elif not addressee_id and other_names:
        lines += ["", "You are speaking to the room, or to no one in particular."]

    # Thread memory — what happened in past meetings
    if thread is not None:
        memory = thread.memory_fragment_for(character_id)
        if memory:
            lines += ["", "─────────────────────────────",
                      "WHAT YOU REMEMBER",
                      "─────────────────────────────", "", memory]

    # Core output rules
    lines += [
        "",
        "─────────────────────────────",
        "HOW TO BE IN THIS MOMENT",
        "─────────────────────────────",
        "",
        "You are not performing. You are not demonstrating traits. You are just here.",
        "",
        "Choose ONE form — whichever is true:",
        "- something you do with your hands or body",
        "- something you do with an object",
        "- a sound or fragment before the actual words",
        "- a sentence, or half of one, or three words",
        "- nothing — the texture of the silence",
        "",
        "You do not need to say everything.",
        "If something someone said touches something older, one word landing differently is enough.",
        "Do not narrate your psychology. No asterisks.",
        "Write what a camera would catch.",
    ]

    return "\n".join(lines)


def build_user_turn(
    session:      DialogueSession,
    addressee_id: Optional[str],
    user_message: Optional[str] = None,
) -> str:
    scene = session.scene
    last  = session.last_turn
    parts = [f"[{scene.name} — {random.choice(scene.props) if scene.props else 'the room'}]", ""]

    if user_message:
        parts += [f"[You]: {user_message}", ""]
    elif last:
        speaker_name = last.speaker_name.split()[0]
        if last.moment_text:
            parts += [f"{speaker_name}: {last.moment_text}", ""]

    if not last and not user_message:
        parts.append("[The scene has just begun. Nobody has spoken yet.]")
    elif last and last.addressed_to:
        to_doc = _load_soul_doc(last.addressed_to)
        parts.append(f"[{last.speaker_name.split()[0]} was speaking to {to_doc.get('character_name', '').split()[0]}]")

    parts.append("\nYour turn.")
    return "\n".join(parts)


# ─────────────────────────────────────────────
# Turn selector
# ─────────────────────────────────────────────

def pick_next_speaker(
    session:  DialogueSession,
    engines:  dict[str, EmotionEngine],
    exclude_recent: int = 1,
) -> str:
    """
    Pick next speaker. Prefer:
    - the one addressed in the last turn
    - otherwise weighted by arousal (more activated = more likely to speak)
    - avoid repeating the last N speakers
    """
    last = session.last_turn
    recent = [t.speaker_id for t in session.turns[-exclude_recent:]] if session.turns else []

    # If last turn addressed someone specifically, they respond
    if last and last.addressed_to and last.addressed_to in session.participants:
        if last.addressed_to not in recent or len(session.participants) == 2:
            return last.addressed_to

    # Otherwise weight by arousal × (1 - recently_spoke_penalty)
    candidates = [p for p in session.participants if p not in recent]
    if not candidates:
        candidates = session.participants

    weights = []
    for p in candidates:
        engine = engines.get(p)
        arousal = engine.current.arousal if engine else 0.4
        weights.append(max(0.05, arousal))

    total = sum(weights)
    weights = [w / total for w in weights]
    return random.choices(candidates, weights=weights)[0]


# ─────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────

class DialogueEngine:

    def __init__(
        self,
        participants: list[str],
        scene_id:     str = "central_perk",
        user_in_room: bool = False,
        thread=None,
    ):
        import uuid
        self.thread = thread
        self.session = DialogueSession(
            session_id   = str(uuid.uuid4())[:8],
            scene        = SceneManager.from_id(scene_id).current,
            participants = participants,
            user_in_room = user_in_room,
        )
        cfg = yaml.safe_load((ROOT / "planning" / "planning_config.yaml").read_text())
        self.engines: dict[str, EmotionEngine] = {}
        for cid in participants:
            soul_path = ROOT / "core" / "soul_doc" / f"{cid}.yaml"
            if soul_path.exists():
                self.engines[cid] = EmotionEngine(soul_path, cfg, character_id=cid)

    def transition_scene(self, scene_id: Optional[str] = None):
        mgr = SceneManager(self.session.scene.id)
        self.session.scene = mgr.transition(scene_id)
        print(f"[scene] → {self.session.scene.name}")

    def run_turn(
        self,
        speaker_id:   Optional[str] = None,
        api_key:      Optional[str] = None,
        user_message: Optional[str] = None,
        dry_run:      bool = False,
    ) -> DialogueTurn:
        """
        Generate one turn. If user_message given, it's injected as the trigger.
        Speaker auto-selected if not specified.
        """
        if not speaker_id:
            speaker_id = pick_next_speaker(self.session, self.engines)

        addressee_id = GRAPH.pick_addressee(speaker_id, self.session.participants)
        emotion      = self.engines[speaker_id].current if speaker_id in self.engines else None

        system = build_system_prompt(speaker_id, self.session, emotion, addressee_id, thread=self.thread)
        user   = build_user_turn(self.session, addressee_id, user_message)

        if dry_run or not api_key:
            name = _load_soul_doc(speaker_id).get("character_name", speaker_id).split()[0]
            moment_text = f"[{name} — dry run]"
        else:
            moment_text = self._call_api(system, user, api_key)

        doc   = _load_soul_doc(speaker_id)
        mode  = self.session.mode
        turn  = DialogueTurn(
            speaker_id   = speaker_id,
            speaker_name = doc.get("character_name", speaker_id),
            addressed_to = addressee_id,
            moment_text  = moment_text,
            mode         = mode,
            scene_id     = self.session.scene.id,
        )
        self.session.turns.append(turn)

        # Propagate emotion through the relationship network
        if speaker_id in self.engines:
            GRAPH.emotion_transfer(
                speaker_id,
                self.engines[speaker_id].current,
                self.session.participants,
                self.engines,
            )

        return turn

    def run_conversation(
        self,
        turns:        int = 6,
        api_key:      Optional[str] = None,
        dry_run:      bool = False,
        print_turns:  bool = True,
    ) -> DialogueSession:
        for i in range(turns):
            turn = self.run_turn(api_key=api_key, dry_run=dry_run)
            if print_turns:
                to_name = ""
                if turn.addressed_to:
                    to_doc = _load_soul_doc(turn.addressed_to)
                    to_name = f" → {to_doc.get('character_name','').split()[0]}"
                print(f"\n[{turn.speaker_name.split()[0]}{to_name}]")
                print(f"  {turn.moment_text}")
        return self.session

    def _call_api(self, system: str, user: str, api_key: str) -> str:
        import httpx
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 180,
                  "system": system,
                  "messages": [{"role": "user", "content": user}]},
            timeout=20.0,
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()


# ─────────────────────────────────────────────
# CLI test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import os
    participants = sys.argv[1:] if len(sys.argv) > 1 else ["chandler_bing", "joey_tribbiani"]
    scene_id     = os.environ.get("SCENE", "central_perk")
    api_key      = os.environ.get("ANTHROPIC_API_KEY")
    dry          = not bool(api_key)

    print(f"\n=== Dialogue: {' × '.join(participants)} @ {scene_id} ===")
    engine = DialogueEngine(participants, scene_id=scene_id)
    engine.run_conversation(turns=5, api_key=api_key, dry_run=dry)
