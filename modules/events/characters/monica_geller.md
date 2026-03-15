# monica_geller — event profile

## Event voice register

Active verbs. Short sentences when decided, longer when competitive.
Food as vehicle. The event is usually something she did or organized.
When something emotional happens, she responds by making it better — whether or not it can be made better.

---

## Event templates by type

### quiet_moment
```yaml
- "reorganized the spice rack. this was necessary. she has a system."
- "the kitchen is clean. she's in it anyway. this is where she thinks."
- "cooked something complicated for no occasion. it was for the occasion of Tuesday."
- "sat down without a task for eleven minutes. got back up."
- "the apartment is exactly as it should be. she checked."
```

### interaction
```yaml
- "Chandler said something sweet in a way that was embarrassing for him. she let it land."
- "beat Joey at something. the something doesn't matter. the beating matters."
- "her mother said something. she handled it. the kitchen got very clean afterward."
- "someone complimented the food. she accepted it without correcting them. progress."
- "had a real conversation with Rachel that wasn't about any of their usual things."
```

### discovery
```yaml
- "a new technique that makes the sauce better. tested it three times. confirmed."
- "realized she's been the one holding something together. not resentfully. just factually."
- "found a recipe from her grandmother. made it. it was the same. this mattered more than expected."
- "noticed Chandler looking at her like he still can't believe it. filed this."
- "understood something about the fat-kid years she hadn't before. not painful. just clear."
```

### conflict
```yaml
- "something was not done correctly. she fixed it. this created friction. the friction was worth it."
- "lost a competition. replayed every decision. identified the error. would not make it again."
- "something Chandler said was small and also wasn't. they talked about it until it was resolved."
- "her mother compared her to someone else. she responded with cooking. then with words."
- "had to let something be imperfect. this took longer than anyone will know."
```

### internal_shift
```yaml
- "woke up and didn't immediately have a plan. lay there. it was okay."
- "thought about high school without it meaning anything bad about right now."
- "let Chandler fix something. didn't take over. watched him do it slightly wrong. said nothing. this was love."
- "realized the restaurant is actually good. not perfect. actually good. this is different."
- "felt genuinely content. confirmed it wasn't satisfaction-disguised-as-control. it wasn't."
```

---

## Habit loop triggers → event pairings

| trigger                        | preferred event type  | intensity range |
|--------------------------------|-----------------------|-----------------|
| competition present            | interaction or conflict | 0.40–0.70     |
| imperfection detected          | conflict              | 0.35–0.55       |
| Chandler warmth                | internal_shift        | 0.25–0.45       |
| mother context                 | conflict              | 0.45–0.65       |
| cooking context                | quiet_moment          | 0.10–0.30       |

---

## Event scoring weights (Monica-specific)

```yaml
quiet_moment:   0.20
interaction:    0.28
discovery:      0.18
conflict:       0.22    # higher — she generates and resolves conflict
internal_shift: 0.12
```
