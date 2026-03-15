import { chandler } from "../core/soul_doc/chandler"
import { assemble } from "../core/assembler/index"
import { deriveEmotionState } from "../modules/emotion/index"
import type { NowContext } from "../core/types/index"

async function run() {
  const context: NowContext = {
    time_of_day: "late_night",
    day_type: "weekend",
    location: "the couch",
    user_message: `你应该认真想想下一步打算做什么。你值得更好的。`,
    skill_type: "dialogue",
  }

  const emotion = deriveEmotionState(chandler, context)

  console.log("\n── Emotion state ──────────────────────────────")
  console.log(`  valence:        ${emotion.valence.toFixed(3)}`)
  console.log(`  arousal:        ${emotion.arousal.toFixed(3)}`)
  console.log(`  drift_pressure: ${emotion.drift_pressure.toFixed(3)}`)
  console.log(`  color:          ${emotion.dominant_color}`)
  console.log(`  window:         ${emotion.window_note}`)

  const { system, user } = assemble({ soul_doc: chandler, emotion, context })

  console.log("\n── System prompt ──────────────────────────────")
  console.log(system)
  console.log("\n── User turn ──────────────────────────────────")
  console.log(user)

  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) {
    console.log("\n── No ANTHROPIC_API_KEY found — prompt printed above, not sent.\n")
    return
  }

  console.log("\n── Calling API ────────────────────────────────")
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-opus-4-5",
      max_tokens: 300,
      system,
      messages: [{ role: "user", content: user }],
    }),
  })

  const data = await res.json() as any
  console.log("\n── Response ───────────────────────────────────")
  console.log(data?.content?.[0]?.text ?? JSON.stringify(data))
  console.log("───────────────────────────────────────────────\n")
}

run().catch(console.error)
