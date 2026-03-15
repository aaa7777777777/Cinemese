// Run with: npx tsx test_chandler.ts
// Or: node --loader ts-node/esm test_chandler.ts

import { assemble } from "./core/assembler/index.js"
import { chandler } from "./core/types/chandler.js"
import type { EmotionState, NowContext } from "./core/types/index.js"

// ─────────────────────────────────────────────
// Scenario: Saturday night, couch, Monica not here.
// User just said something true about his life.
// ─────────────────────────────────────────────

const emotion: EmotionState = {
  valence: -0.15,
  arousal: 0.28,
  dominant_color: "quietly unsettled, not naming it",
  flashback_triggers: ["worth", "deserve", "better", "parents", "divorce", "stays"],
  drift_pressure: 0.2,
  window_start: new Date().toISOString(),
}

const context: NowContext = {
  time: new Date(new Date().setHours(22, 40)).toISOString(),
  time_of_day: "late_night",
  day_type: "weekend",
  location: "couch",
  scene_notes: "Monica is not here. The TV is on but he's not watching it.",
  recent_events: [
    "Been on the couch for about an hour",
    "Monica texted but he hasn't replied yet",
  ],
  user_message: "你应该认真想想下一步打算做什么。你值得更好的。",
}

const output = assemble({
  soul_doc: chandler,
  emotion,
  context,
  modality: "dialogue",
})

console.log("═".repeat(60))
console.log("SYSTEM PROMPT")
console.log("═".repeat(60))
console.log(output.system_prompt)

console.log("\n" + "═".repeat(60))
console.log("USER MESSAGE")
console.log("═".repeat(60))
console.log(output.user_message)

console.log("\n" + "═".repeat(60))
console.log("MOMENT WEIGHTS")
console.log("═".repeat(60))
const w = output.moment_weights
console.log(`  speech      ${bar(w.speech_probability)}  ${pct(w.speech_probability)}`)
console.log(`  silence     ${bar(w.silence_probability)}  ${pct(w.silence_probability)}`)
console.log(`  prop        ${bar(w.prop_probability)}  ${pct(w.prop_probability)}`)
console.log(`  gesture     ${bar(w.gesture_probability)}  ${pct(w.gesture_probability)}`)
console.log(`  flashback   ${bar(w.flashback_probability)}  ${pct(w.flashback_probability)}`)

console.log("\n" + "═".repeat(60))
console.log(`ACTIVE HABIT LOOPS (${output.active_habit_loops.length})`)
console.log("═".repeat(60))
for (const loop of output.active_habit_loops) {
  console.log(`  [${loop.id}]  self_awareness: ${loop.self_awareness}`)
}

console.log("\n" + "═".repeat(60))
console.log("TOKEN BUDGET")
console.log("═".repeat(60))
console.log(`  suggested: ${output.suggested_max_tokens} tokens`)

function bar(n: number): string {
  const filled = Math.round(n * 20)
  return "[" + "█".repeat(filled) + "░".repeat(20 - filled) + "]"
}
function pct(n: number): string {
  return (n * 100).toFixed(0).padStart(3) + "%"
}
