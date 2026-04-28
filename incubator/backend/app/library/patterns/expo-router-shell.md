# Pattern: Expo Router Shell

**Use when**: Setting up the root navigation shell for an Expo Router app.

## Key files
- `app/_layout.tsx` — root layout, provides context, declares Stack screens
- `app/(tabs)/_layout.tsx` — tab navigator with auth guard
- `app/(auth)/login.tsx`, `app/(auth)/signup.tsx` — auth screens

## Root Layout Pattern

```tsx
// app/_layout.tsx
import { Stack } from 'expo-router'
import { SessionProvider, useSession } from '@/lib/storage/session'

function RootLayoutNav() {
  const { isLoading } = useSession()
  if (isLoading) return null
  return (
    <Stack>
      <Stack.Screen name="(auth)" options={{ headerShown: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
    </Stack>
  )
}

export default function RootLayout() {
  return (
    <SessionProvider>
      <RootLayoutNav />
    </SessionProvider>
  )
}
```

**Critical**: `SessionProvider` must wrap an inner component. Never call `useSession()` directly in `RootLayout` — there's no provider above it.

## Tabs Layout with Auth Guard

```tsx
// app/(tabs)/_layout.tsx
import { useEffect } from 'react'
import { Tabs } from 'expo-router'
import { useRouter } from 'expo-router'
import { useSession } from '@/lib/storage/session'

export default function TabsLayout() {
  const { session, isLoading } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !session) router.replace('/(auth)/login')
  }, [session, isLoading])

  return (
    <Tabs>
      <Tabs.Screen name="index" options={{ title: 'Home' }} />
      <Tabs.Screen name="settings" options={{ title: 'Settings' }} />
    </Tabs>
  )
}
```

## Required Config Files

```js
// babel.config.js
module.exports = function (api) {
  api.cache(true)
  return { presets: ['babel-preset-expo'] }
}
```

```js
// metro.config.js
const { getDefaultConfig } = require('expo/metro-config')
module.exports = getDefaultConfig(__dirname)
```

```json
// tsconfig.json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "paths": { "@/*": ["./*"] }
  }
}
```

## app.json Minimal

```json
{
  "expo": {
    "name": "APP_NAME",
    "slug": "app-slug",
    "version": "1.0.0",
    "orientation": "portrait",
    "scheme": "app-slug",
    "userInterfaceStyle": "automatic",
    "ios": { "supportsTablet": true },
    "plugins": ["expo-router", "expo-secure-store"]
  }
}
```

**Note**: Do NOT include `android.adaptiveIcon` unless you are also generating the actual PNG asset file.

## Dependencies (verify versions before use)
- `expo` — check Expo SDK release for current version
- `expo-router` — check for current version compatible with SDK
- `react` / `react-native` — constrained by Expo SDK
- `react-native-safe-area-context` — use `npx expo install` to get compatible version
- `react-native-screens` — use `npx expo install`
- `expo-status-bar` — bundled with SDK
