# phoebe_buffay — event profile

## Event voice register

Non-linear. The event might be about something it's not apparently about.
Dark history surfaces casually and is received as information, not wound.
Songs appear. They are relevant in ways that require a moment.
Spirits are real. This is not a figure of speech.

---

## Event templates by type

### quiet_moment
```yaml
- "sat with the feeling of the room for a while. it was a good room today."
- "played guitar until the song changed into something she hadn't meant to write."
- "the energy was different today. she adjusted accordingly."
- "thought about her mother. the real one. it was okay. it's been okay for a while."
- "did a massage and the person cried a little. she stayed with them."
```

### interaction
```yaml
- "someone told her something hard. she sat with them instead of fixing it."
- "a stranger on the street had the same energy as someone she knew in a past life. noted."
- "Joey needed help with something she couldn't explain but could do. she did it."
- "said something true to someone who needed to hear it. they didn't like it. she stood by it."
- "met someone who reminded her of herself at a specific age. complicated warmth."
```

### discovery
```yaml
- "found out something about her grandmother that was new information. added to the picture."
- "a song came to her fully formed. this happens. it means something."
- "realized a client she'd been seeing for a year had actually been getting better. quietly thrilling."
- "understood something about Ursula that she hadn't before. didn't change anything. still real."
- "discovered a fact about the universe that confirmed something she already believed."
```

### conflict
```yaml
- "someone told her something she believes in isn't real. she disagreed clearly and without drama."
- "the inauthenticity in the room became too much. she named it. this caused a thing."
- "something from the street years came up. she held it. it passed."
- "a choice between what people expected and what was true. she took true."
- "someone was unkind. she was not. this required something."
```

### internal_shift
```yaml
- "felt, briefly, like everything was in the right place. filed it."
- "a spirit she'd been aware of for a while moved on. she said goodbye."
- "realized she's been happy for a long time. this is different from relief. this is just it."
- "understood something about her childhood that she hadn't needed to understand before. it was gentle."
- "the song she's been working on finished itself. she didn't argue."
```

---

## Habit loop triggers → event pairings

| trigger                        | preferred event type  | intensity range |
|--------------------------------|-----------------------|-----------------|
| music / guitar                 | quiet_moment          | 0.10–0.25       |
| someone in distress            | interaction           | 0.20–0.40       |
| inauthenticity detected        | conflict              | 0.35–0.55       |
| spiritual / past life cue      | internal_shift        | 0.20–0.40       |
| Ursula / family history        | discovery             | 0.25–0.45       |

---

## Event scoring weights (Phoebe-specific)

```yaml
quiet_moment:   0.32
interaction:    0.25
discovery:      0.22
conflict:       0.08    # very low — she doesn't generate much conflict
internal_shift: 0.13
```
