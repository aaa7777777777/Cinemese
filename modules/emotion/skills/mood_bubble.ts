// mood_bubble.ts
// Persistent floating widget showing current emotion color.
// Rendered via Capacitor overlay plugin on mobile.

export interface MoodBubbleConfig {
  character_name: string
  emotion_color:  string     // dominant_color from EmotionState
  valence:        number
  arousal:        number
  auto_dismiss_ms?: number   // default: stays until tapped
}

// Generate the HTML/CSS for the bubble
export function renderMoodBubble(config: MoodBubbleConfig): string {
  const intensity = Math.abs(config.valence) * 0.5 + config.arousal * 0.5
  const size = Math.round(44 + intensity * 20)
  const opacity = 0.72 + intensity * 0.18

  // Color based on valence direction
  const hue = config.valence > 0.1 ? "#c8892a"
    : config.valence < -0.2 ? "#4a72a8"
    : "#666"

  return `
<div style="
  width:${size}px; height:${size}px;
  border-radius:50%;
  background:${hue};
  opacity:${opacity.toFixed(2)};
  display:flex; align-items:center; justify-content:center;
  font-family:monospace; font-size:9px; color:#fff;
  text-align:center; padding:6px;
  cursor:pointer;
  line-height:1.3;
">
  ${config.character_name.split(" ")[0]}
</div>
  `.trim()
}

// Dispatch config to the native overlay
export async function showMoodBubble(config: MoodBubbleConfig): Promise<void> {
  // In Capacitor: use a custom plugin or FloatingActionButton plugin
  // For web: inject as a fixed-position overlay
  if (typeof document !== "undefined") {
    const existing = document.getElementById("characteros-mood-bubble")
    if (existing) existing.remove()

    const el = document.createElement("div")
    el.id = "characteros-mood-bubble"
    el.style.cssText = `
      position: fixed;
      bottom: 88px;
      right: 16px;
      z-index: 9999;
      cursor: pointer;
    `
    el.innerHTML = renderMoodBubble(config)
    el.title = config.emotion_color

    el.addEventListener("click", () => {
      el.remove()
      // Trigger dialogue open in app
      window.dispatchEvent(new CustomEvent("characteros:bubble-tapped", { detail: config }))
    })

    document.body.appendChild(el)

    if (config.auto_dismiss_ms) {
      setTimeout(() => el.remove(), config.auto_dismiss_ms)
    }
  }
}
