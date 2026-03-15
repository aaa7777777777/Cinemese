"""
tests/test_assembler.py
Regression tests for the TypeScript assembler output format.
Tests the Python-accessible soul_doc loading + field consistency.

Run with:  python -m pytest tests/test_assembler.py -v
"""
from __future__ import annotations
import sys, yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────
# Soul doc schema consistency
# ─────────────────────────────────────────────

class TestSoulDocSchema:
    """
    Each YAML soul_doc must have the required fields so episode_runner
    and assembler can load them without KeyError.
    """
    REQUIRED_FIELDS = {
        "character_id",
        "character_name",
        "trait_weights",
        "life_nodes",
    }
    OPTIONAL_BUT_TYPED = {
        "core_wound": str,
        "social_drift": list,
        "habit_loops": list,
        "world_lore": str,
    }

    def _all_soul_docs(self) -> list[tuple[Path, dict]]:
        soul_dir = ROOT / "core" / "soul_doc"
        return [
            (p, yaml.safe_load(p.read_text()) or {})
            for p in soul_dir.glob("*.yaml")
        ]

    def test_required_fields_present(self):
        for path, doc in self._all_soul_docs():
            missing = self.REQUIRED_FIELDS - set(doc.keys())
            assert not missing, f"{path.name} missing required fields: {missing}"

    def test_trait_weights_are_floats(self):
        for path, doc in self._all_soul_docs():
            tw = doc.get("trait_weights", {})
            assert isinstance(tw, dict), f"{path.name}: trait_weights must be a dict"
            for trait, val in tw.items():
                assert isinstance(val, (int, float)), (
                    f"{path.name}: trait '{trait}' value {val!r} is not numeric"
                )
                assert 0.0 <= val <= 1.0, (
                    f"{path.name}: trait '{trait}' value {val} outside [0, 1]"
                )

    def test_life_nodes_have_required_keys(self):
        NODE_REQUIRED = {"id", "ts", "event", "delta", "locked"}
        for path, doc in self._all_soul_docs():
            nodes = doc.get("life_nodes", [])
            for i, node in enumerate(nodes):
                missing = NODE_REQUIRED - set(node.keys())
                assert not missing, (
                    f"{path.name} node[{i}] ({node.get('id', '?')}) missing: {missing}"
                )

    def test_habit_loops_use_numeric_intensity(self):
        """
        Ensure all habit loops use emotional_intensity_above (float),
        not the deprecated string '>0.6' format.
        """
        for path, doc in self._all_soul_docs():
            loops = doc.get("habit_loops", [])
            for loop in loops:
                cond = loop.get("condition", {})
                legacy = cond.get("emotional_intensity")
                if legacy is not None:
                    assert isinstance(legacy, (int, float)), (
                        f"{path.name} habit loop '{loop.get('id')}' still uses "
                        f"string emotional_intensity: {legacy!r} — "
                        f"migrate to emotional_intensity_above (numeric)"
                    )
                above = cond.get("emotional_intensity_above")
                if above is not None:
                    assert isinstance(above, (int, float)), (
                        f"{path.name} habit loop '{loop.get('id')}' "
                        f"emotional_intensity_above must be numeric, got {above!r}"
                    )

    def test_character_name_not_empty(self):
        for path, doc in self._all_soul_docs():
            name = doc.get("character_name") or doc.get("name", "")
            assert name.strip(), f"{path.name}: character_name is empty"


# ─────────────────────────────────────────────
# Thread registry — find_or_create is idempotent
# ─────────────────────────────────────────────

class TestThreadRegistry:
    def test_find_or_create_idempotent(self, tmp_path):
        from network.thread_registry import ThreadRegistry
        reg = ThreadRegistry(threads_dir=tmp_path)
        t1, new1 = reg.find_or_create("chandler_bing", "joey_tribbiani")
        t2, new2 = reg.find_or_create("chandler_bing", "joey_tribbiani")
        assert new1 is True
        assert new2 is False
        assert t1.thread_id == t2.thread_id

    def test_order_independent(self, tmp_path):
        from network.thread_registry import ThreadRegistry
        reg = ThreadRegistry(threads_dir=tmp_path)
        t1, _ = reg.find_or_create("chandler_bing", "joey_tribbiani")
        t2, _ = reg.find_or_create("joey_tribbiani", "chandler_bing")
        assert t1.thread_id == t2.thread_id

    def test_record_episode_appends(self, tmp_path):
        from network.thread_registry import ThreadRegistry
        reg = ThreadRegistry(threads_dir=tmp_path)
        thread, _ = reg.find_or_create("chandler_bing", "ross_geller")
        reg.record_episode(
            thread=thread,
            scene_id="central_perk",
            turns=4,
            intensity=0.45,
            outcome_valence=0.2,
            summary_a="something shifted",
            summary_b="not sure what to do with it",
            relationship_a_to_b={"weight": 0.7},
            relationship_b_to_a={"weight": 0.6},
        )
        assert thread.episode_count == 1
        assert len(thread.episodes) == 1
        assert thread.episodes[0].scene_id == "central_perk"

    def test_episode_cap_at_20(self, tmp_path):
        from network.thread_registry import ThreadRegistry
        reg = ThreadRegistry(threads_dir=tmp_path)
        thread, _ = reg.find_or_create("monica_geller", "rachel_green")
        for i in range(25):
            reg.record_episode(
                thread=thread,
                scene_id=f"scene_{i}",
                turns=3,
                intensity=0.3,
                outcome_valence=0.1,
                summary_a=f"episode {i} for a",
                summary_b=f"episode {i} for b",
                relationship_a_to_b={},
                relationship_b_to_a={},
            )
        assert len(thread.episodes) == 20

    def test_memory_fragment_excludes_other_agent(self, tmp_path):
        from network.thread_registry import ThreadRegistry
        reg = ThreadRegistry(threads_dir=tmp_path)
        thread, _ = reg.find_or_create("phoebe_buffay", "monica_geller")
        # canonical order: monica < phoebe → thread.agent_a_id = "monica_geller"
        # pass agent IDs so record_episode can re-map correctly
        reg.record_episode(
            thread=thread,
            scene_id="central_perk",
            turns=4,
            intensity=0.4,
            outcome_valence=0.3,
            summary_a="phoebe's perspective",   # phoebe is caller's "a"
            summary_b="monica's perspective",   # monica is caller's "b"
            relationship_a_to_b={},
            relationship_b_to_a={},
            agent_a_id="phoebe_buffay",         # caller's a
            agent_b_id="monica_geller",         # caller's b
        )
        frag_phoebe = thread.memory_fragment_for("phoebe_buffay")
        frag_monica = thread.memory_fragment_for("monica_geller")
        assert "phoebe's perspective" in frag_phoebe, (
            f"Expected phoebe's perspective in phoebe's fragment.\nGot: {frag_phoebe}"
        )
        assert "monica's perspective" in frag_monica, (
            f"Expected monica's perspective in monica's fragment.\nGot: {frag_monica}"
        )
        # perspectives must NOT cross-contaminate
        assert "monica's perspective" not in frag_phoebe
        assert "phoebe's perspective" not in frag_monica
