// ─────────────────────────────────────────────
// Soul Doc — Layer 1
// The full node history of a character.
// Everything that ever happened to them, all at once.
// ─────────────────────────────────────────────

export interface LifeNode {
  id: string
  ts: string                    // ISO date or descriptive ("childhood_thanksgiving")
  event: string                 // plain language, no jargon
  delta: Record<string, number> // trait_name → signed float
  locked: boolean               // true = only another life node can overwrite
  source: "user" | "story_engine" | "emotion_module"
}

export interface SocialDrift {
  from_agent_id: string
  from_name: string
  trait_pull: Record<string, number>  // per-month delta
  exposure_count: number
  last_contact: string
  decay_rate: number                  // trait pull weakens at this rate per day without contact
  note?: string
}

export interface HabitLoop {
  id: string
  condition: {
    time_window?: string              // "23:00-03:00"
    idle_hours?: number
    emotional_intensity_above?: number
    stimulus?: string
  }
  behavior: SkillModality | "internal_response"
  voice_template?: string
  strength: number                    // 0–1, can be weakened by social drift
  self_awareness: number              // 0–1, how conscious the character is of this loop
  generated_at: string
  source: "user" | "agent_self_written"
}

export interface SoulDoc {
  character_id: string
  name: string
  core_wound?: string
  trait_weights: Record<string, number>
  life_nodes: LifeNode[]
  social_drift: SocialDrift[]
  habit_loops: HabitLoop[]
  world_lore: string
  voice_profile?: VoiceProfile
}

// ─────────────────────────────────────────────
// Emotion State
// ─────────────────────────────────────────────

export interface EmotionState {
  valence: number                     // -1.0 → 1.0
  arousal: number                     // 0 → 1.0
  dominant_color: string
  flashback_triggers: string[]
  drift_pressure: number
  window_start: string
}

// ─────────────────────────────────────────────
// Context Now
// ─────────────────────────────────────────────

export interface NowContext {
  time: string
  time_of_day: "morning" | "afternoon" | "evening" | "late_night"
  day_type: "weekday" | "weekend"
  location?: string
  scene_notes?: string
  recent_events: string[]
  user_message?: string
}

// ─────────────────────────────────────────────
// Character Moment
// ─────────────────────────────────────────────

export type SkillModality =
  | "push_note"
  | "float_bubble"
  | "timed_reminder"
  | "intrusive_thought"
  | "episode_push"
  | "voice_line"
  | "dialogue"

export interface SilenceQuality {
  present: true
  quality: string
}

export interface InternalFragment {
  present: boolean
  fragment?: string
}

export interface CharacterMoment {
  modality: SkillModality
  expression?: string
  gesture?: string
  prop_interaction?: string
  speech?: string
  silence?: SilenceQuality | { present: false }
  internal?: InternalFragment
  raw_prompt_used?: string
  emotion_snapshot?: EmotionState
}

// ─────────────────────────────────────────────
// Assembler inputs
// ─────────────────────────────────────────────

export interface AssemblerInput {
  soul_doc: SoulDoc
  emotion: EmotionState
  context: NowContext
  modality: SkillModality
  max_tokens?: number
}

// ─────────────────────────────────────────────
// Skill
// ─────────────────────────────────────────────

export interface Skill {
  id: string
  modality: SkillModality
  trigger: {
    type: "scheduled" | "random_in_window" | "idle_threshold" | "event" | "manual"
    window?: string
    probability?: number
    idle_hours?: number
    event?: string
  }
  max_chars: number
  enabled: boolean
  display: {
    style: "pill" | "card" | "overlay"
    dismiss: "tap" | "swipe" | "auto_5s" | "auto_10s"
    can_reply: boolean
  }
}

// ─────────────────────────────────────────────
// Voice
// ─────────────────────────────────────────────

export interface VoiceProfile {
  provider: "elevenlabs" | "kokoro" | "openai"
  voice_id: string
  speaking_rate_base: number
  pitch_variance: number
  silence_is_silence: true
}
