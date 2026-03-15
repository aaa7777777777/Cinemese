# EMOTION.md — emotion subsystem spec

## What emotion is here

Emotion is not mood. It is not a label.
It is a state vector that drifts continuously,
has its own small rhythm (independent of events),
and feeds back into the Layer 1 soul doc when it crosses thresholds.

---

## EmotionState schema

```yaml
valence: float        # -1.0 → 1.0  (negative ↔ positive)
arousal: float        # 0.0 → 1.0   (low ↔ high energy)
dominant_color: str   # qualitative texture, in the character's register
drift_pressure: float # 0.0 → 1.0  how hard the current window is pulling
rhythm_phase: str     # "rising" | "peak" | "falling" | "trough"
micro_score: float    # 0.0 → 100.0  current emotion intensity score
                      # used by matchmaker for collision threshold
```

---

## Rhythm — the small independent loop

Emotion has a natural oscillation that runs regardless of events.
Default period: 4 hours. User can adjust in planning_config.yaml.

```
trough → rising (1h) → peak (30min) → falling (1.5h) → trough (1h) → ...
```

At each phase transition, planning.py fires a soft emotion update
that nudges valence/arousal by a small amount (±0.05–0.15)
based on trait_weights in the soul doc.

Characters with high `deflection_via_humor` have
a shallower rhythm — their peaks are flatter.
Characters with high `genuine_vulnerability` have
a deeper trough — it actually lands.

---

## Event → emotion callback

When event_engine.py fires an event, it calls:
```python
emotion_engine.receive_event(event: Event) -> EmotionDelta
```

The delta is applied immediately to the current state.
Large events (intensity > 0.7) can interrupt the rhythm phase.

---

## Emotion → soul doc writeback

When emotion crosses a threshold sustained for > N minutes,
emotion_engine writes a small life node into soul_doc:

```yaml
id: auto_{timestamp}
ts: {now}
event: "sustained {dominant_color} for {duration}"
delta:
  {closest_trait}: ±{small_value}   # ≤ 0.05 per auto-write
locked: false
note: "written by emotion module — rhythm event"
```

Threshold defaults (user-adjustable in planning_config.yaml):
- valence < -0.6 sustained 20min → writes to soul doc
- arousal > 0.8 sustained 10min → writes to soul doc
- drift_pressure > 0.75 sustained 15min → writes to soul doc

---

## micro_score — for matchmaker

```
micro_score = (|valence| * 40) + (arousal * 35) + (drift_pressure * 25)
```

Range: 0–100. Used by network/matchmaker.py to gate agent collisions.
Two agents can only interact if:
```
|agent_A.micro_score - agent_B.micro_score| ≤ COLLISION_THRESHOLD
```
Default threshold: 30. User sets in planning_config.yaml.

---

## Skills output

- `mood_bubble.ts`  — persistent floating widget, color = dominant_color
- `drift_alert.ts`  — push notification when drift_pressure crosses 0.6
