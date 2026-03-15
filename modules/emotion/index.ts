import type { SoulDoc, EmotionState, NowContext } from "../../core/types/index"

export function deriveEmotionState(soul: SoulDoc, context: NowContext): EmotionState {
  const t = soul.trait_weights

  let valence =
    (t["self_worth"] ?? 0.5) * 0.4 +
    (t["warmth_when_safe"] ?? 0.5) * 0.3 -
    (t["cynicism"] ?? 0.3) * 0.2 -
    (t["fear_of_permanence"] ?? 0.5) * 0.1

  let arousal =
    (t["deflection_via_humor"] ?? 0.5) * 0.3 +
    (t["genuine_vulnerability"] ?? 0.3) * 0.2

  if (context.time_of_day === "late_night") { arousal -= 0.15; valence -= 0.08 }
  if (context.day_type === "weekend" && context.time_of_day === "evening") arousal -= 0.10
  if (context.recent_event?.includes("argument")) { arousal += 0.25; valence -= 0.15 }

  valence = Math.max(-1, Math.min(1, valence))
  arousal = Math.max(0, Math.min(1, arousal))

  return {
    valence,
    arousal,
    dominant_color: resolveDominantColor(valence, arousal, context, soul),
    flashback_triggers: ["deserve", "worth", "stay", "leave", "thanksgiving", "marry", "decided", "realized"],
    drift_pressure: arousal * 0.6 + Math.abs(valence) * 0.4,
    window_note: buildWindowNote(context),
  }
}

function resolveDominantColor(v: number, a: number, ctx: NowContext, soul: SoulDoc): string {
  if (ctx.time_of_day === "late_night" && a < 0.4)
    return "the specific quiet of being alone at night that doesn't have a name"
  if (a > 0.65 && v < 0) return "running fast to stay in the same place"
  if (v > 0.3 && a < 0.4) return "quietly okay, not pushing it"
  if ((soul.trait_weights["deflection_via_humor"] ?? 0) > 0.8 && a < 0.5)
    return "dry, watchful, conserving"
  return "somewhere in the middle of things"
}

function buildWindowNote(context: NowContext): string {
  const parts: string[] = []
  if (context.time_of_day === "late_night" && context.day_type === "weekend")
    parts.push("Saturday night. The couch. The TV may or may not be on.")
  else if (context.time_of_day === "morning")
    parts.push("Morning. Low battery. The day hasn't asked anything of him yet.")
  if (context.recent_event) parts.push(`Recent: ${context.recent_event}.`)
  return parts.join(" ")
}
