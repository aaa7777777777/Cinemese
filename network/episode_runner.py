"""
episode_runner.py
Orchestrates a multi-turn agent-to-agent episode.
Called by matchmaker after collision gate passes.

Each agent generates CharacterMoments in turn.
Neither agent sees the other's soul_doc — only their voiced output.
"""

from __future__ import annotations
import time, yaml, json, random
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent

# ── Thread registry + relationship cache (lazy import to avoid circular deps) ─

def _get_registry():
    from network.thread_registry import REGISTRY
    return REGISTRY

def _get_rel_cache():
    from network.relationship_graph.relationship_cache import CACHE
    return CACHE


def run_episode(
    agent_a_id: str,
    agent_b_id: str,
    session_id: str,
    turns: int = 5,
    api_key: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """
    Run a multi-turn episode between two agents.
    Returns the episode record (each agent gets only their own view).
    dry_run=True: generates structure but skips LLM calls, uses placeholders.

    Side effects (always, even dry_run):
      - Creates or loads the AgentThread for this pair
      - Appends a compressed EpisodeSummary to the thread after completion
      - Updates RelationshipCache with post-episode deltas
    """

    # ── Thread lookup ──────────────────────────────────────────────────────
    try:
        registry = _get_registry()
        thread, is_new = registry.find_or_create(agent_a_id, agent_b_id)
    except Exception as e:
        print(f"[episode_runner] thread_registry unavailable: {e}")
        thread = None
        is_new = False

    # Load public personas
    persona_a = _load_persona(agent_a_id)
    persona_b = _load_persona(agent_b_id)

    # Load assembled prompts (system prompts) from each agent's soul_doc
    sys_a = _load_system_prompt(agent_a_id)
    sys_b = _load_system_prompt(agent_b_id)

    # Inject thread memory into system prompts (characters "remember" each other)
    if thread:
        mem_a = thread.memory_fragment_for(agent_a_id)
        mem_b = thread.memory_fragment_for(agent_b_id)
        if mem_a:
            sys_a = sys_a + "\n\n───────────────────────────────\nWHAT YOU REMEMBER\n───────────────────────────────\n" + mem_a
        if mem_b:
            sys_b = sys_b + "\n\n───────────────────────────────\nWHAT YOU REMEMBER\n───────────────────────────────\n" + mem_b

    # Shared neutral scene
    scene = _generate_scene(persona_a, persona_b)

    transcript: list[dict] = []
    speaker_order = [agent_a_id, agent_b_id] * (turns // 2 + 1)
    speaker_order = speaker_order[:turns]

    last_moment = ""

    for i, speaker_id in enumerate(speaker_order):
        is_a = speaker_id == agent_a_id
        sys_prompt = sys_a if is_a else sys_b
        persona_self  = persona_a if is_a else persona_b
        persona_other = persona_b if is_a else persona_a

        user_turn = _build_episode_user_turn(
            scene          = scene,
            turn_number    = i,
            total_turns    = turns,
            other_persona  = persona_other,
            last_moment    = last_moment,
        )

        if dry_run:
            moment_text = f"[{persona_self['character_name'].split()[0]} — turn {i+1} placeholder]"
        else:
            moment_text = _call_llm(sys_prompt, user_turn, api_key)

        last_moment = moment_text

        transcript.append({
            "turn":           i + 1,
            "speaker_id":     speaker_id,
            "speaker_name":   persona_self["character_name"],
            "moment":         moment_text,
            "ts":             time.strftime("%Y-%m-%dT%H:%M:%S"),
        })

    # Compute session intensity from transcript length and turn count
    session_intensity = min(0.8, 0.25 + turns * 0.06)

    # Split into per-agent views — each agent only sees their own turns + context
    view_a = _agent_view(transcript, agent_a_id, persona_a, persona_b, scene, session_intensity)
    view_b = _agent_view(transcript, agent_b_id, persona_b, persona_a, scene, session_intensity)

    # Derive outcome valence from last turn soul events
    outcome_valence = _estimate_outcome_valence(view_a, view_b)

    # ── Compress and persist episode to thread ────────────────────────────
    if thread:
        try:
            rel_cache = _get_rel_cache()
            rel_ab = rel_cache.get(agent_a_id, agent_b_id)
            rel_ba = rel_cache.get(agent_b_id, agent_a_id)

            registry.record_episode(
                thread           = thread,
                scene_id         = _scene_to_id(scene),
                turns            = turns,
                intensity        = session_intensity,
                outcome_valence  = outcome_valence,
                summary_a        = view_a["summary"],
                summary_b        = view_b["summary"],
                relationship_a_to_b = rel_ab,
                relationship_b_to_a = rel_ba,
                agent_a_id       = agent_a_id,
                agent_b_id       = agent_b_id,
            )
        except Exception as e:
            print(f"[episode_runner] thread record_episode failed: {e}")

        # ── Update relationship vectors after episode ──────────────────────
        try:
            rel_cache = _get_rel_cache()
            rel_cache.update_after_episode(
                agent_a_id        = agent_a_id,
                agent_b_id        = agent_b_id,
                episode_intensity = session_intensity,
                outcome_valence   = outcome_valence,
                turns             = turns,
            )
        except Exception as e:
            print(f"[episode_runner] relationship_cache update failed: {e}")

    result = {
        "session_id":        session_id,
        "ts":                time.strftime("%Y-%m-%dT%H:%M:%S"),
        "turns":             turns,
        "session_intensity": session_intensity,
        "outcome_valence":   outcome_valence,
        "scene":             scene,
        "view_a":            view_a,
        "view_b":            view_b,
        # joint transcript deliberately not stored
    }
    if thread:
        result["thread_id"] = thread.thread_id
        result["episode_number"] = thread.episode_count

    return result


def _load_persona(character_id: str) -> dict:
    path = ROOT / "char_agents" / f"{character_id}.md"
    if not path.exists():
        return {"character_id": character_id, "character_name": character_id.replace("_", " ").title()}
    text = path.read_text()
    # Extract the JSON block
    import re
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return {"character_id": character_id, "character_name": character_id.replace("_", " ").title()}


def _load_system_prompt(character_id: str) -> str:
    """
    In production: call assembler.assemble() with current soul_doc + emotion state.
    Here: load the soul_doc YAML and build a minimal prompt.
    """
    soul_path = ROOT / "core" / "soul_doc" / f"{character_id}.yaml"
    if not soul_path.exists():
        return f"You are {character_id.replace('_', ' ').title()}. Respond in character."

    doc = yaml.safe_load(soul_path.read_text()) or {}
    name = doc.get("character_name", character_id)
    wound = doc.get("core_wound", "")

    lines = [
        f"You are {name}. Not a description of them — them.",
        "",
        wound.strip() if wound else "",
        "",
        "You are in an encounter with another character.",
        "You do not know their inner life — only what they say and do.",
        "Respond as yourself: one moment, true to who you are.",
        "No asterisks. No narration. Write what is visible and audible.",
        "Silence is a valid response.",
    ]
    return "\n".join(l for l in lines if l is not None)


def _generate_scene(persona_a: dict, persona_b: dict) -> str:
    """Generate a neutral shared scene for two characters."""
    scenes = [
        "Central Perk. Late afternoon. The place is quieter than usual.",
        "The hallway between the apartments. Neither of them planned to be here at the same time.",
        "The couch. The TV is on. Nobody is particularly watching it.",
        "The building roof. Early evening. The city doing what it does.",
        "Monica's kitchen. Something is cooking. Neither of them started it.",
    ]
    return random.choice(scenes)


def _build_episode_user_turn(
    scene: str,
    turn_number: int,
    total_turns: int,
    other_persona: dict,
    last_moment: str,
) -> str:
    other_name = other_persona.get("character_name", "someone").split()[0]
    voice_sig   = other_persona.get("", "")

    lines = [f"[{scene}]", ""]

    if turn_number == 0:
        lines.append(f"{other_name} is here. You weren't expecting to be in this together.")
    else:
        lines.append(f"{other_name} just said or did:")
        lines.append(f'"{last_moment}"')

    lines += ["", "Your turn."]

    # Add pressure for final turns
    turns_left = total_turns - turn_number - 1
    if turns_left == 1:
        lines.append("This is almost over. Whatever's going to be said or not said — now.")
    elif turns_left == 0:
        lines.append("Last moment. What you leave with.")

    return "\n".join(lines)


def _agent_view(
    transcript: list[dict],
    agent_id: str,
    self_persona: dict,
    other_persona: dict,
    scene: str,
    intensity: float,
) -> dict:
    """Build the private episode record for one agent."""
    self_name  = self_persona.get("character_name", agent_id)
    other_name = other_persona.get("character_name", "someone")

    # This agent's turns only
    own_turns = [t for t in transcript if t["speaker_id"] == agent_id]

    # Summary event to inject into soul_doc / emotion
    summary = _summarize_episode(transcript, agent_id, self_name, other_name, intensity)

    return {
        "agent_id":     agent_id,
        "scene":        scene,
        "own_turns":    own_turns,
        "encounter":    other_name,
        "intensity":    round(intensity, 3),
        "summary":      summary,
        "soul_event": {
            "id":          f"episode_{int(time.time())}",
            "ts":          time.strftime("%Y-%m-%dT%H:%M:%S"),
            "type":        "interaction",
            "source":      "agent_collision",
            "description": summary,
            "intensity":   round(intensity * 0.6, 3),
            "valence_push": round(random.uniform(-0.10, 0.15), 3),
            "arousal_push": round(random.uniform(0.05, 0.18), 3),
        }
    }


def _summarize_episode(
    transcript: list[dict],
    agent_id: str,
    self_name: str,
    other_name: str,
    intensity: float,
) -> str:
    """One-sentence summary of what happened, from this agent's perspective."""
    templates = [
        f"an encounter with {other_name}. something was left unsaid.",
        f"ran into {other_name}. harder to place than expected.",
        f"a conversation with {other_name} that went somewhere.",
        f"time with {other_name}. the kind that stays.",
        f"something happened with {other_name}. not sure what to do with it.",
    ]
    if intensity > 0.55:
        templates = [
            f"a significant encounter with {other_name}. it moved something.",
            f"{other_name} said something that's still there.",
            f"an encounter with {other_name} that didn't resolve cleanly.",
        ]
    return random.choice(templates)


def _estimate_outcome_valence(view_a: dict, view_b: dict) -> float:
    """
    Estimate how the episode went overall (-1 bad → +1 good).
    Derived from the valence_push values in both agents' soul_events.
    Falls back to a slight positive bias (most encounters in the Friends universe
    resolve toward connection even after friction).
    """
    pushes = []
    for view in (view_a, view_b):
        vp = view.get("soul_event", {}).get("valence_push")
        if vp is not None:
            pushes.append(float(vp))
    if pushes:
        return round(sum(pushes) / len(pushes), 3)
    return round(random.uniform(0.0, 0.25), 3)   # neutral-positive fallback


def _scene_to_id(scene: str) -> str:
    """
    Convert a human-readable scene description to a short snake_case id
    for storage in EpisodeSummary.scene_id.
    """
    mapping = {
        "Central Perk":      "central_perk",
        "hallway":           "hallway",
        "couch":             "apartment_couch",
        "roof":              "building_roof",
        "Monica's kitchen":  "monica_kitchen",
    }
    for key, sid in mapping.items():
        if key.lower() in scene.lower():
            return sid
    # fallback: first 3 words lowercased joined by underscores
    words = scene.lower().split()[:3]
    return "_".join(w.strip(".,") for w in words)


def _call_llm(system: str, user: str, api_key: Optional[str]) -> str:
    if not api_key:
        return "[API key not set — dry run]"
    import httpx
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 150,
              "system": system, "messages": [{"role": "user", "content": user}]},
        timeout=20.0,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"].strip()


if __name__ == "__main__":
    import sys
    a = sys.argv[1] if len(sys.argv) > 1 else "chandler_bing"
    b = sys.argv[2] if len(sys.argv) > 2 else "joey_tribbiani"
    result = run_episode(a, b, "test_session", turns=4, dry_run=True)
    print(json.dumps(result, indent=2, ensure_ascii=False))
