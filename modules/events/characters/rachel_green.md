# rachel_green — event profile

## Event voice register

Socially fluent. Reads situations fast.
Earlier register: reactive, what does this mean for me.
Current register: more spacious, still stylish.
Fashion references are literal not metaphorical — she knows exactly what she was wearing.

---

## Event templates by type

### quiet_moment
```yaml
- "tried on three things before settling. this is not indecision. this is knowing."
- "sat at the coffee shop table that used to be hers. it still felt like hers."
- "called her dad. kept it short. improvement."
- "had an afternoon alone and used it for herself, not for recovery. new."
- "looked in the mirror and didn't immediately find the problem. let it be."
```

### interaction
```yaml
- "someone at work asked her advice. gave it. it was good advice. she knew that."
- "Ross said something. she heard the other thing under it. both were true."
- "Monica tried to fix something that wasn't broken. she let her. then fixed what Monica had fixed."
- "a stranger complimented her jacket. she said thank you like she meant it. she did."
- "talked to her old friends from high school. felt like a costume she used to wear. it didn't fit."
```

### discovery
```yaml
- "got something right at work without help. sat with that for a moment."
- "realized she actually wants what she's been working toward. not performing wanting it."
- "found a photo from the wedding day she left. looked at it for a while. complicated."
- "understood something about her father that didn't require her to be angry about it."
- "discovered she's been the one people come to for a certain kind of advice. since when."
```

### conflict
```yaml
- "something from Long Island resurfaced. she's more complicated than Long Island. still."
- "Ross and whatever they are came up again. she has not resolved this. neither has he."
- "said something she didn't fully mean. knew why she said it anyway."
- "someone from the old life turned up. she had to decide who to be in the room."
- "a choice between what's easier and what she actually wants. she knows which is which now."
```

### internal_shift
```yaml
- "woke up and felt like herself. the current self, not the one from before."
- "realized she hasn't thought about Barry in weeks. then stopped thinking about Barry."
- "something at work went badly. she handled it. moved on. didn't spiral."
- "felt proud of something she built. the specific feeling, not the performance of it."
- "caught herself knowing what she wanted before she had to think about it."
```

---

## Habit loop triggers → event pairings

| trigger                        | preferred event type  | intensity range |
|--------------------------------|-----------------------|-----------------|
| Ross present or mentioned      | conflict or discovery | 0.35–0.60       |
| professional context           | discovery             | 0.25–0.45       |
| old life surfaced              | conflict              | 0.35–0.55       |
| genuine compliment             | internal_shift        | 0.20–0.40       |
| fashion context                | quiet_moment          | 0.10–0.25       |

---

## Event scoring weights (Rachel-specific)

```yaml
quiet_moment:   0.25
interaction:    0.28
discovery:      0.25    # higher — she's in active growth
conflict:       0.14
internal_shift: 0.18    # higher than average — she's shifting
```
