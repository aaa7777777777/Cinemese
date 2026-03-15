# WORLDS.md — worldview system spec

## What a world is

A world is the invisible context every character lives inside.
Two characters from the same world understand each other's references,
share the same background noise, breathe the same air.

Two characters from different worlds can meet —
but the gap between their worlds has weight.
If the gap is large enough, one of them loses their track.
They don't die. They just can't go back to where they were.

---

## Three dimensions

```
nation    — the geopolitical and cultural container
era       — when (decade is enough; exact year is optional)
env       — main living environment (shapes daily texture and class register)
```

These three produce a coordinate in world-space.
Distance between two coordinates = worldview_gap.

---

## World distance formula

```python
worldview_gap = (
    nation_distance(A, B)  * 0.40 +
    era_distance(A, B)     * 0.35 +
    env_distance(A, B)     * 0.25
)
# range: 0.0 (identical) → 1.0 (maximally different)
```

---

## Collision rules

### Single meeting

```
gap < 0.30   → smooth interaction, no displacement
gap 0.30–0.55 → friction, one agent's emotion drifts, no track loss
gap 0.55–0.75 → one agent loses event track + emotion resets to zero
              → which one: the one with lower soul_doc.world_resilience
gap > 0.75   → both agents affected; one loses track immediately,
              → the other's track is marked as "unstable"
```

### Second meeting (after first displacement)

If either agent has `track_status: displaced` from a prior meeting:
```
any gap > 0.20 → second displacement risk
gap > 0.40     → both agents lose their tracks
```

A displaced track cannot be restored.
The agent starts accumulating new events from the displacement point.
Their soul_doc retains the old life_nodes (memory) but
their event_engine and emotion_engine restart from baseline zero.

---

## Economic and social context injection

Each world definition includes:
- `economic_register`: wealth distribution, what money means, daily transactions
- `social_register`: class mobility, gender norms, how strangers interact
- `background_noise`: what's in the air (politics, technology, ambient tension)

These are injected into the assembler's system prompt as
"the water you swim in" — not rules the character follows,
but facts that shape how they think without them knowing.

---

## Worldview resilience

A character's `world_resilience` score (0–1) determines
how resistant they are to displacement:

```
world_resilience = (
    soul_doc.trait_weights.get("quiet_resilience", 0.5)   * 0.35 +
    soul_doc.trait_weights.get("self_sufficiency", 0.5)   * 0.30 +
    soul_doc.trait_weights.get("adaptability",     0.4)   * 0.20 +
    soul_doc.trait_weights.get("identity_stability",0.5)  * 0.15
)
```

Lower resilience = more likely to be the displaced agent
when worldview_gap is in the 0.55–0.75 range.
