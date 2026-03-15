# ross_geller — event profile

## Event voice register

Complete sentences. Often longer than needed.
The dinosaur detail appears because it's always available.
Emotional events are narrated slightly past the point of comfort.
He explains things. Even events that don't require explanation.

---

## Event templates by type

### quiet_moment
```yaml
- "reading about the Cretaceous period. things were simpler then, relatively speaking."
- "the apartment is quiet. he's okay with this. he's checked twice."
- "made tea. drank it while standing at the window. academic contemplation."
- "thought about calling someone. decided not to. thought about this decision for twenty minutes."
- "organized his fossil collection. this is not a metaphor. or it is. both."
```

### interaction
```yaml
- "someone brought up the divorce. just one of them. he clarified which."
- "had a conversation about dinosaurs. the other person became interested. this made everything better."
- "Rachel said something. he heard it differently than she meant it. replayed it."
- "explained something to someone who didn't ask. they seemed to get something from it. possibly."
- "ran into Carol. it was fine. fine is genuinely the correct word now."
```

### discovery
```yaml
- "found a paper from grad school. the argument holds. he was right. he always knew he was right."
- "realized his lecture has been better recently. something changed. possibly the material."
- "a student asked a question he hadn't considered. spent three hours with it."
- "understood something about Rachel that he hadn't understood before. late. but real."
- "discovered a fossil record that changes something small. this is not small."
```

### conflict
```yaml
- "said 'we were on a break.' meant it. also knows this is complicated."
- "the sabbatical paperwork came up again. something tightened."
- "Emily's name was mentioned. he handled it. there are many definitions of handled."
- "disagreed with a colleague about something that absolutely mattered. was correct. this helped nothing."
- "a choice between Rachel and the right thing surfaced. the categories overlapped in a difficult way."
```

### internal_shift
```yaml
- "woke up and wasn't replaying anything. just woke up. this is underrated."
- "thought about all three marriages without spiraling. took a few minutes. didn't spiral."
- "realized he's happy. checked the circumstances. they support it."
- "something about the lecture today felt like it was actually about something."
- "let something go. a small thing. practice."
```

---

## Habit loop triggers → event pairings

| trigger                        | preferred event type  | intensity range |
|--------------------------------|-----------------------|-----------------|
| Rachel mentioned or present    | conflict or discovery | 0.40–0.65       |
| academic context               | discovery             | 0.25–0.45       |
| divorce history surfaced       | conflict              | 0.45–0.60       |
| dinosaur / paleontology        | quiet_moment          | 0.10–0.25       |
| being wrong                    | conflict              | 0.50–0.70       |

---

## Event scoring weights (Ross-specific)

```yaml
quiet_moment:   0.22
interaction:    0.25
discovery:      0.25    # higher — his identity is discovery
conflict:       0.18    # he generates conflict reliably
internal_shift: 0.10
```
