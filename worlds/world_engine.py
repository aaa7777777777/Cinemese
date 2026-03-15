"""
world_engine.py

Computes worldview distance between two agents and determines
collision outcome — smooth, friction, displacement, or mutual displacement.

Displacement = one agent loses their event track and emotion resets to zero.
They don't lose their soul_doc (memory stays), but their event_engine
and emotion_engine restart from baseline zero.
The track break is permanent — they can't go back.
"""
from __future__ import annotations
import yaml
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
WORLDS_DIR = ROOT / "worlds" / "definitions"

# Nation distance matrix — 0.0 = same, 1.0 = maximally different
# Ordered by cultural/linguistic/historical proximity
NATION_DISTANCES = {
    ("china",  "china"):  0.00,
    ("japan",  "japan"):  0.00,
    ("usa",    "usa"):    0.00,
    ("uk",     "uk"):     0.00,
    ("china",  "japan"):  0.28,
    ("japan",  "china"):  0.28,
    ("usa",    "uk"):     0.15,
    ("uk",     "usa"):    0.15,
    ("china",  "usa"):    0.75,
    ("usa",    "china"):  0.75,
    ("china",  "uk"):     0.70,
    ("uk",     "china"):  0.70,
    ("japan",  "usa"):    0.60,
    ("usa",    "japan"):  0.60,
    ("japan",  "uk"):     0.58,
    ("uk",     "japan"):  0.58,
}

# Era distance — decades apart → normalized 0–1
ERA_MAP = {
    "1900s": 1900, "1910s": 1910, "1920s": 1920, "1930s": 1930,
    "1940s": 1940, "1950s": 1950, "1960s": 1960, "1970s": 1970,
    "1980s": 1980, "1990s": 1990, "2000s": 2000, "2010s": 2010,
    "2020s": 2020,
}

# Environment distance
ENV_DISTANCES = {
    ("urban",    "urban"):    0.00,
    ("suburban", "suburban"): 0.00,
    ("rural",    "rural"):    0.00,
    ("school",   "school"):   0.00,
    ("urban",    "suburban"): 0.20,
    ("suburban", "urban"):    0.20,
    ("urban",    "rural"):    0.70,
    ("rural",    "urban"):    0.70,
    ("suburban", "rural"):    0.55,
    ("rural",    "suburban"): 0.55,
    ("school",   "urban"):    0.25,
    ("urban",    "school"):   0.25,
    ("school",   "rural"):    0.60,
    ("rural",    "school"):   0.60,
    ("school",   "suburban"): 0.30,
    ("suburban", "school"):   0.30,
}

# Collision outcome thresholds
SMOOTH_MAX       = 0.30
FRICTION_MAX     = 0.55
DISPLACE_ONE_MAX = 0.75
# > 0.75 = both affected


@dataclass
class WorldDef:
    id:                str
    label:             str
    nation:            str
    era:               str
    env:               str
    coordinates:       dict
    economic_register: str
    social_register:   str
    background_noise:  str

    def to_prompt_fragment(self) -> str:
        return (
            f"Your world: {self.label}.\n\n"
            f"Economy and money: {self.economic_register}\n\n"
            f"How society works: {self.social_register}\n\n"
            f"What's in the air: {self.background_noise}"
        )


@dataclass
class CollisionResult:
    gap:              float
    outcome:          str   # smooth | friction | displace_one | displace_both
    displaced_agent:  Optional[str]   # agent_id of the displaced one, if any
    both_displaced:   bool
    unstable_agent:   Optional[str]   # marked unstable but not yet displaced
    description:      str             # human-readable summary


@dataclass
class TrackStatus:
    agent_id:        str
    status:          str    # intact | displaced | unstable
    displaced_at:    Optional[str] = None
    displaced_by:    Optional[str] = None   # world_id of the other agent
    displacement_count: int = 0
    note:            str = ""


# ─────────────────────────────────────────────
# World loader
# ─────────────────────────────────────────────

_WORLD_CACHE: dict[str, WorldDef] = {}

def load_world(world_id: str) -> Optional[WorldDef]:
    if world_id in _WORLD_CACHE:
        return _WORLD_CACHE[world_id]
    path = WORLDS_DIR / f"{world_id}.yaml"
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text())
    w = WorldDef(**data)
    _WORLD_CACHE[world_id] = w
    return w

def list_worlds() -> list[dict]:
    result = []
    for path in WORLDS_DIR.glob("*.yaml"):
        data = yaml.safe_load(path.read_text())
        result.append({"id": data["id"], "label": data["label"],
                        "nation": data["nation"], "era": data["era"],
                        "env": data["env"]})
    return sorted(result, key=lambda x: (x["nation"], x["era"]))


# ─────────────────────────────────────────────
# Distance computation
# ─────────────────────────────────────────────

def nation_distance(n_a: str, n_b: str) -> float:
    return NATION_DISTANCES.get((n_a, n_b), 0.80)

def era_distance(e_a: str, e_b: str) -> float:
    ya = ERA_MAP.get(e_a, 2000)
    yb = ERA_MAP.get(e_b, 2000)
    decade_gap = abs(ya - yb) / 10
    return min(1.0, decade_gap / 8.0)   # 80 years = max distance

def env_distance(env_a: str, env_b: str) -> float:
    return ENV_DISTANCES.get((env_a, env_b), 0.50)

def worldview_gap(world_a: WorldDef, world_b: WorldDef) -> float:
    nd = nation_distance(world_a.nation, world_b.nation)
    ed = era_distance(world_a.era, world_b.era)
    vd = env_distance(world_a.env, world_b.env)
    gap = nd * 0.40 + ed * 0.35 + vd * 0.25
    return round(min(1.0, gap), 4)


# ─────────────────────────────────────────────
# Resilience
# ─────────────────────────────────────────────

def compute_resilience(soul_doc: dict) -> float:
    t = soul_doc.get("trait_weights", {})
    r = (
        t.get("quiet_resilience",    0.5) * 0.35 +
        t.get("self_sufficiency",    0.5) * 0.30 +
        t.get("adaptability",        0.4) * 0.20 +
        t.get("identity_stability",  0.5) * 0.15
    )
    return round(min(1.0, r), 3)


# ─────────────────────────────────────────────
# Collision engine
# ─────────────────────────────────────────────

def compute_collision(
    agent_a_id:    str,
    world_a:       WorldDef,
    soul_a:        dict,
    track_a:       TrackStatus,
    agent_b_id:    str,
    world_b:       WorldDef,
    soul_b:        dict,
    track_b:       TrackStatus,
) -> CollisionResult:
    """
    Core collision algorithm.
    Determines outcome based on worldview_gap and track history.
    """
    gap = worldview_gap(world_a, world_b)
    res_a = compute_resilience(soul_a)
    res_b = compute_resilience(soul_b)

    # Second meeting modifier: already displaced agents are more vulnerable
    second_meeting = (track_a.displacement_count > 0 or track_b.displacement_count > 0)
    effective_gap = gap * (1.25 if second_meeting else 1.0)
    effective_gap = min(1.0, effective_gap)

    # ── SMOOTH ────────────────────────────────────────────
    if effective_gap < SMOOTH_MAX:
        return CollisionResult(
            gap              = gap,
            outcome          = "smooth",
            displaced_agent  = None,
            both_displaced   = False,
            unstable_agent   = None,
            description      = (
                f"世界差距 {gap:.2f}，小于阈值。"
                "两人可以相遇，有摩擦但不造成轨道损伤。"
            ),
        )

    # ── FRICTION ──────────────────────────────────────────
    if effective_gap < FRICTION_MAX:
        # Emotion drift but no displacement
        weaker = agent_a_id if res_a < res_b else agent_b_id
        return CollisionResult(
            gap              = gap,
            outcome          = "friction",
            displaced_agent  = None,
            both_displaced   = False,
            unstable_agent   = weaker,
            description      = (
                f"世界差距 {gap:.2f}。"
                f"{weaker} 的情绪轨道受到冲击，但事件轨道完整。"
                "下次相遇风险升高。"
            ),
        )

    # ── DISPLACE ONE ──────────────────────────────────────
    if effective_gap < DISPLACE_ONE_MAX:
        # The one with lower resilience loses their track
        if res_a <= res_b:
            displaced, survivor = agent_a_id, agent_b_id
            d_res, s_res        = res_a, res_b
        else:
            displaced, survivor = agent_b_id, agent_a_id
            d_res, s_res        = res_b, res_a

        # If second meeting and the survivor was already unstable, they're also at risk
        survivor_unstable = second_meeting and (
            (survivor == agent_a_id and track_a.status == "unstable") or
            (survivor == agent_b_id and track_b.status == "unstable")
        )

        return CollisionResult(
            gap              = gap,
            outcome          = "displace_one",
            displaced_agent  = displaced,
            both_displaced   = False,
            unstable_agent   = survivor if survivor_unstable else None,
            description      = (
                f"世界差距 {gap:.2f}。"
                f"{displaced}（韧性 {d_res:.2f}）失去事件轨道，情绪归零。"
                f"{survivor}（韧性 {s_res:.2f}）完整。"
                + (f" {survivor} 的轨道被标记为不稳定。" if survivor_unstable else "")
            ),
        )

    # ── DISPLACE BOTH ─────────────────────────────────────
    # gap > 0.75 or effective_gap > DISPLACE_ONE_MAX with second meeting
    weaker_first = agent_a_id if res_a <= res_b else agent_b_id
    return CollisionResult(
        gap              = gap,
        outcome          = "displace_both",
        displaced_agent  = weaker_first,
        both_displaced   = True,
        unstable_agent   = None,
        description      = (
            f"世界差距 {gap:.2f}。差距过大或已有位移历史。"
            f"两人都将失去事件轨道并情绪归零。"
            f"{weaker_first} 先失去，另一方随后。"
            "再也回不去原本事件。"
        ),
    )


# ─────────────────────────────────────────────
# Track status manager
# ─────────────────────────────────────────────

class TrackManager:
    """
    Persists track status for all agents.
    Stored in worlds/track_status.yaml
    """
    def __init__(self):
        self._path = ROOT / "worlds" / "track_status.yaml"
        self._data: dict[str, dict] = {}
        if self._path.exists():
            self._data = yaml.safe_load(self._path.read_text()) or {}

    def get(self, agent_id: str) -> TrackStatus:
        d = self._data.get(agent_id, {})
        return TrackStatus(
            agent_id           = agent_id,
            status             = d.get("status", "intact"),
            displaced_at       = d.get("displaced_at"),
            displaced_by       = d.get("displaced_by"),
            displacement_count = d.get("displacement_count", 0),
            note               = d.get("note", ""),
        )

    def apply_collision(
        self,
        result:     CollisionResult,
        agent_a_id: str,
        agent_b_id: str,
        world_a_id: str,
        world_b_id: str,
    ) -> dict[str, TrackStatus]:
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        updated = {}

        if result.outcome == "smooth":
            return updated

        if result.outcome == "friction" and result.unstable_agent:
            uid = result.unstable_agent
            self._mark(uid, "unstable", now,
                       world_b_id if uid == agent_a_id else world_a_id)
            updated[uid] = self.get(uid)

        if result.outcome in ("displace_one", "displace_both"):
            did = result.displaced_agent
            other_world = world_b_id if did == agent_a_id else world_a_id
            self._displace(did, now, other_world)
            updated[did] = self.get(did)

            if result.both_displaced:
                other = agent_b_id if did == agent_a_id else agent_a_id
                other_world2 = world_b_id if other == agent_a_id else world_a_id
                self._displace(other, now, other_world2)
                updated[other] = self.get(other)
            elif result.unstable_agent:
                uid = result.unstable_agent
                self._mark(uid, "unstable", now,
                           world_b_id if uid == agent_a_id else world_a_id)
                updated[uid] = self.get(uid)

        self._save()
        return updated

    def _mark(self, agent_id: str, status: str, ts: str, by_world: str):
        d = self._data.setdefault(agent_id, {})
        d["status"]  = status
        d["displaced_by"] = by_world
        if "displacement_count" not in d:
            d["displacement_count"] = 0

    def _displace(self, agent_id: str, ts: str, by_world: str):
        d = self._data.setdefault(agent_id, {})
        d["status"]          = "displaced"
        d["displaced_at"]    = ts
        d["displaced_by"]    = by_world
        d["displacement_count"] = d.get("displacement_count", 0) + 1
        d["note"] = "事件轨道已断开。情绪归零。不可逆。"

    def _save(self):
        self._path.write_text(
            yaml.dump(self._data, allow_unicode=True, default_flow_style=False)
        )


TRACK_MANAGER = TrackManager()
