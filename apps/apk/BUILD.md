# apps/apk/BUILD.md

## Requirements

- Node.js 20+
- Android Studio Giraffe or later
- Java 17
- `npm install -g @capacitor/cli`
- Android SDK 33+ (API level 33)

## Setup

```bash
cd characteros
npm install

# Build React app
npm run build

# Add Android target (first time only)
npx cap add android
npx cap sync android

# Open in Android Studio
npx cap open android
```

## capacitor.config.ts (shared with iOS)

```typescript
import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.characteros.app',
  appName: 'CharacterOS',
  webDir: 'dist',
  server: { androidScheme: 'https' },
  plugins: {
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    LocalNotifications: {
      smallIcon: 'ic_stat_notify',
      iconColor: '#c8892a',
      sound: 'none',
    },
  },
}
export default config
```

## Skill widgets → Android native

| Skill type        | Android mechanism                              |
|-------------------|------------------------------------------------|
| push_note         | NotificationManager, NotificationChannel       |
| float_bubble      | Floating window (SYSTEM_ALERT_WINDOW perm)     |
| timed_reminder    | AlarmManager + BroadcastReceiver               |
| intrusive_thought | Heads-up notification, low priority            |
| episode_push      | BigTextStyle notification with action          |
| voice_line        | MediaPlayer via Capacitor plugin               |

## Float bubble permission (Android 8+)

The floating bubble requires `ACTION_MANAGE_OVERLAY_PERMISSION`.
Request at runtime:

```kotlin
// In MainActivity.kt
if (!Settings.canDrawOverlays(this)) {
    val intent = Intent(
        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
        Uri.parse("package:$packageName")
    )
    startActivityForResult(intent, OVERLAY_PERMISSION_REQ)
}
```

## Planning daemon

Same as iOS: `planning.py` runs on a home server or local machine.
App polls `planning/skill_queue.json` via local HTTP
or WebSocket connection to `planning/dashboard.py` on port 7331.

For true background on Android:
- Use a Foreground Service (required for Android 12+)
- Or: planning.py runs on a server, push via FCM

## Build release APK

```bash
# In Android Studio: Build → Generate Signed Bundle/APK
# Or via command line:
cd android
./gradlew assembleRelease
# Output: android/app/build/outputs/apk/release/app-release.apk
```

## Debug on device

```bash
npx cap run android --target=<device-id>
# or
adb install android/app/build/outputs/apk/debug/app-debug.apk
```
