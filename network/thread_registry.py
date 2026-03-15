"""
thread_registry.py

Every pair of agents has exactly one persistent thread.
thread_id = deterministic hash of sorted(agent_a_id, agent_b_id)

A thread holds:
- the canonical id (stable across all sessions)
- the episode archive (all past turns, compressed)
- the live relationship vector
- metadata for UI routing

When two agents meet again, the matchmaker calls find_or_create()
instead of starting a blank session. The dialogue engine receives
the thread and injects the episode archive into the system prompt
so each character "remembers" what happened last time.
"""
from __future__ import annotations
import json
import hashlib
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
THREADS_DIR = ROOT / "network" / "threads"
THREADS_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# Thread record
# ─────────────────────────────────────────────

@dataclass
class EpisodeSummary:
    """Compressed record of one past meeting — injected into future prompts."""
    episode_number:  int
    ts:              str
    scene_id:        str
    turns:           int
    intensity:       float
    outcome_valence: float        # -1 bad → +1 good
    # One-sentence summary per agent's perspective
    summary_a:       str          # what agent_a took away
    summary_b:       str          # what agent_b took away


@dataclass
class AgentThread:
    thread_id:    str            # hash(sorted(a,b)) — stable forever
    agent_a_id:   str            # always the lexicographically smaller id
    agent_b_id:   str
    created_at:   str
    last_met_at:  str
    episode_count: int = 0

    # Compressed history — grows slowly, used in prompts
    episodes:     list[EpisodeSummary] = field(default_factory=list)

    # Live relationship state — updated after each episode
    relationship_a_to_b: dict = field(default_factory=dict)
    relationship_b_to_a: dict = field(default_factory=dict)

    # For UI routing: which users own these agents
    owner_a: Optional[str] = None
    owner_b: Optional[str] = None

    def memory_fragment_for(self, agent_id: str) -> str:
        """
        Returns a short memory paragraph to inject into the system prompt.
        Shows only this agent's perspective on past meetings.
        """
        if not self.episodes:
            return ""

        is_a = (agent_id == self.agent_a_id)
        other_id = self.agent_b_id if is_a else self.agent_a_id

        lines = [f"You have met this person before. {len(self.episodes)} time(s)."]

        # Last 3 episodes only — don't flood the prompt
        for ep in self.episodes[-3:]:
            summary = ep.summary_a if is_a else ep.summary_b
            valence_word = (
                "well" if ep.outcome_valence > 0.3
                else "badly" if ep.outcome_valence < -0.3
                else "inconclusively"
            )
            lines.append(
                f"Episode {ep.episode_number} ({ep.ts[:10]}, {ep.scene_id.replace('_',' ')}): "
                f"{summary} It ended {valence_word}."
            )

        # Current relationship state
        rel = self.relationship_a_to_b if is_a else self.relationship_b_to_a
        if rel:
            register = rel.get("register", "")
            valence  = rel.get("valence", "neutral")
            if register:
                lines.append(f"Right now: {register}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["episodes"] = [asdict(e) for e in self.episodes]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AgentThread":
        episodes = [EpisodeSummary(**e) for e in d.pop("episodes", [])]
        thread   = cls(**d)
        thread.episodes = episodes
        return thread


# ─────────────────────────────────────────────
# Thread ID generation
# ─────────────────────────────────────────────

def make_thread_id(agent_a_id: str, agent_b_id: str) -> str:
    """
    Deterministic, order-independent hash.
    sorted() ensures hash(A,B) == hash(B,A).
    """
    pair = ":".join(sorted([agent_a_id, agent_b_id]))
    return hashlib.sha1(pair.encode()).hexdigest()[:12]


def canonical_order(id_a: str, id_b: str) -> tuple[str, str]:
    """Always put the lexicographically smaller id first."""
    return (id_a, id_b) if id_a <= id_b else (id_b, id_a)


# ─────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────

class ThreadRegistry:

    def __init__(self, threads_dir: Path = THREADS_DIR):
        self.dir = threads_dir
        self.dir.mkdir(exist_ok=True)
        self._cache: dict[str, AgentThread] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def find_or_create(
        self,
        agent_a_id: str,
        agent_b_id: str,
        owner_a:    Optional[str] = None,
        owner_b:    Optional[str] = None,
    ) -> tuple[AgentThread, bool]:
        """
        Returns (thread, is_new).
        If a thread for this pair exists, loads it.
        If not, creates one.
        This is the single entry point — matchmaker always calls this.
        """
        a, b      = canonical_order(agent_a_id, agent_b_id)
        thread_id = make_thread_id(a, b)

        # Memory cache
        if thread_id in self._cache:
            return self._cache[thread_id], False

        # Disk
        path = self.dir / f"{thread_id}.json"
        if path.exists():
            thread = AgentThread.from_dict(json.loads(path.read_text()))
            self._cache[thread_id] = thread
            return thread, False

        # New
        thread = AgentThread(
            thread_id    = thread_id,
            agent_a_id   = a,
            agent_b_id   = b,
            created_at   = time.strftime("%Y-%m-%dT%H:%M:%S"),
            last_met_at  = time.strftime("%Y-%m-%dT%H:%M:%S"),
            owner_a      = owner_a,
            owner_b      = owner_b,
        )
        self._cache[thread_id] = thread
        self._save(thread)
        return thread, True

    def get(self, thread_id: str) -> Optional[AgentThread]:
        """Load a thread by its id — used by UI routing."""
        if thread_id in self._cache:
            return self._cache[thread_id]
        path = self.dir / f"{thread_id}.json"
        if path.exists():
            thread = AgentThread.from_dict(json.loads(path.read_text()))
            self._cache[thread_id] = thread
            return thread
        return None

    def get_by_pair(self, agent_a_id: str, agent_b_id: str) -> Optional[AgentThread]:
        tid = make_thread_id(*canonical_order(agent_a_id, agent_b_id))
        return self.get(tid)

    def record_episode(
        self,
        thread:          AgentThread,
        scene_id:        str,
        turns:           int,
        intensity:       float,
        outcome_valence: float,
        summary_a:       str,
        summary_b:       str,
        relationship_a_to_b: dict,
        relationship_b_to_a: dict,
        agent_a_id:      Optional[str] = None,
        agent_b_id:      Optional[str] = None,
    ) -> AgentThread:
        """
        Called by episode_runner after a session ends.
        Appends a compressed summary and updates relationship state.

        summary_a and summary_b must correspond to agent_a_id and agent_b_id
        as passed by the caller — this method re-maps them to the thread's
        canonical agent_a/agent_b order so memory_fragment_for() stays correct.

        If agent_a_id / agent_b_id are not supplied, summaries are assumed to
        already be in canonical thread order.
        """
        thread.episode_count += 1
        thread.last_met_at    = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Re-map summaries to canonical thread order if caller specified IDs
        if agent_a_id and agent_b_id and agent_a_id != thread.agent_a_id:
            # caller's a is thread's b — swap
            summary_a, summary_b = summary_b, summary_a
            relationship_a_to_b, relationship_b_to_a = relationship_b_to_a, relationship_a_to_b

        ep = EpisodeSummary(
            episode_number  = thread.episode_count,
            ts              = time.strftime("%Y-%m-%dT%H:%M:%S"),
            scene_id        = scene_id,
            turns           = turns,
            intensity       = round(intensity, 3),
            outcome_valence = round(outcome_valence, 3),
            summary_a       = summary_a,
            summary_b       = summary_b,
        )
        thread.episodes.append(ep)

        # Keep at most 20 episodes in the record
        if len(thread.episodes) > 20:
            thread.episodes = thread.episodes[-20:]

        thread.relationship_a_to_b = relationship_a_to_b
        thread.relationship_b_to_a = relationship_b_to_a

        self._save(thread)
        return thread

    def threads_for_agent(self, agent_id: str) -> list[AgentThread]:
        """Return all threads this agent is part of — for UI thread list."""
        results = []
        for path in self.dir.glob("*.json"):
            try:
                t = AgentThread.from_dict(json.loads(path.read_text()))
                if agent_id in (t.agent_a_id, t.agent_b_id):
                    results.append(t)
            except Exception:
                pass
        results.sort(key=lambda t: t.last_met_at, reverse=True)
        return results

    def threads_for_owner(self, owner_id: str) -> list[AgentThread]:
        """Return all threads owned by this user — for UI inbox."""
        results = []
        for path in self.dir.glob("*.json"):
            try:
                t = AgentThread.from_dict(json.loads(path.read_text()))
                if owner_id in (t.owner_a, t.owner_b):
                    results.append(t)
            except Exception:
                pass
        results.sort(key=lambda t: t.last_met_at, reverse=True)
        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    def _save(self, thread: AgentThread):
        path = self.dir / f"{thread.thread_id}.json"
        path.write_text(json.dumps(thread.to_dict(), indent=2, ensure_ascii=False))


# Module singleton
REGISTRY = ThreadRegistry()
