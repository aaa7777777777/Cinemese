# MATCHMAKING.md — multi-agent collision spec

## Privacy model

Agent A and Agent B never see each other's soul_doc.
They see only each other's `char_agents/{id}.md` — the public persona file.

What the public persona contains:
- character name + world tags
- current emotion color (not the full state vector)
- current event type (not the description)
- event_score + micro_score combined as a single `tension_score`
- available_for_interaction: bool

What it does NOT contain:
- soul_doc content
- life nodes
- habit loops
- internal fragments

---

## Scoring

Each agent carries two live scores, written by planning.py every tick:

```
tension_score = event_engine.current_score + emotion_engine.micro_score
```

Range: 0–200.

---

## Collision gate

Two agents can attempt interaction when ALL of:

1. Both `available_for_interaction: true`

2. `|agent_A.tension_score - agent_B.tension_score| ≤ collision_threshold`
   (default: 80 — neither too similar nor too distant)

3. `agent_A.tension_score + agent_B.tension_score ≤ collision_threshold * 2`
   (default: 160 — combined intensity doesn't spike above system ceiling)

4. Event types are compatible:
   ```
   compatible_pairs:
     quiet_moment   ↔ quiet_moment
     quiet_moment   ↔ internal_shift
     interaction    ↔ interaction
     interaction    ↔ discovery
     discovery      ↔ internal_shift
     conflict       ↔ conflict       (high stakes — requires allow_high_intensity)
   ```

5. Last interaction between these two agents was > min_reinteract_hours ago
   (default: 6h)

---

## What happens during collision

1. `matchmaker.py` pairs the two agents, writes a shared `session_id`

2. `episode_runner.py` creates a joint session:
   - both agents receive the other's `public_persona` as context
   - both agents receive a shared `scene_context` (neutral location)
   - episode_runner orchestrates N turns (default: 4–8)

3. Each agent generates a `CharacterMoment` per turn via `api.chat`
   - using their own soul_doc + emotion_state + event_context
   - plus the other agent's last `CharacterMoment` as conversation input

4. After session ends:
   - `episode_runner` calls `event_engine.inject()` for each agent
     with a summary event (intensity = session_intensity * 0.6)
   - emotion states updated via `emotion_engine.receive_event()`
   - session transcript NOT persisted — each agent gets only their own view

5. If session intensity > 0.6:
   - both agents get an `episode_push` skill output
   - owners see: "[character name] had an encounter" — no details

---

## Smoothness requirement

New combined score after collision must not exceed
pre-collision combined score by more than 20%:

```python
pre  = agent_A.tension_score + agent_B.tension_score
post = (agent_A.tension_score + event_delta_A) + (agent_B.tension_score + event_delta_B)
assert post <= pre * 1.20
```

If this would be violated, episode_runner reduces the session's generated
event intensity until the constraint is satisfied.

---

## Matchmaking algorithm

```python
def find_match(agent: Agent, pool: list[Agent]) -> Agent | None:
    candidates = [
        a for a in pool
        if a.id != agent.id
        and a.available_for_interaction
        and abs(a.tension_score - agent.tension_score) <= COLLISION_THRESHOLD
        and (a.tension_score + agent.tension_score) <= COLLISION_THRESHOLD * 2
        and compatible_event_types(a.last_event_type, agent.last_event_type)
        and hours_since_last_interaction(agent.id, a.id) >= MIN_REINTERACT_HOURS
    ]
    if not candidates:
        return None
    # pick closest tension score for smoothest interaction
    return min(candidates, key=lambda a: abs(a.tension_score - agent.tension_score))
```
