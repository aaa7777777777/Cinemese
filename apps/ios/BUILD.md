# apps/ios/BUILD.md

## Requirements

- Node.js 20+
- Xcode 15+ (macOS only)
- Apple Developer account (for device install)
- `npm install -g @capacitor/cli`

## Setup

```bash
cd characteros
npm install

# Build React app
npm run build

# Sync to iOS
npx cap add ios
npx cap sync ios

# Open in Xcode
npx cap open ios
```

## capacitor.config.ts

```typescript
import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.characteros.app',
  appName: 'CharacterOS',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
  plugins: {
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    LocalNotifications: {
      smallIcon: 'ic_stat_icon_config_sample',
      iconColor: '#488AFF',
    },
  },
}

export default config
```

## Planning daemon

planning.py runs as a local Python process on the same device (or home server).
The React app polls `planning/skill_queue.json` and `planning/context_patch.json`
via a local HTTP server (planning/dashboard.py serves on localhost:7331).

For true background operation on iOS:
- Use a home server or VPS for planning.py
- Mobile app connects via WebSocket to receive skill dispatches
- soul_doc stays device-local, synced via iCloud if user opts in

## Skill widgets → iOS native

| Skill type       | iOS mechanism                              |
|------------------|--------------------------------------------|
| push_note        | UNUserNotificationCenter                   |
| float_bubble     | Capacitor overlay plugin (custom)          |
| timed_reminder   | UNTimeIntervalNotificationTrigger          |
| intrusive_thought| Local notification, no sound               |
| episode_push     | Rich notification with expand              |
| voice_line       | AVAudioPlayer via Capacitor plugin         |
