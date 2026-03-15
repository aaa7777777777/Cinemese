// plot_nudge.ts
// Push notification sent after a significant event fires.
// Content is a one-line story nudge in character voice — not a summary,
// the thing that would make you want to open the app.

export interface PlotNudgeConfig {
  character_id:    string
  character_name:  string
  event_type:      string
  voiced_nudge:    string   // ≤60 chars, in-character, from api.chat
  intensity:       number
  after_collision: boolean  // true when this follows an agent-to-agent episode
}

const NUDGE_TEMPLATES: Record<string, string[]> = {
  quiet_moment:   ["{name} is somewhere.", "something's on {name}'s mind."],
  interaction:    ["something happened between {name} and someone.", "{name} just talked to someone."],
  discovery:      ["{name} found something out.", "{name} realized something."],
  conflict:       ["{name} is in the middle of something.", "it got complicated for {name}."],
  internal_shift: ["{name} is different today.", "something shifted for {name}."],
}

function fillTemplate(tmpl: string, name: string): string {
  return tmpl.replace("{name}", name.split(" ")[0])
}

function fallbackNudge(config: PlotNudgeConfig): string {
  const templates = NUDGE_TEMPLATES[config.event_type] ?? ["{name}."]
  const tmpl = templates[Math.floor(Math.random() * templates.length)]
  return fillTemplate(tmpl, config.character_name)
}

export async function sendPlotNudge(config: PlotNudgeConfig): Promise<void> {
  const name  = config.character_name.split(" ")[0]
  const body  = config.voiced_nudge || fallbackNudge(config)
  const title = config.after_collision ? `${name} just had an encounter` : name

  // Capacitor
  if (typeof (window as any).Capacitor !== "undefined") {
    const { LocalNotifications } = await import("@capacitor/local-notifications")
    await LocalNotifications.schedule({
      notifications: [{
        id:   Date.now(),
        title,
        body,
        extra: {
          character_id:    config.character_id,
          skill_type:      "plot_nudge",
          event_type:      config.event_type,
          after_collision: config.after_collision,
        },
        actionTypeId: "OPEN_CHARACTER",
      }],
    })
    return
  }

  // Web Notifications
  if ("Notification" in window && Notification.permission === "granted") {
    const n = new Notification(title, {
      body,
      tag:    `plot_${config.character_id}_${config.event_type}`,
      silent: config.event_type === "quiet_moment",
    })
    n.onclick = () => {
      window.dispatchEvent(new CustomEvent("characteros:open", {
        detail: { character_id: config.character_id }
      }))
      n.close()
    }
  }
}

// Decide if this event warrants a nudge at all
export function shouldNudge(intensity: number, event_type: string, after_collision: boolean): boolean {
  if (after_collision) return true
  if (event_type === "conflict" && intensity > 0.40) return true
  if (event_type === "internal_shift" && intensity > 0.35) return true
  if (event_type === "discovery" && intensity > 0.38) return true
  if (intensity > 0.50) return true
  return false
}
