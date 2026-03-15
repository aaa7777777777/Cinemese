"""
world_matchmaker.py

Web-side random collision algorithm.
Extends the base matchmaker with worldview gating and displacement logic.

Pipeline:
1. Pull candidate pool from available agents
2. Compute worldview_gap for each pair
3. Apply gap-specific rules:
   - smooth/friction → allow, with emotion modifiers
   - displace_one    → allow, flag the weaker agent for track reset
   - displace_both   → allow if both consent (or in "wild" mode)
4. Execute collision via dialogue_engine
5. Apply track status changes after session
6. Reset displaced agents' emotion and event engines to baseline zero
"""
from __future__ import annotations
import random
import yaml
import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

ROOT = Path(__file__).parent.parent

from worlds.world_engine import (
    WorldDef, TrackStatus, CollisionResult,
    load_world, worldview_gap, compute_collision,
    TRACK_MANAGER, SMOOTH_MAX, FRICTION_MAX, DISPLACE_ONE_MAX,
)
from network.relationship_graph import CACHE as REL_CACHE


# ─────────────────────────────────────────────
# Agent world registry
# ─────────────────────────────────────────────

def get_agent_world(agent_id: str) -> Optional[WorldDef]:
    """
    Load the world assigned to an agent.
    World id stored in soul_doc.world_id, or inferred from world_tags.
    """
    soul_path = ROOT / "core" / "soul_doc" / f"{agent_id}.yaml"
    if not soul_path.exists():
        return None
    doc = yaml.safe_load(soul_path.read_text()) or {}

    # Explicit world_id takes priority
    if "world_id" in doc:
        return load_world(doc["world_id"])

    # Infer from world_tags
    tags = set(doc.get("world_tags", []))
    best, best_score = None, -1
    for wpath in (ROOT / "worlds" / "definitions").glob("*.yaml"):
        wdata = yaml.safe_load(wpath.read_text())
        wtags = {wdata.get("nation",""), wdata.get("era",""), wdata.get("env","")}
        score = len(tags & wtags)
        if score > best_score:
            best_score, best = score, load_world(wdata["id"])
    return best


# ─────────────────────────────────────────────
# Candidate pool
# ─────────────────────────────────────────────

@dataclass
class WorldCandidate:
    agent_id:       str
    world:          WorldDef
    track:          TrackStatus
    tension_score:  float
    last_event_type: str


def build_candidate_pool(
    exclude_ids: list[str] = [],
    only_intact: bool = False,
) -> list[WorldCandidate]:
    """
    Collect all available agents with their world and track status.
    In production this reads from the agent registry / dashboard runtime.
    Here we scan soul_docs and load corresponding data.
    """
    soul_dir = ROOT / "core" / "soul_doc"
    candidates = []

    for soul_path in soul_dir.glob("*.yaml"):
        agent_id = soul_path.stem
        if agent_id in exclude_ids:
            continue

        world = get_agent_world(agent_id)
        if not world:
            continue

        track = TRACK_MANAGER.get(agent_id)
        if only_intact and track.status == "displaced":
            continue

        # Default tension score — in production this comes from AgentRuntime
        candidates.append(WorldCandidate(
            agent_id        = agent_id,
            world           = world,
            track           = track,
            tension_score   = 30.0 + random.uniform(-10, 20),
            last_event_type = "quiet_moment",
        ))

    return candidates


# ─────────────────────────────────────────────
# Core matching algorithm
# ─────────────────────────────────────────────

@dataclass
class WorldMatchResult:
    agent_a_id:      str
    agent_b_id:      str
    world_a_id:      str
    world_b_id:      str
    gap:             float
    outcome:         str
    collision:       CollisionResult
    session_config:  dict    # ready to pass to /dialogue/start


def find_world_match(
    agent_id:        str,
    mode:            str = "normal",  # normal | wild
    max_gap:         float = 0.90,
    prefer_gap_range: tuple = (0.10, 0.60),
) -> Optional[WorldMatchResult]:
    """
    Find the best match for agent_id from the candidate pool.

    mode="normal": displace_both only if both have been displaced before
    mode="wild":   displace_both always allowed — the encounter is fated

    prefer_gap_range: target gap window for interesting collisions
    The ideal match has enough gap to matter, not so much it's just destruction.
    """
    soul_path = ROOT / "core" / "soul_doc" / f"{agent_id}.yaml"
    if not soul_path.exists():
        return None

    doc_a    = yaml.safe_load(soul_path.read_text()) or {}
    world_a  = get_agent_world(agent_id)
    track_a  = TRACK_MANAGER.get(agent_id)
    if not world_a:
        return None

    pool = build_candidate_pool(exclude_ids=[agent_id])
    if not pool:
        return None

    # Score each candidate
    scored: list[tuple[float, WorldCandidate]] = []
    for cand in pool:
        gap = worldview_gap(world_a, cand.world)
        if gap > max_gap:
            continue

        # Penalise both-displace in normal mode unless pre-conditions met
        col = compute_collision(
            agent_id, world_a, doc_a, track_a,
            cand.agent_id, cand.world,
            yaml.safe_load((ROOT/"core"/"soul_doc"/f"{cand.agent_id}.yaml").read_text()) or {},
            cand.track,
        )
        if col.outcome == "displace_both" and mode != "wild":
            # Only allow if both already have displacement history
            if track_a.displacement_count == 0 and cand.track.displacement_count == 0:
                continue

        # Quality score: prefer gaps in the interesting range
        lo, hi = prefer_gap_range
        if lo <= gap <= hi:
            quality = 1.0 - abs(gap - (lo + hi) / 2) / ((hi - lo) / 2)
        else:
            quality = max(0.0, 1.0 - abs(gap - (lo + hi) / 2))

        # Displaced agents are interesting matches (world already shifted)
        if cand.track.status == "displaced":
            quality += 0.15

        scored.append((quality, cand))

    if not scored:
        return None

    scored.sort(key=lambda x: -x[0])

    # Pick from top 3 with some randomness
    top = scored[:min(3, len(scored))]
    quality, winner = random.choices(top, weights=[s[0]+0.1 for s,_ in top], k=1)[0]

    doc_b = yaml.safe_load((ROOT/"core"/"soul_doc"/f"{winner.agent_id}.yaml").read_text()) or {}

    collision = compute_collision(
        agent_id, world_a, doc_a, track_a,
        winner.agent_id, winner.world, doc_b, winner.track,
    )

    # Pick a scene appropriate to the gap
    scene_id = _pick_scene_for_gap(collision.gap, world_a, winner.world)

    return WorldMatchResult(
        agent_a_id   = agent_id,
        agent_b_id   = winner.agent_id,
        world_a_id   = world_a.id,
        world_b_id   = winner.world.id,
        gap          = collision.gap,
        outcome      = collision.outcome,
        collision    = collision,
        session_config = {
            "participants": [agent_id, winner.agent_id],
            "scene_id":     scene_id,
        },
    )


def _pick_scene_for_gap(gap: float, wa: WorldDef, wb: WorldDef) -> str:
    """Scene selection based on worldview gap."""
    if gap < 0.30:
        return "central_perk"         # comfortable common ground
    elif gap < 0.55:
        return "hallway"              # transitional, ambiguous
    elif gap < 0.75:
        return "street"               # public, exposed, no shared frame
    else:
        return "street"               # the most neutral possible ground


# ─────────────────────────────────────────────
# Displacement executor
# ─────────────────────────────────────────────

def execute_displacement(
    agent_id:    str,
    world_id:    str,
    engines:     dict,   # AgentRuntime engines dict from dashboard
):
    """
    Apply displacement to an agent:
    1. Reset emotion engine to baseline zero
    2. Clear event engine current event + timer
    3. Write a permanent displacement node to soul_doc
    """
    import os

    # 1. Reset emotion
    if agent_id in engines:
        e = engines[agent_id].emotion_engine
        e.state.valence        = 0.0
        e.state.arousal        = 0.0
        e.state.drift_pressure = 0.0
        e.state.dominant_color = "归零。原来的世界已经不在了。"
        e.state.rhythm_phase   = "trough"
        e.state.micro_score    = 0.0
        e._rhythm_timer        = time.time()
        e._rhythm_idx          = 0
        e._writeback_timers    = {}

        # 2. Reset event engine
        ev = engines[agent_id].event_engine
        ev._current_event      = None
        ev._last_event_time    = time.time()

    # 3. Write displacement node to soul_doc
    soul_path = ROOT / "core" / "soul_doc" / f"{agent_id}.yaml"
    if soul_path.exists():
        doc = yaml.safe_load(soul_path.read_text()) or {}
        nodes = doc.setdefault("life_nodes", [])
        nodes.append({
            "id":     f"displacement_{int(time.time())}",
            "ts":     time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event":  f"遇到了来自 {world_id} 的人。原有的事件轨道断开。归零。",
            "delta":  {
                "self_worth":         -0.05,
                "adaptability":       +0.08,
                "identity_stability": -0.10,
            },
            "locked": False,
            "note":   "displacement node — written by world_engine. 不可逆。",
        })
        soul_path.write_text(
            yaml.dump(doc, allow_unicode=True, default_flow_style=False)
        )

    print(f"[displacement] {agent_id} — track reset. 原轨道已断开。")


# ─────────────────────────────────────────────
# System prompt injection
# ─────────────────────────────────────────────

def world_prompt_fragment(world: WorldDef, track: TrackStatus) -> str:
    """
    The world context injected into every LLM call.
    Two versions: intact track vs displaced track.
    """
    if track.status == "displaced":
        return (
            f"你来自：{world.label}。\n\n"
            f"{world.economic_register}\n\n"
            f"{world.social_register}\n\n"
            f"{world.background_noise}\n\n"
            "───\n"
            f"你的原有事件轨道在 {track.displaced_at[:10] if track.displaced_at else '某个时刻'} 断开了。\n"
            "你不再是原来的位置。那个位置不存在了。\n"
            "你现在从零开始积累新的事件，但你记得以前。\n"
            "记得和在那里是不同的事。"
        )
    elif track.status == "unstable":
        return (
            f"你来自：{world.label}。\n\n"
            f"{world.economic_register}\n\n"
            f"{world.social_register}\n\n"
            f"{world.background_noise}\n\n"
            "───\n"
            "你的轨道是稳定的，但上次的相遇在某处留下了什么。\n"
            "你还在原来的位置，但那个位置的地基动了一点点。"
        )
    else:
        return (
            f"你来自：{world.label}。\n\n"
            f"这是你呼吸的空气，不是你遵守的规则：\n\n"
            f"{world.economic_register}\n\n"
            f"{world.social_register}\n\n"
            f"{world.background_noise}"
        )
