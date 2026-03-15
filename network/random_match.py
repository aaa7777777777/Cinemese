"""
network/random_match.py

The core matching algorithm:
  1. Score each agent (tension_score = micro_score + event_score)
  2. Gate by threshold + event compatibility
  3. Pick best match (closest tension)
  4. Clamp post-collision delta to budget

This file is the canonical reference — matchmaker.py uses these same rules.
"""

from __future__ import annotations
import random
import math
from dataclasses import dataclass


# ── Score computation ─────────────────────────────────────────────────────────

def micro_score(valence: float, arousal: float, pressure: float) -> float:
    """
    Emotion intensity → 0–100 score.
    All three axes contribute independently.

    |valence|: how far from neutral (both extremes score high)
    arousal:   how activated the character is
    pressure:  how much the current window is pulling on them
    """
    return abs(valence) * 40 + arousal * 35 + pressure * 25


def event_score(intensity: float, valence_push: float, arousal_push: float) -> float:
    """
    How charged is the most recent event → 0–100.
    """
    return intensity * 50 + abs(valence_push) * 30 + abs(arousal_push) * 20


def tension_score(ms: float, es: float) -> float:
    return ms + es


# ── Compatibility gate ────────────────────────────────────────────────────────

COMPATIBLE_EVENT_PAIRS: list[frozenset] = [
    frozenset({"quiet_moment"}),
    frozenset({"quiet_moment", "internal_shift"}),
    frozenset({"interaction"}),
    frozenset({"interaction", "discovery"}),
    frozenset({"discovery", "internal_shift"}),
    # conflict ↔ conflict only if allow_high_intensity=True
]

def events_compatible(type_a: str, type_b: str, allow_high: bool = False) -> bool:
    if "conflict" in {type_a, type_b}:
        return allow_high and type_a == type_b == "conflict"
    pair = frozenset({type_a, type_b})
    return any(pair <= p or pair == p for p in COMPATIBLE_EVENT_PAIRS)


# ── Main matching function ────────────────────────────────────────────────────

@dataclass
class Agent:
    id:          str
    tension:     float
    event_type:  str
    available:   bool = True
    last_interactions: dict = None   # {other_id: unix_timestamp}

    def __post_init__(self):
        if self.last_interactions is None:
            self.last_interactions = {}


def find_best_match(
    agent: Agent,
    pool: list[Agent],
    threshold: int = 80,
    min_reinteract_hours: float = 6.0,
    allow_high_intensity: bool = False,
) -> Agent | None:
    """
    Find the best agent to pair with `agent` from `pool`.

    Rules:
    1. Must be available
    2. |tension_A - tension_B| <= threshold
    3. tension_A + tension_B <= threshold * 2
    4. Event types compatible
    5. Cooldown: last interaction > min_reinteract_hours ago

    Selection: closest tension score (smoothest transition).
    If tie: random among tied candidates.
    """
    import time

    candidates: list[tuple[float, Agent]] = []

    for other in pool:
        if other.id == agent.id:              continue
        if not other.available:               continue

        delta    = abs(agent.tension - other.tension)
        combined = agent.tension + other.tension

        if delta > threshold:                 continue
        if combined > threshold * 2:          continue

        if not events_compatible(agent.event_type, other.event_type, allow_high_intensity):
            continue

        last_ts = agent.last_interactions.get(other.id, 0)
        hours_elapsed = (time.time() - last_ts) / 3600
        if hours_elapsed < min_reinteract_hours:
            continue

        candidates.append((delta, other))

    if not candidates:
        return None

    # Sort by delta ascending — closest tension wins
    candidates.sort(key=lambda x: x[0])

    # If multiple agents within 5 points of the best, pick randomly among them
    # This avoids the same pair always matching
    best_delta = candidates[0][0]
    near_best  = [a for d, a in candidates if d <= best_delta + 5]

    return random.choice(near_best)


# ── Post-collision budget constraint ─────────────────────────────────────────

def clamp_collision_deltas(
    tension_a: float,
    tension_b: float,
    raw_delta_a: float,
    raw_delta_b: float,
    budget_factor: float = 1.20,
) -> tuple[float, float]:
    """
    After a collision, each agent's tension increases by their delta.
    Constraint: post_combined ≤ pre_combined * budget_factor.

    If violated, scale both deltas down proportionally.
    This ensures interactions never spike total system intensity by more than 20%.

    Returns (safe_delta_a, safe_delta_b).
    """
    pre     = tension_a + tension_b
    post    = (tension_a + raw_delta_a) + (tension_b + raw_delta_b)
    ceiling = pre * budget_factor

    if post <= ceiling:
        return raw_delta_a, raw_delta_b

    # How much overshoot?
    overshoot = post - ceiling
    total_delta = raw_delta_a + raw_delta_b

    if total_delta <= 0:
        return 0.0, 0.0

    # Scale both deltas down to exactly hit the ceiling
    scale = 1.0 - (overshoot / total_delta)
    scale = max(0.0, scale)

    return raw_delta_a * scale, raw_delta_b * scale


# ── Smoothness score ──────────────────────────────────────────────────────────

def smoothness_score(
    tension_a: float,
    tension_b: float,
    event_type_a: str,
    event_type_b: str,
) -> float:
    """
    0–1 score: how naturally this collision flows.
    Used to weight random selection when multiple candidates are similar.

    High score = similar tension + compatible events + not both high-arousal.
    """
    # Tension similarity (closer = smoother)
    delta_norm = abs(tension_a - tension_b) / 100.0
    tension_factor = 1.0 - delta_norm

    # Event harmony
    event_factor = 1.0 if events_compatible(event_type_a, event_type_b) else 0.0

    # Not both at max tension
    combined_norm = (tension_a + tension_b) / 200.0
    headroom_factor = 1.0 - max(0, combined_norm - 0.7)

    return tension_factor * 0.5 + event_factor * 0.3 + headroom_factor * 0.2


def weighted_random_match(
    agent: Agent,
    pool: list[Agent],
    threshold: int = 80,
    temperature: float = 0.3,
) -> Agent | None:
    """
    Alternative to find_best_match: probabilistic selection weighted by smoothness.
    temperature: 0 = always pick best, 1 = fully random among compatible.

    Use this for the network matchmaker to avoid deterministic pairing.
    """
    import time

    candidates: list[tuple[float, Agent]] = []

    for other in pool:
        if other.id == agent.id: continue
        if not other.available:  continue
        if abs(agent.tension - other.tension) > threshold: continue
        if agent.tension + other.tension > threshold * 2:  continue
        if not events_compatible(agent.event_type, other.event_type): continue
        last_ts = agent.last_interactions.get(other.id, 0)
        if (time.time() - last_ts) / 3600 < 6: continue

        score = smoothness_score(agent.tension, other.tension,
                                  agent.event_type, other.event_type)
        candidates.append((score, other))

    if not candidates:
        return None

    if temperature == 0:
        return max(candidates, key=lambda x: x[0])[1]

    # Softmax weighted selection
    scores = [s for s, _ in candidates]
    max_s  = max(scores)
    weights = [math.exp((s - max_s) / temperature) for s in scores]
    total   = sum(weights)
    probs   = [w / total for w in weights]

    r = random.random()
    cumulative = 0.0
    for prob, (_, agent_b) in zip(probs, candidates):
        cumulative += prob
        if r <= cumulative:
            return agent_b

    return candidates[-1][1]


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agents = [
        Agent("chandler", tension=42, event_type="quiet_moment"),
        Agent("joey",      tension=38, event_type="interaction"),
        Agent("monica",    tension=71, event_type="conflict"),
        Agent("sheldon",   tension=55, event_type="discovery"),
        Agent("penny",     tension=44, event_type="quiet_moment"),
    ]

    print("=== find_best_match ===")
    for ag in agents:
        pool   = [a for a in agents if a.id != ag.id]
        match  = find_best_match(ag, pool, threshold=80)
        smooth = smoothness_score(ag.tension, match.tension, ag.event_type, match.event_type) if match else 0
        print(f"  {ag.id:<10} t={ag.tension:<5} → {match.id if match else 'no match':<10} "
              f"Δ={abs(ag.tension - match.tension) if match else '-':<5} smooth={smooth:.2f}")

    print()
    print("=== budget clamp test ===")
    da, db = clamp_collision_deltas(42, 38, 20, 18, budget_factor=1.20)
    pre    = 42 + 38
    post   = (42 + da) + (38 + db)
    print(f"  pre={pre}  post={post:.1f}  ceiling={pre*1.2:.1f}  da={da:.1f}  db={db:.1f}")

    print()
    print("=== weighted_random_match ===")
    chandler = agents[0]
    pool     = agents[1:]
    for _ in range(5):
        m = weighted_random_match(chandler, pool, temperature=0.3)
        print(f"  → {m.id if m else 'none'}")
