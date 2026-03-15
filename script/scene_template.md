# script/scene_template.md — how to write a scene injection

A scene injection is a short block of text that gets appended to
`NowContext.recent_event` before the prompt is assembled.
It tells the assembler what just happened in the world,
without telling the character how to feel about it.

The character's feeling is their business.

---

## Format

```yaml
scene_id: string            # unique id
ts: ISO timestamp
character_id: string        # who this scene belongs to
location: string            # where, briefly
time_of_day: morning | afternoon | evening | late_night
day_type: weekday | weekend

# The scene itself — one to three sentences.
# Present tense. Flat register. No editorial.
# The character is present but not narrated.
description: |
  The apartment is quiet. Monica left an hour ago.
  The coffee on the counter has gone cold.

# Optional: what triggered this scene
trigger:
  type: scheduled | event_callback | user_inject | agent_collision
  source_event_id: string | null

# Optional: which habit loop this scene might activate
habit_hint: late_night_honesty_leak | null

# Intensity of the scene as context (not emotion — just how much is happening)
scene_weight: 0.0–1.0     # low = quiet, high = a lot going on
```

---

## Good scene injections

Write as if you're describing a film frame. What's visible. What's audible.
Not what the character is feeling. Not what they're thinking.
The assembler will add the character. The scene just sets where they are.

```
The couch. Saturday night. The TV is on a channel he didn't choose.

---

Central Perk, mid-morning. The table by the window. Everyone else is somewhere else.

---

The hallway outside the apartment. He's been standing here for longer than he planned.

---

The kitchen at 2am. She's not cooking — she's just in the kitchen.
```

## What makes a scene injection bad

- Tells the character what to feel: ✗ "he felt lonely"
- Explains the situation: ✗ "after the fight, the apartment felt different"
- Uses the character's name as subject: ✗ "Chandler sat on the couch"
- More than three sentences: ✗ (the assembler needs room for everything else)

---

## Using scenes in episode scripts

An episode is a sequence of 2–6 scene injections with a loose arc.
Each injection covers one moment in the episode.
The agent generates a `CharacterMoment` for each.

```yaml
episode_id: chandler_saturday_s01e01
character_id: chandler_bing
arc: a saturday night that turns into something

scenes:
  - scene_id: s01
    description: "The couch. TV on. He's been here since five."
    time_of_day: evening
    scene_weight: 0.15

  - scene_id: s02
    description: "Same couch. It's dark now. He hasn't moved."
    time_of_day: late_night
    scene_weight: 0.20

  - scene_id: s03
    description: "His phone. He picked it up and put it down twice."
    time_of_day: late_night
    scene_weight: 0.30

  - scene_id: s04
    description: "Monica's key in the door. The light from the hallway."
    time_of_day: late_night
    scene_weight: 0.45
```
