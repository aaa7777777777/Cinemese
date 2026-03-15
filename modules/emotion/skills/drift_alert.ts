// drift_alert.ts
// Push notification when emotion drift_pressure crosses threshold.
// Uses Capacitor LocalNotifications on mobile, Web Notifications API on web.

export interface DriftAlertConfig {
  character_name:  string
  character_id:    string
  dominant_color:  string
  drift_pressure:  number
  rhythm_phase:    string
  content:         string   // pre-generated in-character text from api.chat
}

const DRIFT_THRESHOLD = 0.60

export function shouldAlert(drift_pressure: number, last_alert_ts?: number): boolean {
  if (drift_pressure < DRIFT_THRESHOLD) return false
  if (!last_alert_ts) return true
  // Don't alert more than once per hour
  return (Date.now() - last_alert_ts) > 60 * 60 * 1000
}

export async function sendDriftAlert(config: DriftAlertConfig): Promise<void> {
  const title = config.character_name.split(" ")[0]
  const body  = config.content

  // Capacitor push (mobile)
  if (typeof (window as any).Capacitor !== "undefined") {
    const { LocalNotifications } = await import("@capacitor/local-notifications")
    await LocalNotifications.schedule({
      notifications: [{
        id:    Date.now(),
        title,
        body,
        extra: {
          character_id:   config.character_id,
          skill_type:     "drift_alert",
          drift_pressure: config.drift_pressure,
        },
      }],
    })
    return
  }

  // Web Notifications fallback
  if ("Notification" in window) {
    if (Notification.permission === "granted") {
      new Notification(title, { body, tag: `drift_${config.character_id}` })
    } else if (Notification.permission !== "denied") {
      const perm = await Notification.requestPermission()
      if (perm === "granted") {
        new Notification(title, { body })
      }
    }
  }
}
