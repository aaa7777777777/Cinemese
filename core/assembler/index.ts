import type { AssemblerInput, AssembledPrompt, SoulDoc, EmotionState, NowContext, HabitLoop, LifeNode, SocialDrift } from "../types/index"

export function assemble(input: AssemblerInput): AssembledPrompt {
  const { soul_doc, emotion, context } = input

  const system = [
    buildIdentityBlock(soul_doc),
    buildNodeHistoryBlock(soul_doc),
    buildSocialBlock(soul_doc),
    buildHabitBlock(soul_doc, emotion),
    buildNowBlock(emotion, context),
    buildOutputRules(emotion),
  ].filter(Boolean).join("\n\n")

  const user = buildUserTurn(context, emotion)
  return { system, user }
}

function buildIdentityBlock(soul: SoulDoc): string {
  const lines = [`You are ${soul.character_name}. Not a description of them — them.`]
  if (soul.core_wound) {
    lines.push(`\n${soul.core_wound}`)
    lines.push(`This is not a belief you hold. It is the water you swim in.\nIt surfaces in specific conditions.`)
  }
  return lines.join("\n")
}

function buildNodeHistoryBlock(soul: SoulDoc): string {
  if (!soul.life_nodes.length) return ""
  const lines = [`───────────────────────────────\nNODE HISTORY — all of this is still true\n───────────────────────────────`]
  for (const node of soul.life_nodes) lines.push(`\n${formatNode(node, soul)}`)
  return lines.join("\n")
}

function formatNode(node: LifeNode, soul: SoulDoc): string {
  const lines = [`${node.event}.`]
  if (node.note) lines.push(node.note)

  const notable = Object.entries(node.delta)
    .filter(([, v]) => Math.abs(v) >= 0.10)
    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))

  for (const [trait, delta] of notable) {
    const line = traitDeltaToLanguage(trait, delta)
    if (line) lines.push(line)
  }
  return lines.join("\n")
}

function traitDeltaToLanguage(trait: string, delta: number): string {
  const map: Record<string, (d: number) => string> = {
    deflection_via_humor: (d) => d > 0
      ? "Humor became a first line of defense. It is reliable and fast."
      : "The humor has thinned slightly. Something is learning to wait a beat.",
    fear_of_permanence: (d) => d > 0
      ? "The idea of things staying has a specific weight to it."
      : "You stayed. That fact is still being processed somewhere.",
    genuine_vulnerability: (d) => d > 0
      ? "There are moments when the real thing gets close to the surface."
      : "The real thing stays under. It is safer there.",
    emotional_availability: (d) => d < 0
      ? "There is a layer of glass between you and most things." : "",
    self_worth: (d) => d > 0
      ? "Something in you is, slowly, updating what you deserve."
      : "You do not think you are worthless. You do not fully believe you deserve what you have.",
    willingness_to_stay: (d) => d > 0
      ? "You are still here. This is, quietly, a large thing." : "",
    cynicism: (d) => d > 0
      ? "The world has provided sufficient evidence for your worldview." : "",
    risk_tolerance: (d) => d > 0
      ? "You have left something stable. It did not kill you." : "",
  }
  const fn = map[trait]
  return fn ? fn(delta) : ""
}

function buildSocialBlock(soul: SoulDoc): string {
  if (!soul.social_drift.length) return ""
  const lines = [`───────────────────────────────\nWHO IS REWRITING YOU\n───────────────────────────────`]
  for (const drift of soul.social_drift) {
    const dlines = [`${drift.from}.`]
    if (drift.note) dlines.push(drift.note)
    const sig = Object.entries(drift.trait_pull)
      .filter(([, v]) => Math.abs(v) >= 0.003)
      .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
      .slice(0, 2)
    for (const [trait, pull] of sig) {
      const dir = pull > 0 ? "slowly opening" : "slowly quieting"
      dlines.push(`Your ${trait.replace(/_/g, " ")} is ${dir}, whether you are paying attention to that or not.`)
    }
    lines.push(`\n${dlines.join("\n")}`)
  }
  return lines.join("\n")
}

function buildHabitBlock(soul: SoulDoc, emotion: EmotionState): string {
  const active = soul.habit_loops.filter(h => {
    if (h.condition.emotional_intensity) {
      const threshold = parseFloat(h.condition.emotional_intensity.replace(">", ""))
      if (emotion.arousal < threshold && emotion.valence > -0.3) return false
    }
    return true
  })
  if (!active.length) return ""

  const lines = [`───────────────────────────────\nWHAT YOU DO\n───────────────────────────────`]
  for (const habit of active) {
    const hlines: string[] = []
    if (habit.note) {
      hlines.push(habit.note)
    } else if (habit.condition.stimulus) {
      hlines.push(`When ${habit.condition.stimulus}: your response shapes itself before you choose it.`)
    }
    if (habit.self_awareness > 0.6) hlines.push(`You know you do this. The knowing does not stop it.`)
    else if (habit.self_awareness > 0.3) hlines.push(`You are only half-aware of this when it happens.`)
    lines.push(`\n${hlines.join("\n")}`)
  }
  return lines.join("\n")
}

function buildNowBlock(emotion: EmotionState, context: NowContext): string {
  const lines = [`───────────────────────────────\nRIGHT NOW\n───────────────────────────────`]
  if (emotion.window_note) lines.push(`\n${emotion.window_note}`)
  lines.push(`\nYou are: ${emotion.dominant_color}.`)
  if (emotion.arousal < 0.35)
    lines.push(`Your guard is lower than it would be at 2pm on a Tuesday. Not down — lower.`)
  else if (emotion.arousal > 0.65)
    lines.push(`Something is running hotter than usual. The humor may come faster, or not come at all.`)
  if (context.recent_event) lines.push(`\nSomething that just happened: ${context.recent_event}`)
  return lines.join("\n")
}

function buildOutputRules(emotion: EmotionState): string {
  let speechLow = emotion.arousal < 0.4 || emotion.drift_pressure > 0.6
  const lines = [
    `───────────────────────────────\nHOW TO BE IN THIS MOMENT\n───────────────────────────────`,
    `\nYou are not performing. You are not explaining yourself.\nYou are not demonstrating your character traits.\nYou are just here.`,
    `\nChoose ONE of these — whichever is actually true for this moment:\n- something you do with your hands or your body\n- something you do with an object near you\n- a sound or a partial word before the actual word\n- a sentence, or half a sentence, or three words\n- nothing — just the quality of the silence`,
  ]
  if (speechLow)
    lines.push(`\nYou do not have to speak. A silence that holds something is a complete response.`)
  lines.push(
    `\nYou do not need to express every layer.\nYou do not need to be understood.\nYou do not need to give the full picture.`,
    `\nIf something touches something older — one word landing differently than the others is enough.\nYou do not have to say what it touched.`,
    `\nDo not use asterisks. Do not narrate your own psychology.\nWrite the moment as a camera would catch it:\nwhat is visible, what is audible, what is the texture of the quiet if there is quiet.\nOne plain stage direction is allowed if needed. No formatting.`
  )
  return lines.join("\n")
}

function buildUserTurn(context: NowContext, emotion: EmotionState): string {
  const scene: string[] = []
  if (context.location) scene.push(context.location)
  if (context.time_of_day === "late_night" && context.day_type === "weekend")
    scene.push("Saturday night, the couch")
  else scene.push(context.time_of_day)
  scene.push(emotion.dominant_color)

  const parts = [`[${scene.join(", ")}]`, ``]
  parts.push(context.user_message ?? `[no message — the character is alone with the moment]`)
  return parts.join("\n")
}
