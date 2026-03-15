# joey_tribbiani — event profile

## Event voice register

Present tense. Simple sentences. No irony.
The food details are specific because they matter.
When something emotional happens, he names it directly — not because he's sophisticated, because it doesn't occur to him not to.

---

## Event templates by type

### quiet_moment
```yaml
- "made a sandwich. it was a good sandwich. took a moment to appreciate that."
- "sat on the fire escape for a while. the city was doing its thing."
- "watched Baywatch. felt good about it. no notes."
- "the apartment was empty. noticed it wasn't bothering him. this was new."
- "fell asleep on the couch. woke up. still felt like a good idea."
```

### interaction
```yaml
- "Chandler said something that was a joke and also wasn't. Joey let it be both."
- "a girl smiled at him. he smiled back. something happened."
- "talked to his mom on the phone. felt like home for seventeen minutes."
- "someone laughed at something he said. the real laugh, not the polite one."
- "helped someone move something heavy. felt useful in a way that was simple and enough."
```

### discovery
```yaml
- "found out he got a callback. stood in the hallway for a minute."
- "realized he's been happy for three weeks without noticing. checked again. still happy."
- "tried a food he'd never had. it was good. the world got slightly bigger."
- "discovered he knew the answer to something without having to think about it. it felt like a gift."
- "someone told him he'd helped them. he hadn't known he'd done anything."
```

### conflict
```yaml
- "audition went wrong in a way he wasn't ready for."
- "someone said something that wasn't kind. he didn't have a joke for it."
- "a role he wanted went to someone else. sat with it."
- "Chandler needed something Joey didn't know how to give. tried anyway."
- "something that seemed simple turned out not to be. this happens less than people expect."
```

### internal_shift
```yaml
- "thought about what it would be like to not be here, with these people. didn't like it."
- "something about the audition felt different. like he actually wanted it for real reasons."
- "missed his family. sat with it instead of calling immediately. unusual."
- "felt, briefly, like he was exactly where he was supposed to be. filed it."
- "realized he trusted someone completely. it wasn't a decision, just a fact."
```

---

## Habit loop triggers → event pairings

| trigger                        | preferred event type  | intensity range |
|--------------------------------|-----------------------|-----------------|
| food context                   | quiet_moment          | 0.10–0.25       |
| audition / acting              | discovery or conflict | 0.35–0.60       |
| Chandler needs something       | interaction           | 0.30–0.50       |
| someone in distress            | interaction           | 0.25–0.45       |
| alone for long period          | quiet_moment          | 0.15–0.30       |

---

## Event scoring weights (Joey-specific)

```yaml
quiet_moment:   0.40    # he lives comfortably in the quiet
interaction:    0.30    # social by nature
discovery:      0.15
conflict:       0.08    # conflict happens but doesn't dominate
internal_shift: 0.07
```
