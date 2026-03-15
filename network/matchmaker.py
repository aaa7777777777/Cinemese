"""
matchmaker.py
Scores agents, gates collisions, pairs for episode_runner.
"""

from __future__ import annotations
import time
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

COLLISION_THRESHOLD   = 80
MIN_REINTERACT_HOURS  = 6
MAX_COMBINED_SCORE    = COLLISION_THRESHOLD * 2     # 160
POST_COLLISION_BUDGET = 1.20                        # max 20% spike

COMPATIBLE_EVENT_PAIRS = {
    frozenset({"quiet_moment"}),
    frozenset({"quiet_moment", "internal_shift"}),
    frozenset({"interaction"}),
    frozenset({"interaction", "discovery"}),
    frozenset({"discovery", "internal_shift"}),
}


@dataclass
class AgentPublicProfile:
    id:                     str
    character_name:         str
    world_tags:             list[str]
    emotion_color:          str
    last_event_type:        str
    tension_score:          float        # event_score + micro_score
    available:              bool
    last_interaction:       dict         # {partner_id: timestamp}
    updated_at:             float = field(default_factory=time.time)


class Matchmaker:

    def __init__(self, profiles_dir: Path, config: dict):
        self.profiles_dir = profiles_dir
        self.config       = config
        self._profiles: dict[str, AgentPublicProfile] = {}

    def load_profiles(self):
        for path in self.profiles_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                self._profiles[data["id"]] = AgentPublicProfile(**data)
            except Exception as e:
                print(f"[matchmaker] failed to load {path.name}: {e}")

    def find_match(self, agent_id: str) -> Optional[AgentPublicProfile]:
        self.load_profiles()
        agent = self._profiles.get(agent_id)
        if not agent or not agent.available:
            return None

        candidates = []
        for other in self._profiles.values():
            if not self._gate(agent, other):
                continue
            delta = abs(other.tension_score - agent.tension_score)
            candidates.append((delta, other))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def _gate(self, a: AgentPublicProfile, b: AgentPublicProfile) -> bool:
        if b.id == a.id:                         return False
        if not b.available:                      return False
        if abs(a.tension_score - b.tension_score) > COLLISION_THRESHOLD: return False
        if a.tension_score + b.tension_score > MAX_COMBINED_SCORE:       return False
        if not self._compatible_events(a.last_event_type, b.last_event_type): return False
        if not self._cooldown_ok(a, b):          return False
        return True

    def _compatible_events(self, type_a: str, type_b: str) -> bool:
        pair = frozenset({type_a, type_b})
        # conflict only allowed if config permits high intensity
        if "conflict" in pair:
            return self.config.get("allow_high_intensity", False)
        return any(pair <= p or pair == p for p in COMPATIBLE_EVENT_PAIRS)

    def _cooldown_ok(self, a: AgentPublicProfile, b: AgentPublicProfile) -> bool:
        last_ts = a.last_interaction.get(b.id, 0)
        hours_elapsed = (time.time() - last_ts) / 3600
        return hours_elapsed >= MIN_REINTERACT_HOURS

    def check_post_collision_budget(
        self,
        agent_a_score: float,
        agent_b_score: float,
        delta_a: float,
        delta_b: float,
    ) -> tuple[float, float]:
        """
        Clamp deltas so combined post-collision score ≤ pre * POST_COLLISION_BUDGET.
        Returns (safe_delta_a, safe_delta_b).
        """
        pre  = agent_a_score + agent_b_score
        post = (agent_a_score + delta_a) + (agent_b_score + delta_b)
        ceiling = pre * POST_COLLISION_BUDGET

        if post <= ceiling:
            return delta_a, delta_b

        # Scale down proportionally
        excess = post - ceiling
        scale  = 1.0 - (excess / (delta_a + delta_b + 1e-9))
        scale  = max(0.0, scale)
        return delta_a * scale, delta_b * scale
