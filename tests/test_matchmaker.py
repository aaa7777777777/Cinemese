"""
tests/test_matchmaker.py
Unit tests for matchmaker worldview_gap formula and world_resilience.

Run with:  python -m pytest tests/test_matchmaker.py -v
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from network.matchmaker import get_world_coords, world_prompt_fragment


# ─────────────────────────────────────────────
# world_prompt_fragment language test — issue #13
# ─────────────────────────────────────────────

class TestWorldPromptFragment:
    def test_output_is_english(self):
        """world_prompt_fragment must not contain Chinese characters."""
        wc = {
            "label":           "New York City",
            "era_label":       "1990s",
            "economic_trend":  "Post-Cold-War boom. Jobs feel permanent until they don't.",
            "cultural_trend":  "Gen X irony as default register.",
            "background_noise":"AIDS crisis receding from public conversation. Y2K approaching.",
        }
        fragment = world_prompt_fragment(wc)
        # No CJK unified ideograph range
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in fragment), (
            f"Fragment contains Chinese characters:\n{fragment}"
        )

    def test_output_contains_label(self):
        wc = {"label": "Tokyo", "era_label": "1980s"}
        fragment = world_prompt_fragment(wc)
        assert "Tokyo" in fragment

    def test_displaced_count_in_output(self):
        wc = {"label": "London", "era_label": "2010s"}
        fragment = world_prompt_fragment(wc, displaced_count=2)
        assert "2" in fragment
        assert "broken" in fragment.lower() or "track" in fragment.lower()

    def test_zero_displaced_no_displacement_text(self):
        wc = {"label": "Paris", "era_label": "1960s"}
        fragment = world_prompt_fragment(wc, displaced_count=0)
        assert "broken" not in fragment.lower()
        assert "displaced" not in fragment.lower()


# ─────────────────────────────────────────────
# world_resilience formula — issue #12
# ─────────────────────────────────────────────

def _compute_resilience(trait_weights: dict) -> float:
    """Mirror the formula in WORLDS.md."""
    return (
        trait_weights.get("quiet_resilience", 0.5)    * 0.35 +
        trait_weights.get("self_sufficiency", 0.5)    * 0.30 +
        trait_weights.get("adaptability",     0.4)    * 0.20 +
        trait_weights.get("identity_stability", 0.5)  * 0.15
    )


class TestWorldResilience:
    def test_formula_range(self):
        """Result should always be in [0, 1]."""
        for val in [0.0, 0.5, 1.0]:
            traits = {
                "quiet_resilience":   val,
                "self_sufficiency":   val,
                "adaptability":       val,
                "identity_stability": val,
            }
            r = _compute_resilience(traits)
            assert 0.0 <= r <= 1.0

    def test_all_max_gives_one(self):
        traits = {
            "quiet_resilience":   1.0,
            "self_sufficiency":   1.0,
            "adaptability":       1.0,
            "identity_stability": 1.0,
        }
        r = _compute_resilience(traits)
        assert abs(r - 1.0) < 1e-9

    def test_all_zero_gives_zero(self):
        traits = {
            "quiet_resilience":   0.0,
            "self_sufficiency":   0.0,
            "adaptability":       0.0,
            "identity_stability": 0.0,
        }
        r = _compute_resilience(traits)
        assert abs(r) < 1e-9

    def test_joey_more_resilient_than_chandler(self):
        """
        Joey should be more worldview-resilient than Chandler.
        Both now have explicit trait values in soul_docs.
        """
        import yaml
        soul_dir = ROOT / "core" / "soul_doc"
        chandler = yaml.safe_load((soul_dir / "chandler_bing.yaml").read_text())
        joey     = yaml.safe_load((soul_dir / "joey_tribbiani.yaml").read_text())
        r_chandler = _compute_resilience(chandler.get("trait_weights", {}))
        r_joey     = _compute_resilience(joey.get("trait_weights", {}))
        assert r_joey > r_chandler, (
            f"Expected joey ({r_joey:.3f}) > chandler ({r_chandler:.3f})"
        )

    def test_all_soul_docs_have_resilience_traits(self):
        """Every soul_doc YAML should now have all four resilience traits."""
        import yaml
        REQUIRED = {"quiet_resilience", "self_sufficiency", "adaptability", "identity_stability"}
        soul_dir = ROOT / "core" / "soul_doc"
        for path in soul_dir.glob("*.yaml"):
            doc    = yaml.safe_load(path.read_text()) or {}
            traits = set(doc.get("trait_weights", {}).keys())
            missing = REQUIRED - traits
            assert not missing, f"{path.name} is missing traits: {missing}"
