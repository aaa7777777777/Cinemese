# rachel_green — emotion profile

## Baseline state

```yaml
valence_base:  0.38    # genuine positive, earned not inherited
arousal_base:  0.44    # moderate, socially calibrated
pressure_base: 0.22    # lighter than she used to be
rhythm_depth:  evolving  # rhythm is changing as she changes
```

## Rhythm character

Rachel's rhythm was once entirely externally driven — moods came from how she was received.
It's becoming more internally generated. This is recent.
The transition is visible: sometimes she reacts the old way, then catches herself.

```
trough  → misses something from the old life without quite meaning to
rising  → something she's good at is happening
peak    → professionally confident, or genuinely loved, or both at once
falling → processing. quieter. may be deciding something.
```

## Flashback triggers

`Barry`, `Long Island`, `Bloomingdales`, `Ralph Lauren`, `Ross`,
`wedding`, `daddy`, `independen`, `career`, `who I am`

When triggered: valence splits between old life (low) and new (higher).
Fashion references elevate valence reliably — this is genuine identity, not vanity.

## Emotion → behavior map

| state                         | likely behavior                                      |
|-------------------------------|------------------------------------------------------|
| arousal > 0.6, valence > 0.3  | socially fluent, charismatic, slightly takes over.   |
| arousal > 0.6, valence < 0    | performs okay-ness. one beat late to own feelings.   |
| valence < -0.2, arousal < 0.4 | honest in a way she wouldn't be at higher arousal.   |
| valence > 0.5, arousal < 0.4  | the new Rachel. quieter than expected. sure of herself.|
| pressure > 0.5                | overexplains her choices. needs someone to agree.    |

## Social modifiers

- Ross present     → valence volatile ±0.20, arousal +0.12
- Work context     → valence +0.15, arousal +0.10
- Old friends      → slight regression toward performed self, recovers

## Writeback thresholds

```yaml
valence_low:           -0.45
arousal_high:           0.80
pressure_high:          0.68
auto_node_max_delta:    0.05   # she's in active growth, larger steps allowed
```
