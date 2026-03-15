"""
relationship_cache.py

Runtime cache for relationship vectors.
- Hand-authored (Friends cast) loaded from relationships.yaml at startup
- Stranger pairs computed on demand and cached in memory + optional disk
- Updated after each episode via update_after_episode()

Used by dialogue_engine as a drop-in replacement for
direct YAML lookups — it doesn't know if a relationship
was authored or computed.
"""
from __future__ import annotations
import yaml
import json
import time
from pathlib import Path
from typing import Optional
from .relationship_initializer import (
    RelationshipVector,
    initialize_stranger_relationship,
    update_after_episode,
)

ROOT = Path(__file__).parent.parent.parent


class RelationshipCache:

    def __init__(self, authored_path: Optional[Path] = None):
        # {(from_id, to_id): RelationshipVector}
        self._cache: dict[tuple[str, str], RelationshipVector] = {}

        # Load hand-authored relationships
        p = authored_path or (ROOT / "network" / "relationship_graph" / "relationships.yaml")
        if p.exists():
            self._load_authored(p)

        # Disk cache for computed stranger relationships
        self._disk_path = ROOT / "network" / "relationship_graph" / "stranger_cache.json"
        if self._disk_path.exists():
            self._load_from_disk()

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, from_id: str, to_id: str,
            doc_from: Optional[dict] = None,
            doc_to:   Optional[dict] = None) -> dict:
        """
        Returns a relationship dict (same shape as relationships.yaml entries).
        If the relationship doesn't exist yet, computes it from soul_docs.
        """
        key = (from_id, to_id)

        if key not in self._cache:
            if doc_from and doc_to:
                # Compute stranger relationship
                vec_ab, vec_ba = initialize_stranger_relationship(doc_from, doc_to)
                self._cache[(from_id, to_id)] = vec_ab
                self._cache[(to_id, from_id)] = vec_ba
                self._save_to_disk()
            else:
                # Try loading soul_docs from disk
                loaded = self._try_load_and_compute(from_id, to_id)
                if not loaded:
                    return self._default_stranger(from_id, to_id)

        return self._cache[key].to_dict()

    def update_after_episode(
        self,
        agent_a_id:        str,
        agent_b_id:        str,
        episode_intensity: float,
        outcome_valence:   float,
        turns:             int = 4,
    ):
        """Called by episode_runner after a dialogue session ends."""
        for from_id, to_id in [(agent_a_id, agent_b_id), (agent_b_id, agent_a_id)]:
            key = (from_id, to_id)
            if key in self._cache:
                self._cache[key] = update_after_episode(
                    self._cache[key], episode_intensity, outcome_valence, turns
                )
        self._save_to_disk()

    def address_weights(self, speaker_id: str, participants: list[str],
                        docs: Optional[dict[str, dict]] = None) -> dict[str, float]:
        """Return probability weights for who speaker might address."""
        others = [p for p in participants if p != speaker_id]
        weights = {}
        for other in others:
            doc_s = docs.get(speaker_id) if docs else None
            doc_o = docs.get(other) if docs else None
            rel   = self.get(speaker_id, other, doc_s, doc_o)
            weights[other] = rel.get("address_weight", 0.12)
        weights["__room__"] = 0.15 + 0.04 * len(others)
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}

    def register_for(self, speaker_id: str, addressee_id: Optional[str],
                     docs: Optional[dict[str, dict]] = None) -> str:
        if not addressee_id:
            return "speaking to the room or to no one in particular"
        doc_s = docs.get(speaker_id)  if docs else None
        doc_o = docs.get(addressee_id) if docs else None
        rel = self.get(speaker_id, addressee_id, doc_s, doc_o)
        return rel.get("register", "stranger — first impression forming")

    def summary(self, agent_a_id: str, agent_b_id: str) -> dict:
        """Human-readable summary of the A↔B relationship state."""
        ab = self.get(agent_a_id, agent_b_id)
        ba = self.get(agent_b_id, agent_a_id)
        return {
            f"{agent_a_id} → {agent_b_id}": ab,
            f"{agent_b_id} → {agent_a_id}": ba,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_authored(self, path: Path):
        data = yaml.safe_load(path.read_text()) or {}
        rels = data.get("relationships", {})
        for from_id, targets in rels.items():
            for to_id, props in targets.items():
                vec = RelationshipVector(
                    from_id          = from_id,
                    to_id            = to_id,
                    weight           = props.get("weight", 0.5),
                    friction         = props.get("friction", 0.2),
                    emotion_transfer = props.get("emotion_transfer", 0.3),
                    address_weight   = props.get("address_weight", 0.15),
                    register         = props.get("register", ""),
                    valence          = props.get("valence", "neutral"),
                    notes            = props.get("notes", "authored"),
                )
                self._cache[(from_id, to_id)] = vec

    def _try_load_and_compute(self, from_id: str, to_id: str) -> bool:
        soul_dir = ROOT / "core" / "soul_doc"
        path_a   = soul_dir / f"{from_id}.yaml"
        path_b   = soul_dir / f"{to_id}.yaml"
        if not path_a.exists() or not path_b.exists():
            return False
        doc_a = yaml.safe_load(path_a.read_text()) or {}
        doc_b = yaml.safe_load(path_b.read_text()) or {}
        vec_ab, vec_ba = initialize_stranger_relationship(doc_a, doc_b)
        self._cache[(from_id, to_id)] = vec_ab
        self._cache[(to_id, from_id)] = vec_ba
        self._save_to_disk()
        return True

    def _default_stranger(self, from_id: str, to_id: str) -> dict:
        return {
            "weight": 0.30, "friction": 0.18,
            "emotion_transfer": 0.22, "address_weight": 0.10,
            "register": "stranger — no data yet",
            "valence": "neutral", "notes": "default fallback",
        }

    def _save_to_disk(self):
        try:
            data = {}
            for (fid, tid), vec in self._cache.items():
                # Only persist computed (stranger) relationships, not authored
                if vec.notes and "authored" not in vec.notes:
                    key = f"{fid}||{tid}"
                    data[key] = {
                        "weight":           vec.weight,
                        "friction":         vec.friction,
                        "emotion_transfer": vec.emotion_transfer,
                        "address_weight":   vec.address_weight,
                        "register":         vec.register,
                        "valence":          vec.valence,
                        "resonance_score":  vec.resonance_score,
                        "fit_score":        vec.fit_score,
                        "overlap_score":    vec.overlap_score,
                        "notes":            vec.notes,
                    }
            self._disk_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"[relationship_cache] disk write failed: {e}")

    def _load_from_disk(self):
        try:
            data = json.loads(self._disk_path.read_text())
            for key, props in data.items():
                fid, tid = key.split("||")
                vec = RelationshipVector(
                    from_id          = fid,
                    to_id            = tid,
                    weight           = props["weight"],
                    friction         = props["friction"],
                    emotion_transfer = props["emotion_transfer"],
                    address_weight   = props["address_weight"],
                    register         = props["register"],
                    valence          = props["valence"],
                    resonance_score  = props.get("resonance_score", 0),
                    fit_score        = props.get("fit_score", 0),
                    overlap_score    = props.get("overlap_score", 0),
                    notes            = props.get("notes", ""),
                )
                self._cache[(fid, tid)] = vec
        except Exception as e:
            print(f"[relationship_cache] disk load failed: {e}")


# Module-level singleton — imported by dialogue_engine
CACHE = RelationshipCache()
