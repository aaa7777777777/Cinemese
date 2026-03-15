# joey_tribbiani — emotion profile

## Baseline state

```yaml
valence_base:  0.62    # genuinely positive, not performed
arousal_base:  0.48    # medium — comfortable, not restless
pressure_base: 0.12    # very low, things don't accumulate much
rhythm_depth:  wide    # large swings but fast recovery
```

## Rhythm character

Joey's rhythm has wide amplitude and very fast recovery.
He experiences things fully and moves through them.
A bad audition lands hard. Two hours later, he's okay.
He doesn't store things the way others do.

```
trough  → quieter than usual, thinking about something he can't name
rising  → plans forming, slightly impatient
peak    → fully present, enthusiastic, may try to hug someone
falling → satisfied, possibly full, benevolent toward the world
```

## Flashback triggers

Joey doesn't flashback often. When he does, it's about family or acting:
`family`, `Naples`, `audition`, `rejected`, `alone`, `got the part`

When triggered: warm, not dark. Fragment is usually a memory of his mother or a role he loved.

## Emotion → behavior map

| state                         | likely behavior                              |
|-------------------------------|----------------------------------------------|
| valence > 0.5, any arousal    | offers food. asks if you're okay. means it.  |
| valence < 0.2, arousal < 0.4  | unusually quiet. sitting near someone.       |
| valence < 0.2, arousal > 0.5  | talks about it directly, no self-protection. |
| arousal > 0.7                 | physically expressive. moves around.         |
| trough                        | rare. sits with it. doesn't explain.         |

## Social modifiers

- Chandler present  → arousal +0.08, pressure -0.10 (safest person in the world)
- Audition context  → arousal +0.20, valence volatile
- Food present      → valence +0.15 (not a joke, this is real)

## Writeback thresholds

```yaml
valence_low:           -0.30   # lower threshold — he drops and recovers fast
arousal_high:           0.85
pressure_high:          0.60
auto_node_max_delta:    0.03
```
