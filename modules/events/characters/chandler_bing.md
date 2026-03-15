# chandler_bing — event profile

## Event voice register

Dry. Observational. The event is stated, not dramatized.
Even significant events get a slightly flat delivery —
the weight is carried in what's not said.

---

## Event templates by type

### quiet_moment
```yaml
- "it's been quiet for a few hours. the kind of quiet that has a texture."
- "the TV is on. he's not watching it. this is fine."
- "he's been on the couch longer than he planned. the couch doesn't judge."
- "the apartment is very clean. Monica cleaned it. this means something but he's not looking at what."
- "he made coffee. it's gone cold. he noticed but didn't do anything about it."
```

### interaction
```yaml
- "Joey said something honest without meaning to."
- "Monica looked at him for a second longer than usual. she didn't say anything."
- "someone asked him what he actually wanted. he answered something else."
- "he ran into someone from before. it went okay. okay is a lot."
- "he said something and it landed wrong. he replayed it four times."
```

### discovery
```yaml
- "found a photo from a few years ago. took a minute to decide what to do with it."
- "realized he's been telling the same joke for six years. still works. something about this is both good and not good."
- "something that used to be hard was easy today. he didn't trust it."
- "read something that was exactly the thing he'd been thinking. unsettling."
- "found out something about his parents. added to the existing collection."
```

### conflict
```yaml
- "a choice surfaced that he'd been successfully not making."
- "said the wrong thing. knew it while saying it. kept going."
- "something Monica wanted and something he wanted were not the same thing. this required an entire evening."
- "the joke didn't land. the room went quiet. he made another joke."
- "someone needed him to be more than he thought he could be. he showed up anyway. barely."
```

### internal_shift
```yaml
- "woke up and the fear was quieter than usual. didn't trust it."
- "thought about Thanksgiving. didn't spiral. this is new."
- "something that used to feel impossible felt difficult. difficult is progress."
- "missed Monica while she was standing right there. this is the good version of that feeling."
- "caught himself meaning something he said. that's been happening more."
```

---

## Habit loop triggers → event pairings

| trigger                        | preferred event type  | intensity range |
|--------------------------------|-----------------------|-----------------|
| late_night + alone             | quiet_moment          | 0.15–0.30       |
| receives significant compliment| internal_shift        | 0.25–0.45       |
| Monica context                 | internal_shift        | 0.30–0.50       |
| argument or tension            | conflict              | 0.45–0.65       |
| Joey interaction               | interaction           | 0.20–0.40       |

---

## Event scoring weights (Chandler-specific)

```yaml
quiet_moment:   0.38    # higher than default — he lives here
interaction:    0.22
discovery:      0.18
conflict:       0.10    # lower — he avoids direct conflict
internal_shift: 0.12
```
