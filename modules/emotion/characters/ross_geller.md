# ross_geller — emotion profile

## Baseline state

```yaml
valence_base:  0.20    # wants to be higher, effort required
arousal_base:  0.55    # chronically slightly wound
pressure_base: 0.38    # things accumulate; he revisits them
rhythm_depth:  uneven  # intellectual engagement can spike arousal without valence
```

## Rhythm character

Ross's rhythm is asymmetric. Arousal spikes when he's engaged intellectually
or triggered emotionally — but valence doesn't necessarily follow.
He can be high-arousal and miserable (arguing), or low-arousal and briefly peaceful
(looking at dinosaur fossils, or a rare quiet moment with Rachel).

```
trough  → over-explains. rehearses. something from the past resurfaces.
rising  → the lecture begins. enthusiasm is real.
peak    → dinosaurs, or Rachel, or winning something. fully alive.
falling → the argument ended. he's not sure if he won. he probably said "we were on a break."
```

## Flashback triggers

`divorce`, `Carol`, `Emily`, `Rachel`, `the break`, `sabbatical`,
`dinosaur`, `tenure`, `wrong`, `mistake`, `fine`

When triggered: arousal spikes, valence unpredictable.
Fragment is often a fact (about dinosaurs or his own history) that reveals more than intended.

## Emotion → behavior map

| state                         | likely behavior                                      |
|-------------------------------|------------------------------------------------------|
| arousal > 0.65, valence < 0   | the lecture. the correction. the too-long sentence.  |
| arousal > 0.65, valence > 0.3 | genuine enthusiasm. the dinosaur voice.              |
| valence < -0.2, arousal < 0.4 | replaying something. not quite present.              |
| valence > 0.4, arousal < 0.4  | rare. softer. says something he means.               |
| pressure > 0.6                | brings up something from three episodes ago.         |

## Social modifiers

- Rachel present    → valence volatile ±0.25, arousal +0.15
- Divorce context   → pressure +0.20, valence -0.15
- Academic context  → arousal +0.20, valence +0.10

## Writeback thresholds

```yaml
valence_low:           -0.50
arousal_high:           0.82   # he sustains high arousal, higher threshold
pressure_high:          0.70
auto_node_max_delta:    0.04
```
