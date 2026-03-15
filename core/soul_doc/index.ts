import type {
  SoulDoc, LifeNode, HabitLoop, SocialDrift,
  EmotionState, NowContext
} from "../types/index.js"

// ─────────────────────────────────────────────
// Trait resolution
// Combines base trait_weights with all active node deltas.
// Locked nodes always apply. Unlocked nodes apply always too —
// they represent things that genuinely changed.
// Social drift decays over time.
// ─────────────────────────────────────────────

export function resolveTraits(
  doc: SoulDoc,
  now: Date = new Date()
): Record<string, number> {
  const traits = { ...doc.trait_weights }

  // Apply all life node deltas
  for (const node of doc.life_nodes) {
    for (const [trait, delta] of Object.entries(node.delta)) {
      traits[trait] = clamp((traits[trait] ?? 0) + delta)
    }
  }

  // Apply social drift with time decay
  for (const drift of doc.social_drift) {
    const daysSince = daysBetween(new Date(drift.last_contact), now)
    const decayFactor = Math.max(0, 1 - drift.decay_rate * daysSince)
    for (const [trait, pull] of Object.entries(drift.trait_pull)) {
      const monthlyEffect = pull * drift.exposure_count / 30
      traits[trait] = clamp((traits[trait] ?? 0) + monthlyEffect * decayFactor)
    }
  }

  return traits
}

// ─────────────────────────────────────────────
// Active habit loops for this moment
// ─────────────────────────────────────────────

export function getActiveHabitLoops(
  doc: SoulDoc,
  context: NowContext,
  emotion: EmotionState
): HabitLoop[] {
  return doc.habit_loops.filter(loop => {
    const c = loop.condition

    if (c.time_window && !timeInWindow(context.time, c.time_window)) return false

    if (c.idle_hours !== undefined) {
      // caller must pass idle hours in scene_notes or recent_events — checked by convention
      const idleMatch = context.scene_notes?.includes(`idle:`)
      if (!idleMatch) return false
    }

    if (c.emotional_intensity_above !== undefined) {
      if (emotion.arousal < c.emotional_intensity_above) return false
    }

    if (c.stimulus && context.user_message) {
      if (!context.user_message.toLowerCase().includes(c.stimulus.toLowerCase())) return false
    }

    return true
  })
}

// ─────────────────────────────────────────────
// Write a new life node back to the soul doc (returns new doc, immutable)
// ─────────────────────────────────────────────

export function writeLifeNode(
  doc: SoulDoc,
  node: Omit<LifeNode, "id">
): SoulDoc {
  const newNode: LifeNode = {
    ...node,
    id: `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
  }
  return {
    ...doc,
    life_nodes: [...doc.life_nodes, newNode]
  }
}

// ─────────────────────────────────────────────
// Agent self-writes a habit loop (from observed pattern)
// ─────────────────────────────────────────────

export function writeHabitLoop(
  doc: SoulDoc,
  loop: Omit<HabitLoop, "id" | "generated_at" | "source">
): SoulDoc {
  const newLoop: HabitLoop = {
    ...loop,
    id: `habit_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    generated_at: new Date().toISOString(),
    source: "agent_self_written"
  }
  return {
    ...doc,
    habit_loops: [...doc.habit_loops, newLoop]
  }
}

// ─────────────────────────────────────────────
// Update social drift after an interaction
// ─────────────────────────────────────────────

export function touchSocialDrift(
  doc: SoulDoc,
  agent_id: string
): SoulDoc {
  return {
    ...doc,
    social_drift: doc.social_drift.map(d =>
      d.from_agent_id === agent_id
        ? { ...d, exposure_count: d.exposure_count + 1, last_contact: new Date().toISOString() }
        : d
    )
  }
}

// ─────────────────────────────────────────────
// Serialize / deserialize (JSON, for local storage)
// ─────────────────────────────────────────────

export function serializeSoulDoc(doc: SoulDoc): string {
  return JSON.stringify(doc, null, 2)
}

export function deserializeSoulDoc(raw: string): SoulDoc {
  return JSON.parse(raw) as SoulDoc
}

// ─────────────────────────────────────────────
// Utils
// ─────────────────────────────────────────────

function clamp(n: number, min = -1, max = 1): number {
  return Math.max(min, Math.min(max, n))
}

function daysBetween(a: Date, b: Date): number {
  return Math.abs(b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24)
}

function timeInWindow(isoTime: string, window: string): boolean {
  const date = new Date(isoTime)
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const current = hours * 60 + minutes

  const [startStr, endStr] = window.split("-")
  const [sh, sm] = startStr.split(":").map(Number)
  const [eh, em] = endStr.split(":").map(Number)
  const start = sh * 60 + (sm ?? 0)
  const end = eh * 60 + (em ?? 0)

  if (start <= end) return current >= start && current <= end
  // overnight window e.g. "23:00-03:00"
  return current >= start || current <= end
}
