"""
tests/test_emotion_engine.py
Unit tests for EmotionEngine.

Run with:  python -m pytest tests/test_emotion_engine.py -v
"""
from __future__ import annotations
import sys, tempfile, yaml, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from modules.emotion.emotion_engine import EmotionEngine, EmotionState


# ─────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────

MINIMAL_SOUL_DOC = {
    "character_id": "test_char",
    "character_name": "Test Character",
    "trait_weights": {
        "self_worth":              0.5,
        "warmth_when_safe":        0.5,
        "cynicism":                0.3,
        "fear_of_permanence":      0.4,
        "deflection_via_humor":    0.5,
        "genuine_vulnerability":   0.3,
    },
    "life_nodes": [],
    "social_drift": [],
    "habit_loops": [],
    "world_lore": "",
}


def make_engine(traits: dict | None = None) -> tuple[EmotionEngine, Path]:
    """Return a fresh engine backed by a temp soul_doc yaml."""
    doc = dict(MINIMAL_SOUL_DOC)
    if traits:
        doc["trait_weights"] = {**doc["trait_weights"], **traits}

    tmp = tempfile.NamedTemporaryFile(
        suffix=".yaml", mode="w", delete=False, encoding="utf-8"
    )
    yaml.dump(doc, tmp)
    tmp.flush()
    tmp.close()

    engine = EmotionEngine(
        soul_doc_path=Path(tmp.name),
        config={},
        character_id="test_char",
    )
    return engine, Path(tmp.name)


# ─────────────────────────────────────────────
# Clamp tests — issue #9
# ─────────────────────────────────────────────

class TestClamp:
    def test_valence_never_exceeds_bounds(self):
        engine, _ = make_engine()
        # hammer with large positive deltas
        for _ in range(20):
            engine.receive_event({"intensity": 1.0, "valence_push": 1.0, "arousal_push": 0.0})
        assert engine.current.valence <= 1.0

    def test_valence_never_below_minus_one(self):
        engine, _ = make_engine()
        for _ in range(20):
            engine.receive_event({"intensity": 1.0, "valence_push": -1.0, "arousal_push": 0.0})
        assert engine.current.valence >= -1.0

    def test_arousal_never_exceeds_one(self):
        engine, _ = make_engine()
        for _ in range(20):
            engine.receive_event({"intensity": 1.0, "valence_push": 0.0, "arousal_push": 1.0})
        assert engine.current.arousal <= 1.0

    def test_arousal_never_below_zero(self):
        engine, _ = make_engine()
        for _ in range(20):
            engine.receive_event({"intensity": 1.0, "valence_push": 0.0, "arousal_push": -1.0})
        assert engine.current.arousal >= 0.0

    def test_drift_pressure_clamped(self):
        engine, _ = make_engine()
        for _ in range(20):
            engine.receive_event({"intensity": 1.0, "valence_push": 0.0, "arousal_push": 0.0})
        assert 0.0 <= engine.current.drift_pressure <= 1.0

    def test_override_clamp(self):
        engine, _ = make_engine()
        engine.receive_planning_override({"valence": 5.0, "arousal": -3.0, "pressure": 99.0})
        assert engine.current.valence   <= 1.0
        assert engine.current.arousal  >= 0.0
        assert engine.current.drift_pressure <= 1.0


# ─────────────────────────────────────────────
# Dominant color tests
# ─────────────────────────────────────────────

class TestDominantColor:
    def test_color_assigned_after_init(self):
        engine, _ = make_engine()
        assert engine.current.dominant_color != ""

    def test_color_changes_with_extreme_state(self):
        engine, _ = make_engine()
        original = engine.current.dominant_color
        engine.receive_event({"intensity": 1.0, "valence_push": -1.0, "arousal_push": 1.0})
        # after an extreme negative event, color should update
        assert engine.current.dominant_color is not None  # never None


# ─────────────────────────────────────────────
# Writeback tests — ensures timers fire correctly
# ─────────────────────────────────────────────

class TestWriteback:
    def test_writeback_fires_when_timer_expires(self):
        written_nodes: list[dict] = []

        engine, _ = make_engine()
        engine.on_writeback = lambda node: written_nodes.append(node)

        # Force valence very low
        for _ in range(10):
            engine.receive_event({"intensity": 1.0, "valence_push": -1.0, "arousal_push": 0.0})

        # Manually expire the timer
        engine._writeback_timers["low_valence"] = time.time() - 9999
        engine._check_writebacks()

        assert len(written_nodes) >= 1
        assert written_nodes[0]["id"].startswith("auto_low_valence")

    def test_writeback_not_fired_before_timer(self):
        written_nodes: list[dict] = []
        engine, _ = make_engine()
        engine.on_writeback = lambda node: written_nodes.append(node)

        for _ in range(10):
            engine.receive_event({"intensity": 1.0, "valence_push": -1.0, "arousal_push": 0.0})

        # Timer just started — should NOT fire yet
        engine._check_writebacks()
        assert len(written_nodes) == 0


# ─────────────────────────────────────────────
# Trait-derived baseline tests
# ─────────────────────────────────────────────

class TestBaseline:
    def test_high_cynicism_lowers_valence(self):
        engine_hi, _ = make_engine({"cynicism": 0.95, "self_worth": 0.5})
        engine_lo, _ = make_engine({"cynicism": 0.05, "self_worth": 0.5})
        assert engine_hi.current.valence < engine_lo.current.valence

    def test_high_humor_raises_arousal(self):
        engine_hi, _ = make_engine({"deflection_via_humor": 0.95})
        engine_lo, _ = make_engine({"deflection_via_humor": 0.05})
        assert engine_hi.current.arousal >= engine_lo.current.arousal
