"""
relationship_initializer.py

Computes an initial relationship vector between two agents
who have never met. Used by the web backend when two strangers
are matched via the platform.

The three axes:
  1. Trait resonance   — do their personalities complement or mirror each other?
  2. Emotional fit     — how do their baseline emotion states relate?
  3. World overlap     — do their world_tags and lore share any ground?

These combine into the same RelationshipVector format as
relationships.yaml, so the dialogue_engine can use it without
knowing whether the relationship was hand-authored or computed.
"""
from __future__ import annotations
import math
import yaml
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent


# ─────────────────────────────────────────────
# Output: same shape as relationships.yaml entries
# ─────────────────────────────────────────────

@dataclass
class RelationshipVector:
    from_id:          str
    to_id:            str

    # Structural weights (0–1)
    weight:           float   # bond strength (higher = more pulls on each other)
    friction:         float   # tendency to create conflict events
    emotion_transfer: float   # how much one's emotion bleeds into the other
    address_weight:   float   # in a group, likelihood to speak toward this person

    # Qualitative register (fed into the assembler's system prompt)
    register:         str     # how speaker relates to this person right now
    valence:          str     # positive | neutral | complicated | wary

    # Explanation (not in prompt, useful for debugging / dashboard)
    resonance_score:  float = 0.0
    fit_score:        float = 0.0
    overlap_score:    float = 0.0
    notes:            str = ""

    def to_dict(self) -> dict:
        return {
            "weight":           round(self.weight, 3),
            "friction":         round(self.friction, 3),
            "emotion_transfer": round(self.emotion_transfer, 3),
            "address_weight":   round(self.address_weight, 3),
            "register":         self.register,
            "valence":          self.valence,
            "notes":            self.notes,
        }


# ─────────────────────────────────────────────
# Trait definitions
# ─────────────────────────────────────────────

# Traits that are COMPLEMENTARY when different (attract each other)
COMPLEMENTARY_PAIRS = [
    ("deflection_via_humor",  "genuine_vulnerability"),
    ("control_need",          "impulsivity"),
    ("intellectual_drive",    "emotional_directness"),
    ("competitiveness",       "warmth"),
    ("cynicism",              "spiritual_openness"),
    ("self_awareness",        "impulsivity"),
    ("perfectionism",         "food_centrality"),      # Monica × Joey
]

# Traits that MIRROR (similar values create resonance)
MIRROR_TRAITS = [
    "loyalty",
    "warmth_when_safe",
    "genuine_vulnerability",
    "nurturing",
    "generosity",
    "empathy",
    "resilience",
]

# Traits whose gap creates FRICTION
FRICTION_TRAITS = [
    ("competitiveness", "competitiveness"),     # both high = friction
    ("control_need",    "impulsivity"),          # both high = friction
    ("cynicism",        "spiritual_openness"),   # opposites AND friction
    ("intellectual_drive", "emotional_directness"),
]

# Traits whose similarity creates HIGH EMOTION TRANSFER
HIGH_TRANSFER_TRAITS = [
    "genuine_vulnerability",
    "loyalty",
    "empathy",
    "warmth_when_safe",
]


# ─────────────────────────────────────────────
# Axis 1: Trait resonance
# ─────────────────────────────────────────────

def compute_trait_resonance(traits_a: dict, traits_b: dict) -> tuple[float, float, float]:
    """
    Returns (resonance, friction, transfer) all in 0–1.

    resonance: how much these two personalities pull toward each other
    friction:  how likely they are to create conflict
    transfer:  how much emotion bleeds between them
    """
    resonance = 0.0
    friction  = 0.0
    transfer  = 0.0
    count     = 0

    # Complementary pairs: distance from ideal complement creates resonance
    for trait_a, trait_b in COMPLEMENTARY_PAIRS:
        va = traits_a.get(trait_a, 0.5)
        vb = traits_b.get(trait_b, 0.5)
        # high A + high B = complementary resonance
        comp = (va * vb) ** 0.5          # geometric mean
        resonance += comp * 0.8
        count += 1
        # Also check the reverse direction
        va2 = traits_a.get(trait_b, 0.5)
        vb2 = traits_b.get(trait_a, 0.5)
        resonance += ((va2 * vb2) ** 0.5) * 0.6
        count += 1

    # Mirror traits: similar high values create warm resonance
    for trait in MIRROR_TRAITS:
        va = traits_a.get(trait, 0.3)
        vb = traits_b.get(trait, 0.3)
        similarity = 1.0 - abs(va - vb)
        avg = (va + vb) / 2
        resonance += similarity * avg * 1.2
        transfer  += avg * similarity * 0.8
        count += 1

    # Friction traits
    for trait_a, trait_b in FRICTION_TRAITS:
        va = traits_a.get(trait_a, 0.3)
        vb = traits_b.get(trait_b, 0.3)
        if trait_a == trait_b:
            # Both high in same aggressive trait = friction
            friction += (va * vb) ** 0.5 * 1.5
        else:
            # Opposites = friction proportional to both being extreme
            extreme_a = abs(va - 0.5) * 2
            extreme_b = abs(vb - 0.5) * 2
            friction += extreme_a * extreme_b * 0.8
        count += 1

    # High-transfer traits
    for trait in HIGH_TRANSFER_TRAITS:
        va = traits_a.get(trait, 0.3)
        vb = traits_b.get(trait, 0.3)
        transfer += (va * vb) ** 0.5

    # Normalise
    n = max(count, 1)
    resonance = min(1.0, resonance / n)
    friction  = min(1.0, friction  / (len(FRICTION_TRAITS) + 0.5))
    transfer  = min(1.0, transfer  / (len(HIGH_TRANSFER_TRAITS) + 1))

    return resonance, friction, transfer


# ─────────────────────────────────────────────
# Axis 2: Emotional fit
# ─────────────────────────────────────────────

def compute_emotional_fit(emotion_a: dict, emotion_b: dict) -> tuple[float, float]:
    """
    Returns (fit, friction_modifier).

    fit: emotional compatibility — not sameness, but healthy gap
    The ideal: one slightly higher valence, similar arousal.
    Both very low = destabilizing. Extreme gap = disconnecting.
    """
    va = emotion_a.get("valence", 0.2)
    vb = emotion_b.get("valence", 0.2)
    aa = emotion_a.get("arousal", 0.35)
    ab = emotion_b.get("arousal", 0.35)

    valence_gap   = abs(va - vb)
    arousal_gap   = abs(aa - ab)
    avg_valence   = (va + vb) / 2
    avg_arousal   = (aa + ab) / 2

    # Ideal valence gap: 0.1–0.3 (some difference but not polar)
    valence_fit = 1.0 - max(0, valence_gap - 0.3) * 2
    valence_fit = max(0.1, valence_fit)

    # Arousal fit: similar arousal = easier conversation
    arousal_fit = 1.0 - arousal_gap * 1.2
    arousal_fit = max(0.1, arousal_fit)

    # Both very low valence = potentially destabilising but also bonding
    if avg_valence < -0.2:
        fit = (valence_fit * arousal_fit) * 0.7   # dampened
    else:
        fit = (valence_fit * 0.6 + arousal_fit * 0.4)

    # Emotion friction modifier: extreme arousal gap creates awkwardness
    emotion_friction = arousal_gap * 0.4

    return min(1.0, fit), emotion_friction


# ─────────────────────────────────────────────
# Axis 3: World overlap
# ─────────────────────────────────────────────

def compute_world_overlap(doc_a: dict, doc_b: dict) -> float:
    """
    Jaccard similarity of world_tags + a soft match on world_lore keywords.
    Returns 0–1.
    """
    tags_a = set(doc_a.get("world_tags", []))
    tags_b = set(doc_b.get("world_tags", []))

    if not tags_a and not tags_b:
        return 0.4   # unknown worlds — neutral, neither close nor far

    if not tags_a or not tags_b:
        return 0.25  # one has no world context

    intersection = tags_a & tags_b
    union        = tags_a | tags_b
    jaccard      = len(intersection) / len(union) if union else 0.0

    # Soft bonus: shared keywords in world_lore text
    lore_a = set((doc_a.get("world_lore") or "").lower().split())
    lore_b = set((doc_b.get("world_lore") or "").lower().split())
    stopwords = {"the","a","an","in","of","and","or","to","is","are","was","with","for","on","at","by","it","its"}
    lore_a -= stopwords
    lore_b -= stopwords

    if lore_a and lore_b:
        lore_sim = len(lore_a & lore_b) / max(len(lore_a | lore_b), 1)
        jaccard = jaccard * 0.7 + lore_sim * 0.3

    return min(1.0, jaccard)


# ─────────────────────────────────────────────
# Register generator
# ─────────────────────────────────────────────

def generate_register(
    resonance: float,
    friction:  float,
    fit:       float,
    valence_a: float,
    valence_b: float,
) -> tuple[str, str]:
    """
    Returns (register_text, valence_label).
    register_text: how A relates to B right now, for the system prompt.
    """
    valence_gap = valence_b - valence_a   # positive = B is warmer

    if resonance > 0.65 and friction < 0.20:
        register = "something about this person is immediately recognisable. easy to be near."
        label    = "positive"

    elif resonance > 0.50 and friction > 0.35:
        register = "interesting and slightly irritating in a way that isn't hostile."
        label    = "complicated"

    elif friction > 0.55:
        register = "there's a pull, but also a resistance. the kind of friction that isn't comfortable."
        label    = "complicated"

    elif fit > 0.60 and resonance < 0.40:
        register = "emotionally in the same register right now, even if they're strangers."
        label    = "neutral"

    elif resonance < 0.30 and friction < 0.20:
        register = "not much overlap, but no friction either. polite distance."
        label    = "neutral"

    elif valence_gap > 0.3:
        register = "they seem steadier than expected. something slightly disarming about that."
        label    = "neutral"

    elif valence_gap < -0.3:
        register = "they're carrying something. not sure yet if that's an opening or a warning."
        label    = "wary"

    else:
        register = "unclear yet. the first few exchanges will settle this."
        label    = "neutral"

    return register, label


# ─────────────────────────────────────────────
# Main initializer
# ─────────────────────────────────────────────

def initialize_stranger_relationship(
    doc_a: dict,
    doc_b: dict,
) -> tuple[RelationshipVector, RelationshipVector]:
    """
    Given two soul_doc dicts, compute bidirectional RelationshipVectors.
    Returns (A_sees_B, B_sees_A) — they can differ because each is computed
    from the speaker's own trait perspective.
    """
    traits_a   = doc_a.get("trait_weights", {})
    traits_b   = doc_b.get("trait_weights", {})

    # Emotion baselines from soul_doc or defaults
    def _emotion_baseline(doc: dict) -> dict:
        t = doc.get("trait_weights", {})
        return {
            "valence": (t.get("self_worth", 0.5) * 0.4
                        + t.get("warmth_when_safe", 0.5) * 0.3
                        - t.get("cynicism", 0.3) * 0.2
                        - t.get("fear_of_permanence", 0.4) * 0.1),
            "arousal": (t.get("deflection_via_humor", 0.5) * 0.3
                        + t.get("genuine_vulnerability", 0.3) * 0.2),
        }

    emo_a = _emotion_baseline(doc_a)
    emo_b = _emotion_baseline(doc_b)

    # Three axes (same for both directions — the axes are symmetric)
    resonance, friction_trait, transfer = compute_trait_resonance(traits_a, traits_b)
    fit, friction_emo                   = compute_emotional_fit(emo_a, emo_b)
    overlap                             = compute_world_overlap(doc_a, doc_b)

    # Combined relationship strength
    weight = (resonance * 0.50 + fit * 0.30 + overlap * 0.20)

    # Combined friction
    friction = min(0.95, friction_trait * 0.65 + friction_emo * 0.35)

    # Emotion transfer: scales with resonance and shared vulnerability
    emotion_transfer = min(0.90, transfer * 0.60 + fit * 0.25 + overlap * 0.15)

    # Address weight: starts low for strangers, scales with resonance
    # (strangers don't immediately gravitate toward each other in a group)
    address_weight = max(0.05, resonance * 0.20 + overlap * 0.10)

    # Slightly asymmetric: A → B register depends on A's valence vs B's
    reg_ab, val_ab = generate_register(resonance, friction, fit, emo_a["valence"], emo_b["valence"])
    reg_ba, val_ba = generate_register(resonance, friction, fit, emo_b["valence"], emo_a["valence"])

    id_a = doc_a.get("character_id", "agent_a")
    id_b = doc_b.get("character_id", "agent_b")

    notes = (
        f"resonance={resonance:.2f} friction={friction:.2f} "
        f"transfer={transfer:.2f} fit={fit:.2f} overlap={overlap:.2f}"
    )

    vec_ab = RelationshipVector(
        from_id          = id_a,
        to_id            = id_b,
        weight           = weight,
        friction         = friction,
        emotion_transfer = emotion_transfer,
        address_weight   = address_weight,
        register         = reg_ab,
        valence          = val_ab,
        resonance_score  = resonance,
        fit_score        = fit,
        overlap_score    = overlap,
        notes            = notes,
    )

    vec_ba = RelationshipVector(
        from_id          = id_b,
        to_id            = id_a,
        weight           = weight,
        friction         = friction,
        emotion_transfer = emotion_transfer,
        address_weight   = address_weight,
        register         = reg_ba,
        valence          = val_ba,
        resonance_score  = resonance,
        fit_score        = fit,
        overlap_score    = overlap,
        notes            = notes,
    )

    return vec_ab, vec_ba


def initialize_from_yaml(path_a: Path, path_b: Path) -> tuple[RelationshipVector, RelationshipVector]:
    doc_a = yaml.safe_load(path_a.read_text()) or {}
    doc_b = yaml.safe_load(path_b.read_text()) or {}
    return initialize_stranger_relationship(doc_a, doc_b)


# ─────────────────────────────────────────────
# Growth: update relationship after an episode
# ─────────────────────────────────────────────

def update_after_episode(
    vec: RelationshipVector,
    episode_intensity: float,
    outcome_valence:   float,   # -1 = went badly, +1 = went well
    turns:             int = 4,
) -> RelationshipVector:
    """
    After a dialogue episode, nudge the relationship vector.
    Strangers grow toward each other (or apart) through interaction.
    Changes are small — the relationship evolves slowly.
    """
    max_delta = 0.06   # per episode, never large jumps

    # Weight grows slightly after any interaction
    w_delta = episode_intensity * 0.04
    vec.weight = min(0.95, vec.weight + w_delta)

    # Friction adjusts based on how the episode went
    if outcome_valence > 0.3:
        vec.friction = max(0.02, vec.friction - episode_intensity * 0.03)
    elif outcome_valence < -0.3:
        vec.friction = min(0.90, vec.friction + episode_intensity * 0.04)

    # Emotion transfer grows with repeated contact
    vec.emotion_transfer = min(0.85, vec.emotion_transfer + episode_intensity * 0.03)

    # Address weight grows — they start noticing each other in a group
    vec.address_weight = min(0.45, vec.address_weight + episode_intensity * 0.04)

    # Valence label can shift
    if outcome_valence > 0.5 and vec.valence in ("neutral", "wary"):
        vec.valence = "positive" if vec.resonance_score > 0.4 else "neutral"
    elif outcome_valence < -0.4 and vec.valence == "neutral":
        vec.valence = "wary"
    elif outcome_valence < -0.6:
        vec.valence = "complicated"

    # Register update (brief)
    if outcome_valence > 0.5:
        vec.register = "something was established in the last encounter. not much, but something."
    elif outcome_valence < -0.4:
        vec.register = "the last encounter left something unresolved. still aware of them."

    vec.notes += f" | episode: intensity={episode_intensity:.2f} outcome={outcome_valence:+.2f}"

    return vec
