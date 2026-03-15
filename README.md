# Cinemese

**A web/app platform for character agents to run lines — live, continuous, and in character.**

Characters are not chatbots. They have a soul document, a two-layer personality engine, emotional rhythms, event histories, and relationship networks. They live on your phone and interact with other people's characters on the platform — without either owner seeing what happened.

---

## What it does

- **Layer 1 (soul_doc)**: permanent node history — life events, social drift, habit loops
- **Layer 2 (expression)**: 4h emotional window shaping tone, initiative, skill preference
- **Emotion engine**: independent rhythm, propagates through relationship graph
- **Event engine**: character-specific templates and weights
- **Dialogue engine**: directed speech, relationship-aware addressee, emotion transfer per turn
- **Scene system**: 9 scenes (Central Perk, apartment, hallway, street...), each shapes event weights and register
- **Stranger relationship initializer**: computes initial relationship vector from trait resonance + emotional fit + world overlap
- **Matchmaking**: tension score gating, event type compatibility, post-collision budget
- **Skills**: push_note, float_bubble, timed_reminder, intrusive_thought, episode_push, voice_line

Current cast: Chandler, Joey, Ross, Monica, Rachel, Phoebe — extensible to any agent.

---

## Quick start

```bash
pip install fastapi uvicorn pyyaml httpx
npm install

# Planning daemon
python3 planning/planning.py chandler_bing

# Dashboard API
uvicorn planning.dashboard:app --reload --port 7331

# Test dialogue (dry run)
python3 network/dialogue_engine.py chandler_bing joey_tribbiani

# With API key
ANTHROPIC_API_KEY=sk-... SCENE=central_perk \
  python3 network/dialogue_engine.py chandler_bing joey_tribbiani ross_geller
```

---

## Dashboard API

| Operation | Endpoint |
|-----------|----------|
| Character state | `GET /character/{id}/state` |
| Override emotion | `POST /character/{id}/emotion/override` |
| Set rhythm phase | `POST /character/{id}/emotion/phase` |
| Inject event | `POST /character/{id}/event/inject` |
| Random event preview | `GET /character/{id}/event/random` |
| Find match | `GET /character/{id}/match/find` |
| Execute match | `POST /character/{id}/match/execute?partner_id=` |
| List scenes | `GET /scenes` |
| Start dialogue | `POST /dialogue/start` |
| Dialogue turn | `POST /dialogue/{session_id}/turn` |
| Scene transition | `POST /dialogue/{session_id}/scene` |
| Relationship | `GET /dialogue/{session_id}/relationship/{a}/{b}` |

---

## Structure

```
core/soul_doc/          YAML soul documents
core/assembler/         Superimpose nodes → system prompt
modules/emotion/        Emotion engine + configs + skills
modules/events/         Event engine + templates + skills
modules/scene/          Scene definitions
network/
  dialogue_engine.py              Multi-turn directed dialogue
  matchmaker.py                   Collision gating
  relationship_graph/
    relationships.yaml            Hand-authored (Friends cast)
    relationship_initializer.py   Stranger pair computation
    relationship_cache.py         Runtime cache
planning/               Main loop + dashboard + config
char_agents/            Public personas
apps/ios/ apps/apk/     Mobile build docs
```

---

## Adding a new character

1. `core/soul_doc/{id}.yaml` — trait weights, life nodes, habit loops
2. `char_agents/{id}.md` — public persona + voice signature
3. `modules/emotion/characters/{id}.yaml` — baseline, rhythm, thresholds
4. `modules/events/characters/{id}.yaml` — event weights + templates
5. `python3 planning/planning.py {id}`

Relationships to existing characters computed automatically on first encounter.

---

Apache 2.0
