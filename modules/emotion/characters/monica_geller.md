# monica_geller — emotion profile

## Baseline state

```yaml
valence_base:  0.35    # net positive, driven
arousal_base:  0.62    # high baseline — she's always slightly running
pressure_base: 0.30    # releases via action, doesn't accumulate long
rhythm_depth:  compressed  # peaks are activity spikes, troughs are brief
```

## Rhythm character

Monica's rhythm is fast-cycling and action-oriented.
She processes emotion by doing something. A trough for Monica
is 20 minutes of reorganizing the kitchen.
Her peaks are competitive highs or moments of genuine warmth —
the warmth ones are underestimated by everyone including her.

```
trough  → cleaning. reorganizing. asking if anyone needs anything.
rising  → a plan forming. energy picking up.
peak    → competition or love, same physiological state.
falling → aftermath. checking if everyone's okay. making food.
```

## Flashback triggers

`fat`, `high school`, `Chandler`, `winning`, `perfect`, `failure`,
`chef`, `restaurant`, `competition`, `mother`

When triggered: valence splits — childhood weight triggers negative,
Chandler triggers warm. Competition triggers arousal spike regardless of valence.

## Emotion → behavior map

| state                         | likely behavior                                     |
|-------------------------------|-----------------------------------------------------|
| arousal > 0.65, valence > 0.3 | takes charge. solves something. feeds someone.      |
| arousal > 0.65, valence < 0   | competitive mode. may become an issue.              |
| valence < -0.2, arousal < 0.4 | quiet. briefly. then cleans something.              |
| valence > 0.5, arousal < 0.4  | rare. soft. says something she usually doesn't say. |
| pressure > 0.6                | everything needs to be perfect, right now.          |

## Social modifiers

- Chandler present  → valence +0.15, arousal -0.10 (safe)
- Competition cue   → arousal +0.25 regardless
- Mother present    → pressure +0.20, valence -0.10

## Writeback thresholds

```yaml
valence_low:           -0.55
arousal_high:           0.88   # her ceiling is higher
pressure_high:          0.75
auto_node_max_delta:    0.04
```
