// event_card.ts
// Card widget showing an event description in character voice.
// Appears in the app's main feed when an event fires.

export interface EventCardConfig {
  character_id:   string
  character_name: string
  event_type:     string
  event_desc:     string   // raw event description
  voiced_content: string   // in-character version from api.chat
  intensity:      float
  ts:             string
  can_reply:      boolean
}

export type EventCardStyle = "pill" | "card" | "overlay"

function styleForEvent(type: string, intensity: number): EventCardStyle {
  if (intensity > 0.6) return "overlay"
  if (type === "quiet_moment" || type === "internal_shift") return "pill"
  return "card"
}

export function renderEventCard(config: EventCardConfig): string {
  const style = styleForEvent(config.event_type, config.intensity)
  const name  = config.character_name.split(" ")[0]

  const typeColors: Record<string, string> = {
    quiet_moment:   "#666",
    interaction:    "#2a8a72",
    discovery:      "#3a72a8",
    conflict:       "#c84a3a",
    internal_shift: "#a87032",
  }
  const accent = typeColors[config.event_type] ?? "#666"

  if (style === "pill") {
    return `
<div style="
  display:inline-flex; align-items:center; gap:8px;
  padding:5px 12px; border-radius:20px;
  border:0.5px solid ${accent}22;
  background:${accent}11;
  font-family:monospace; font-size:11px;
  color:#ccc; max-width:280px;
  animation: fadein 0.3s ease;
">
  <span style="color:${accent}; font-size:9px; letter-spacing:.08em; text-transform:uppercase;">
    ${name}
  </span>
  <span style="flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
    ${config.voiced_content}
  </span>
</div>`.trim()
  }

  if (style === "card") {
    return `
<div style="
  padding:12px 14px; border-radius:8px;
  border:0.5px solid ${accent}33;
  border-left:2px solid ${accent};
  background:#111;
  font-family:monospace; font-size:12px; line-height:1.55;
  color:#ddd; max-width:320px;
  animation: fadein 0.3s ease;
">
  <div style="font-size:9px; color:${accent}; letter-spacing:.10em; text-transform:uppercase; margin-bottom:6px;">
    ${name} · ${config.event_type.replace("_"," ")}
  </div>
  ${config.voiced_content}
  ${config.can_reply ? `
  <div style="margin-top:8px; font-size:10px; color:#555; cursor:pointer;"
       onclick="window.dispatchEvent(new CustomEvent('characteros:reply', {detail:'${config.character_id}'}))">
    reply ↗
  </div>` : ""}
</div>`.trim()
  }

  // overlay
  return `
<div style="
  position:fixed; bottom:80px; left:50%; transform:translateX(-50%);
  padding:16px 20px; border-radius:10px;
  border:0.5px solid ${accent}55;
  background:#0d0d0d; box-shadow:0 8px 32px #00000088;
  font-family:monospace; font-size:12px; line-height:1.6;
  color:#e8e4dc; max-width:340px; z-index:9998;
  animation: slidein 0.25s ease;
">
  <div style="font-size:9px; color:${accent}; letter-spacing:.10em; margin-bottom:8px;">
    ${name} · ${config.event_type.replace("_"," ")} · intensity ${config.intensity.toFixed(2)}
  </div>
  ${config.voiced_content}
  <div style="margin-top:10px; display:flex; gap:10px; font-size:10px;">
    ${config.can_reply ? `<span style="color:#2a8a72; cursor:pointer;"
      onclick="window.dispatchEvent(new CustomEvent('characteros:reply',{detail:'${config.character_id}'}))">
      respond ↗
    </span>` : ""}
    <span style="color:#555; cursor:pointer; margin-left:auto;"
      onclick="this.closest('[style*=position:fixed]').remove()">
      dismiss
    </span>
  </div>
</div>`.trim()
}

export function mountEventCard(config: EventCardConfig): void {
  if (typeof document === "undefined") return
  const style = styleForEvent(config.event_type, config.intensity)
  const el    = document.createElement("div")
  el.innerHTML = renderEventCard(config)

  if (style === "pill") {
    // inject into feed
    const feed = document.getElementById("characteros-feed")
    if (feed) feed.prepend(el)
    setTimeout(() => el.remove(), 8000)
  } else if (style === "card") {
    const feed = document.getElementById("characteros-feed")
    if (feed) feed.prepend(el)
  } else {
    document.body.appendChild(el)
    setTimeout(() => el.remove(), 12000)
  }
}
