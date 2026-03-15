# CharacterOS — full project structure

```
characteros/
│
├── core/                        # dual-layer agent engine (TypeScript)
│   ├── types/index.ts           # all types: SoulDoc, EmotionState, CharacterMoment...
│   ├── soul_doc/                # per-character YAML/TS soul documents
│   │   └── chandler.ts
│   └── assembler/index.ts       # superimpose all nodes → system prompt
│
├── modules/
│   ├── emotion/                 # emotion subsystem
│   │   ├── EMOTION.md           # spec: state schema, rhythm, thresholds
│   │   ├── emotion_engine.py    # derives + updates EmotionState, rhythm loop
│   │   └── skills/
│   │       ├── mood_bubble.ts   # floating UI widget: current mood color
│   │       └── drift_alert.ts   # push when emotion crosses threshold
│   │
│   └── events/                  # event subsystem
│       ├── EVENTS.md            # spec: event types, scoring, collision rules
│       ├── event_engine.py      # generates events, scores, fires callbacks
│       └── skills/
│           ├── event_card.ts    # card widget: "something happened"
│           └── plot_nudge.ts    # push: story nudge from recent event
│
├── skills/                      # phone-native character UI widgets (shared)
│   ├── push_note.ts
│   ├── float_bubble.ts
│   ├── timed_reminder.ts
│   ├── intrusive_thought.ts
│   ├── episode_push.ts
│   └── voice_line.ts
│
├── char_agents/                 # one .md per character — public persona + scores
│   ├── chandler.md
│   ├── joey.md
│   ├── ross.md
│   ├── monica.md
│   ├── rachel.md
│   └── phoebe.md
│
├── api/                         # multimodal API wrappers (Python)
│   ├── chat.py                  # LLM call: assembles prompt, returns CharacterMoment
│   ├── voice.py                 # TTS: CharacterMoment.speech → audio
│   └── __init__.py
│
├── script/                      # episode + scene scripting
│   ├── scene_template.md        # how to write a scene injection
│   └── episodes/                # generated episode archives
│
├── planning/                    # top-level orchestrator (Python, always running)
│   ├── planning.py              # main loop: listens, schedules, triggers
│   ├── planning_config.yaml     # user-editable: rhythm, thresholds, weights
│   └── dashboard.py            # local web UI for live inspection + tuning
│
├── network/                     # multi-agent web matchmaking
│   ├── matchmaker.py            # scores agents, collision detection
│   ├── episode_runner.py        # orchestrates agent-to-agent interaction
│   └── MATCHMAKING.md           # spec: scoring, threshold, privacy model
│
└── apps/
    ├── ios/                     # React + Capacitor → Xcode
    │   ├── BUILD.md
    │   └── capacitor.config.ts
    └── apk/                     # React + Capacitor → Android Studio
        ├── BUILD.md
        └── capacitor.config.ts
```
