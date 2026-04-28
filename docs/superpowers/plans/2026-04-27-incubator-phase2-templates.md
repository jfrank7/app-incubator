> **SUPERSEDED** — Template-based approach abandoned. See 2026-04-28-agentic-redesign.md

# Agentic App Incubator — Phase 2: Template Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Jinja2 template system for Expo mobile app and FastAPI backend, plus the scaffolder service that renders templates to disk.

**Architecture:** Templates are `.j2` files in `incubator/backend/app/templates/`. A module manifest maps module names to their template files. The `ScaffolderService` takes a `Blueprint` + `ProductSpec`, resolves templates, renders with Jinja2 context, and writes files to `~/generated-apps/<run-id>/`.

**Tech Stack:** Jinja2, Python pathlib, pytest

---

## File Map

**Create:**
- `incubator/backend/app/templates/mobile/base/app/_layout.tsx.j2`
- `incubator/backend/app/templates/mobile/base/app/(auth)/login.tsx.j2`
- `incubator/backend/app/templates/mobile/base/app/(auth)/signup.tsx.j2`
- `incubator/backend/app/templates/mobile/base/app/(tabs)/_layout.tsx.j2`
- `incubator/backend/app/templates/mobile/base/app/(tabs)/index.tsx.j2`
- `incubator/backend/app/templates/mobile/base/lib/api/client.ts.j2`
- `incubator/backend/app/templates/mobile/base/lib/storage/session.ts.j2`
- `incubator/backend/app/templates/mobile/base/package.json.j2`
- `incubator/backend/app/templates/mobile/base/app.json.j2`
- `incubator/backend/app/templates/mobile/base/tsconfig.json.j2`
- `incubator/backend/app/templates/mobile/modules/payments_placeholder/app/paywall.tsx.j2`
- `incubator/backend/app/templates/backend/base/app/main.py.j2`
- `incubator/backend/app/templates/backend/base/app/auth/router.py.j2`
- `incubator/backend/app/templates/backend/base/app/auth/service.py.j2`
- `incubator/backend/app/templates/backend/base/app/core/security.py.j2`
- `incubator/backend/app/templates/backend/base/app/db/database.py.j2`
- `incubator/backend/app/templates/backend/base/app/models/user.py.j2`
- `incubator/backend/app/templates/backend/base/app/schemas/auth.py.j2`
- `incubator/backend/app/templates/backend/base/pyproject.toml.j2`
- `incubator/backend/app/templates/backend/base/.env.example.j2`
- `incubator/backend/app/templates/backend/base/README.md.j2`
- `incubator/backend/app/templates/modules/manifest.py`
- `incubator/backend/app/services/scaffolder.py`
- `incubator/backend/tests/test_scaffolder.py`

---

## Task 7: Module manifest + template registry

**Files:**
- Create: `incubator/backend/app/templates/modules/manifest.py`

- [ ] **Step 1: Write failing test**

`incubator/backend/tests/test_scaffolder.py` (first portion):
```python
import pytest
from app.templates.modules.manifest import MODULE_MANIFEST, get_module_templates


def test_auth_module_always_present():
    templates = get_module_templates(["auth"])
    assert any("auth" in t for t in templates)


def test_payments_placeholder_module():
    templates = get_module_templates(["payments_placeholder"])
    assert any("paywall" in t for t in templates)


def test_unknown_module_raises():
    with pytest.raises(ValueError, match="Unknown module"):
        get_module_templates(["nonexistent_module"])
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && pytest tests/test_scaffolder.py::test_auth_module_always_present -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `incubator/backend/app/templates/modules/manifest.py`**

```python
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).parent.parent

MODULE_MANIFEST: dict[str, list[str]] = {
    "auth": [
        "mobile/base/app/(auth)/login.tsx.j2",
        "mobile/base/app/(auth)/signup.tsx.j2",
        "backend/base/app/auth/router.py.j2",
        "backend/base/app/auth/service.py.j2",
        "backend/base/app/schemas/auth.py.j2",
        "backend/base/app/core/security.py.j2",
        "backend/base/app/models/user.py.j2",
    ],
    "dashboard": [
        "mobile/base/app/(tabs)/index.tsx.j2",
        "mobile/base/app/(tabs)/_layout.tsx.j2",
    ],
    "settings": [
        "mobile/modules/settings/app/(tabs)/settings.tsx.j2",
    ],
    "list_detail_crud": [
        "mobile/modules/list_detail/app/(tabs)/list.tsx.j2",
        "mobile/modules/list_detail/app/(tabs)/detail.tsx.j2",
        "backend/modules/list_detail/app/api/items.py.j2",
        "backend/modules/list_detail/app/models/item.py.j2",
    ],
    "form_flow": [
        "mobile/modules/form_flow/app/(tabs)/new-entry.tsx.j2",
    ],
    "local_persistence": [
        "mobile/base/lib/db/local.ts.j2",
    ],
    "notifications_placeholder": [
        "mobile/modules/notifications/lib/notifications.ts.j2",
    ],
    "payments_placeholder": [
        "mobile/modules/payments_placeholder/app/paywall.tsx.j2",
        "backend/modules/payments_placeholder/app/api/billing.py.j2",
        "backend/modules/payments_placeholder/app/services/billing.py.j2",
    ],
    "analytics_hook": [
        "mobile/base/lib/telemetry/analytics.ts.j2",
    ],
    "onboarding": [
        "mobile/modules/onboarding/app/onboarding.tsx.j2",
    ],
    "profile": [
        "mobile/modules/profile/app/(tabs)/profile.tsx.j2",
    ],
    "search_filter": [
        "mobile/modules/search/app/(tabs)/search.tsx.j2",
    ],
}

BASE_TEMPLATES: list[str] = [
    "mobile/base/app/_layout.tsx.j2",
    "mobile/base/lib/api/client.ts.j2",
    "mobile/base/lib/storage/session.ts.j2",
    "mobile/base/package.json.j2",
    "mobile/base/app.json.j2",
    "mobile/base/tsconfig.json.j2",
    "backend/base/app/main.py.j2",
    "backend/base/app/db/database.py.j2",
    "backend/base/pyproject.toml.j2",
    "backend/base/.env.example.j2",
    "backend/base/README.md.j2",
]


def get_module_templates(modules: list[str]) -> list[str]:
    unknown = [m for m in modules if m not in MODULE_MANIFEST]
    if unknown:
        raise ValueError(f"Unknown module: {unknown}")
    result: list[str] = []
    for m in modules:
        result.extend(MODULE_MANIFEST[m])
    return result
```

- [ ] **Step 4: Run tests**

```bash
cd incubator/backend && pytest tests/test_scaffolder.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/app/templates/modules/manifest.py incubator/backend/tests/test_scaffolder.py
git commit -m "feat: add module manifest and template registry"
```

---

## Task 8: Mobile base templates

**Files:**
- Create: all `mobile/base/**/*.j2` templates

- [ ] **Step 1: Create template directories**

```bash
mkdir -p incubator/backend/app/templates/mobile/base/app/\(auth\)
mkdir -p incubator/backend/app/templates/mobile/base/app/\(tabs\)
mkdir -p incubator/backend/app/templates/mobile/base/lib/{api,storage,db,telemetry}
mkdir -p incubator/backend/app/templates/mobile/modules/{settings,list_detail,form_flow,notifications,payments_placeholder,onboarding,profile,search}
mkdir -p incubator/backend/app/templates/mobile/modules/payments_placeholder/app
mkdir -p incubator/backend/app/templates/mobile/modules/list_detail/app/\(tabs\)
mkdir -p incubator/backend/app/templates/mobile/modules/form_flow/app/\(tabs\)
mkdir -p incubator/backend/app/templates/mobile/modules/settings/app/\(tabs\)
```

- [ ] **Step 2: Write `mobile/base/package.json.j2`**

`incubator/backend/app/templates/mobile/base/package.json.j2`:
```json
{
  "name": "{{ app_slug }}",
  "version": "1.0.0",
  "main": "expo-router/entry",
  "scripts": {
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "lint": "eslint . --ext .ts,.tsx",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "expo": "~51.0.0",
    "expo-router": "~3.5.0",
    "expo-secure-store": "~13.0.0",
    "expo-sqlite": "~14.0.0",
    "expo-status-bar": "~1.12.0",
    "react": "18.2.0",
    "react-native": "0.74.0",
    "@react-native-async-storage/async-storage": "~1.23.0"
  },
  "devDependencies": {
    "@babel/core": "^7.24.0",
    "@types/react": "~18.2.0",
    "typescript": "~5.3.0",
    "eslint": "^8.57.0",
    "eslint-config-expo": "~7.0.0"
  }
}
```

- [ ] **Step 3: Write `mobile/base/app.json.j2`**

`incubator/backend/app/templates/mobile/base/app.json.j2`:
```json
{
  "expo": {
    "name": "{{ app_name }}",
    "slug": "{{ app_slug }}",
    "version": "1.0.0",
    "orientation": "portrait",
    "scheme": "{{ app_slug }}",
    "userInterfaceStyle": "automatic",
    "ios": { "supportsTablet": true },
    "android": { "adaptiveIcon": { "foregroundImage": "./assets/adaptive-icon.png", "backgroundColor": "#ffffff" } },
    "plugins": ["expo-router", "expo-secure-store", ["expo-sqlite", { "enableFTS": true }]]
  }
}
```

- [ ] **Step 4: Write `mobile/base/tsconfig.json.j2`**

```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

- [ ] **Step 5: Write `mobile/base/app/_layout.tsx.j2`**

`incubator/backend/app/templates/mobile/base/app/_layout.tsx.j2`:
```tsx
import { useEffect } from 'react'
import { Stack } from 'expo-router'
import { useSession } from '@/lib/storage/session'

export default function RootLayout() {
  const { session, isLoading } = useSession()

  if (isLoading) return null

  return (
    <Stack>
      <Stack.Screen name="(auth)" options={{ headerShown: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
    </Stack>
  )
}
```

- [ ] **Step 6: Write `mobile/base/app/(auth)/login.tsx.j2`**

`incubator/backend/app/templates/mobile/base/app/(auth)/login.tsx.j2`:
```tsx
import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native'
import { useRouter } from 'expo-router'
import { useSession } from '@/lib/storage/session'
import { api } from '@/lib/api/client'

export default function LoginScreen() {
  const router = useRouter()
  const { signIn } = useSession()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    if (!email || !password) { Alert.alert('Error', 'Email and password required'); return }
    setLoading(true)
    try {
      const { access_token, refresh_token } = await api.auth.login(email, password)
      await signIn(access_token, refresh_token)
      router.replace('/(tabs)/')
    } catch (e) {
      Alert.alert('Login failed', String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{{ app_name }}</Text>
      <TextInput style={styles.input} placeholder="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
      <TextInput style={styles.input} placeholder="Password" value={password} onChangeText={setPassword} secureTextEntry />
      <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
        <Text style={styles.buttonText}>{loading ? 'Signing in...' : 'Sign in'}</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => router.push('/(auth)/signup')}>
        <Text style={styles.link}>Don't have an account? Sign up</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 24 },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 32, textAlign: 'center' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, marginBottom: 12 },
  button: { backgroundColor: '#2563eb', borderRadius: 8, padding: 14, alignItems: 'center', marginBottom: 12 },
  buttonText: { color: '#fff', fontWeight: '600' },
  link: { textAlign: 'center', color: '#2563eb' },
})
```

- [ ] **Step 7: Write `mobile/base/app/(auth)/signup.tsx.j2`**

`incubator/backend/app/templates/mobile/base/app/(auth)/signup.tsx.j2`:
```tsx
import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native'
import { useRouter } from 'expo-router'
import { useSession } from '@/lib/storage/session'
import { api } from '@/lib/api/client'

export default function SignupScreen() {
  const router = useRouter()
  const { signIn } = useSession()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSignup = async () => {
    if (!email || !password) { Alert.alert('Error', 'Email and password required'); return }
    setLoading(true)
    try {
      const { access_token, refresh_token } = await api.auth.register(email, password)
      await signIn(access_token, refresh_token)
      router.replace('/(tabs)/')
    } catch (e) {
      Alert.alert('Signup failed', String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Create account</Text>
      <TextInput style={styles.input} placeholder="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
      <TextInput style={styles.input} placeholder="Password" value={password} onChangeText={setPassword} secureTextEntry />
      <TouchableOpacity style={styles.button} onPress={handleSignup} disabled={loading}>
        <Text style={styles.buttonText}>{loading ? 'Creating account...' : 'Sign up'}</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => router.back()}>
        <Text style={styles.link}>Already have an account? Sign in</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 24 },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 32, textAlign: 'center' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, marginBottom: 12 },
  button: { backgroundColor: '#2563eb', borderRadius: 8, padding: 14, alignItems: 'center', marginBottom: 12 },
  buttonText: { color: '#fff', fontWeight: '600' },
  link: { textAlign: 'center', color: '#2563eb' },
})
```

- [ ] **Step 8: Write `mobile/base/app/(tabs)/_layout.tsx.j2`**

`incubator/backend/app/templates/mobile/base/app/(tabs)/_layout.tsx.j2`:
```tsx
import { Tabs } from 'expo-router'
import { useSession } from '@/lib/storage/session'
import { useRouter } from 'expo-router'
import { useEffect } from 'react'

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

- [ ] **Step 9: Write `mobile/base/app/(tabs)/index.tsx.j2`**

`incubator/backend/app/templates/mobile/base/app/(tabs)/index.tsx.j2`:
```tsx
import { View, Text, StyleSheet, ScrollView } from 'react-native'

export default function HomeScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{{ app_name }}</Text>
      <Text style={styles.subtitle}>{{ goal }}</Text>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 8 },
  subtitle: { fontSize: 16, color: '#666' },
})
```

- [ ] **Step 10: Write `mobile/base/lib/storage/session.ts.j2`**

`incubator/backend/app/templates/mobile/base/lib/storage/session.ts.j2`:
```typescript
import * as SecureStore from 'expo-secure-store'
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

interface SessionContext {
  session: string | null
  isLoading: boolean
  signIn: (accessToken: string, refreshToken: string) => Promise<void>
  signOut: () => Promise<void>
}

const SessionCtx = createContext<SessionContext | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    SecureStore.getItemAsync('access_token').then(token => {
      setSession(token)
      setIsLoading(false)
    })
  }, [])

  const signIn = async (accessToken: string, refreshToken: string) => {
    await SecureStore.setItemAsync('access_token', accessToken)
    await SecureStore.setItemAsync('refresh_token', refreshToken)
    setSession(accessToken)
  }

  const signOut = async () => {
    await SecureStore.deleteItemAsync('access_token')
    await SecureStore.deleteItemAsync('refresh_token')
    setSession(null)
  }

  return <SessionCtx.Provider value={{ session, isLoading, signIn, signOut }}>{children}</SessionCtx.Provider>
}

export function useSession(): SessionContext {
  const ctx = useContext(SessionCtx)
  if (!ctx) throw new Error('useSession must be used within SessionProvider')
  return ctx
}
```

- [ ] **Step 11: Write `mobile/base/lib/api/client.ts.j2`**

`incubator/backend/app/templates/mobile/base/lib/api/client.ts.j2`:
```typescript
import * as SecureStore from 'expo-secure-store'

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await SecureStore.getItemAsync('access_token')
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; refresh_token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    register: (email: string, password: string) =>
      request<{ access_token: string; refresh_token: string }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
  },
  health: () => request<{ status: string }>('/health'),
}
```

- [ ] **Step 12: Write `mobile/base/lib/telemetry/analytics.ts.j2`**

`incubator/backend/app/templates/mobile/base/lib/telemetry/analytics.ts.j2`:
```typescript
export function logEvent(name: string, params?: Record<string, unknown>): void {
  if (__DEV__) {
    console.log('[analytics]', name, params)
  }
}

export function logError(error: Error, context?: Record<string, unknown>): void {
  console.error('[error]', error.message, context)
}
```

- [ ] **Step 13: Write payments placeholder template**

`incubator/backend/app/templates/mobile/modules/payments_placeholder/app/paywall.tsx.j2`:
```tsx
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native'
import { useRouter } from 'expo-router'

export default function PaywallScreen() {
  const router = useRouter()
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{{ app_name }} Pro</Text>
      <Text style={styles.subtitle}>Unlock all features</Text>
      <Text style={styles.price}>$4.99 / month</Text>
      <TouchableOpacity style={styles.button} onPress={() => alert('Billing not yet implemented')}>
        <Text style={styles.buttonText}>Subscribe (placeholder)</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => router.back()}>
        <Text style={styles.skip}>Maybe later</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 8 },
  subtitle: { fontSize: 16, color: '#666', marginBottom: 24 },
  price: { fontSize: 20, fontWeight: '600', marginBottom: 32 },
  button: { backgroundColor: '#2563eb', borderRadius: 8, padding: 16, width: '100%', alignItems: 'center', marginBottom: 16 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 16 },
  skip: { color: '#888' },
})
```

- [ ] **Step 14: Commit**

```bash
git add incubator/backend/app/templates/mobile/
git commit -m "feat: add Expo mobile base templates and module templates"
```

---

## Task 9: Backend base templates

**Files:**
- Create: all `backend/base/**/*.j2` templates
- Create: all `backend/modules/**/*.j2` templates

- [ ] **Step 1: Create backend template directories**

```bash
mkdir -p incubator/backend/app/templates/backend/base/app/{auth,core,db,models,schemas,api,services,telemetry}
mkdir -p incubator/backend/app/templates/backend/modules/{list_detail,payments_placeholder,form_flow}
mkdir -p incubator/backend/app/templates/backend/modules/list_detail/app/{api,models}
mkdir -p incubator/backend/app/templates/backend/modules/payments_placeholder/app/{api,services}
```

- [ ] **Step 2: Write `backend/base/app/main.py.j2`**

`incubator/backend/app/templates/backend/base/app/main.py.j2`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import init_db
from app.auth.router import router as auth_router
{% if "list_detail_crud" in selected_modules %}
from app.api.items import router as items_router
{% endif %}
{% if "payments_placeholder" in selected_modules %}
from app.api.billing import router as billing_router
{% endif %}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="{{ app_name }}", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
{% if "list_detail_crud" in selected_modules %}
app.include_router(items_router)
{% endif %}
{% if "payments_placeholder" in selected_modules %}
app.include_router(billing_router)
{% endif %}


@app.get("/health")
async def health():
    return {"status": "ok", "app": "{{ app_slug }}"}
```

- [ ] **Step 3: Write `backend/base/app/core/security.py.j2`**

`incubator/backend/app/templates/backend/base/app/core/security.py.j2`:
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": subject, "exp": expire, "type": "refresh"}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    sub = payload.get("sub")
    if sub is None:
        raise JWTError("No subject")
    return sub
```

- [ ] **Step 4: Write `backend/base/app/db/database.py.j2`**

`incubator/backend/app/templates/backend/base/app/db/database.py.j2`:
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./{{ app_slug }}.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 5: Write `backend/base/app/models/user.py.j2`**

`incubator/backend/app/templates/backend/base/app/models/user.py.j2`:
```python
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 6: Write `backend/base/app/schemas/auth.py.j2`**

`incubator/backend/app/templates/backend/base/app/schemas/auth.py.j2`:
```python
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
```

- [ ] **Step 7: Write `backend/base/app/auth/service.py.j2`**

`incubator/backend/app/templates/backend/base/app/auth/service.py.j2`:
```python
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.user import User
from app.core.security import verify_password, hash_password, create_access_token, create_refresh_token


async def register_user(email: str, password: str, session: AsyncSession) -> dict:
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(id=str(uuid.uuid4()), email=email, hashed_password=hash_password(password))
    session.add(user)
    await session.commit()
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


async def login_user(email: str, password: str, session: AsyncSession) -> dict:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }
```

- [ ] **Step 8: Write `backend/base/app/auth/router.py.j2`**

`incubator/backend/app/templates/backend/base/app/auth/router.py.j2`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.auth.service import register_user, login_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    tokens = await register_user(body.email, body.password, session)
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    tokens = await login_user(body.email, body.password, session)
    return TokenResponse(**tokens)
```

- [ ] **Step 9: Write `backend/base/pyproject.toml.j2`**

`incubator/backend/app/templates/backend/base/pyproject.toml.j2`:
```toml
[project]
name = "{{ app_slug }}-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.20.0",
    "pydantic>=2.7.0",
    "pydantic[email]>=2.7.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 10: Write `backend/base/.env.example.j2`**

`incubator/backend/app/templates/backend/base/.env.example.j2`:
```
DATABASE_URL=sqlite+aiosqlite:///./{{ app_slug }}.db
SECRET_KEY=change-me-in-production
{% if payments_placeholder %}
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
{% endif %}
EXPO_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 11: Write `backend/base/README.md.j2`**

`incubator/backend/app/templates/backend/base/README.md.j2`:
```markdown
# {{ app_name }} — Backend

Generated by App Incubator.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# edit .env with your values
uvicorn app.main:app --reload
```

## Auth endpoints

- `POST /auth/register` — create account
- `POST /auth/login` — get tokens
- `GET /health` — health check

## Mobile app

See `../apps/mobile/` for the Expo app.
```
```

- [ ] **Step 12: Write payments placeholder backend templates**

`incubator/backend/app/templates/backend/modules/payments_placeholder/app/services/billing.py.j2`:
```python
class BillingService:
    """Placeholder billing service. Replace with real Stripe integration."""

    async def get_subscription_status(self, user_id: str) -> dict:
        return {"status": "free", "plan": None}

    async def create_checkout_session(self, user_id: str, plan: str) -> dict:
        raise NotImplementedError("Billing not implemented in v1")
```

`incubator/backend/app/templates/backend/modules/payments_placeholder/app/api/billing.py.j2`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/status")
async def billing_status():
    return {"status": "free", "plan": None, "note": "Billing not implemented"}


@router.post("/webhook")
async def billing_webhook():
    return {"received": True}
```

- [ ] **Step 13: Commit**

```bash
git add incubator/backend/app/templates/backend/
git commit -m "feat: add FastAPI backend base templates and module templates"
```

---

## Task 10: Scaffolder service

**Files:**
- Create: `incubator/backend/app/services/scaffolder.py`
- Modify: `incubator/backend/tests/test_scaffolder.py`

- [ ] **Step 1: Add scaffolder tests**

Append to `incubator/backend/tests/test_scaffolder.py`:
```python
import shutil
from pathlib import Path
import pytest
from app.services.scaffolder import ScaffolderService
from app.schemas.form import ProductSpec, ScreenSpec, EntitySpec, ArchitectureBlueprint, FilePlan, APIRoute, EnvVar


@pytest.fixture
def sample_spec() -> ProductSpec:
    return ProductSpec(
        app_name="Caffeine Tracker",
        app_slug="caffeine-tracker",
        goal="track daily caffeine",
        target_user="health-conscious adults",
        screens=[ScreenSpec(name="Dashboard", route="/", description="main view")],
        features=["logging"],
        data_entities=[EntitySpec(name="CaffeineEntry", fields=["id", "mg", "timestamp"])],
        offline_support=True,
        notifications=False,
        auth_required=True,
        payments_placeholder=False,
        style_notes="minimal",
        non_goals=["social"],
    )


@pytest.fixture
def sample_blueprint(sample_spec) -> ArchitectureBlueprint:
    return ArchitectureBlueprint(
        selected_modules=["auth", "dashboard", "local_persistence", "analytics_hook"],
        file_plan=[
            FilePlan(
                path="apps/mobile/package.json",
                template="mobile/base/package.json.j2",
                context_keys=["app_name", "app_slug"],
            ),
            FilePlan(
                path="apps/mobile/app.json",
                template="mobile/base/app.json.j2",
                context_keys=["app_name", "app_slug"],
            ),
        ],
        api_routes=[],
        db_entities=["User"],
        env_vars=[EnvVar(key="SECRET_KEY", example_value="change-me", description="JWT secret")],
    )


@pytest.fixture
def output_dir(tmp_path) -> Path:
    d = tmp_path / "test-run-id"
    d.mkdir()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_scaffolder_renders_package_json(sample_spec, sample_blueprint, output_dir):
    svc = ScaffolderService()
    written = svc.scaffold(sample_spec, sample_blueprint, output_dir)
    pkg_path = output_dir / "apps/mobile/package.json"
    assert pkg_path.exists()
    content = pkg_path.read_text()
    assert "caffeine-tracker" in content
    assert "Caffeine Tracker" not in content  # slug used not name


def test_scaffolder_returns_file_list(sample_spec, sample_blueprint, output_dir):
    svc = ScaffolderService()
    written = svc.scaffold(sample_spec, sample_blueprint, output_dir)
    assert len(written) == 2
    assert all(isinstance(p, str) for p in written)
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && pytest tests/test_scaffolder.py::test_scaffolder_renders_package_json -v
```

Expected: `ImportError` — scaffolder not defined.

- [ ] **Step 3: Write `incubator/backend/app/services/scaffolder.py`**

```python
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from app.schemas.form import ProductSpec, ArchitectureBlueprint

TEMPLATES_ROOT = Path(__file__).parent.parent / "templates"


class ScaffolderService:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_ROOT)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def _build_context(self, spec: ProductSpec, blueprint: ArchitectureBlueprint) -> dict:
        return {
            "app_name": spec.app_name,
            "app_slug": spec.app_slug,
            "goal": spec.goal,
            "target_user": spec.target_user,
            "offline_support": spec.offline_support,
            "notifications": spec.notifications,
            "auth_required": spec.auth_required,
            "payments_placeholder": spec.payments_placeholder,
            "style_notes": spec.style_notes,
            "non_goals": spec.non_goals,
            "screens": spec.screens,
            "data_entities": spec.data_entities,
            "features": spec.features,
            "selected_modules": blueprint.selected_modules,
            "api_routes": blueprint.api_routes,
            "db_entities": blueprint.db_entities,
            "env_vars": blueprint.env_vars,
        }

    def scaffold(
        self,
        spec: ProductSpec,
        blueprint: ArchitectureBlueprint,
        output_dir: Path,
    ) -> list[str]:
        context = self._build_context(spec, blueprint)
        written: list[str] = []

        for file_plan in blueprint.file_plan:
            template = self.env.get_template(file_plan.template)
            rendered = template.render(**context)
            dest = output_dir / file_plan.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(rendered, encoding="utf-8")
            written.append(str(dest))

        return written
```

- [ ] **Step 4: Run tests**

```bash
cd incubator/backend && pytest tests/test_scaffolder.py -v
```

Expected: all pass. (Some tests may warn about missing template files — that's expected until all templates exist.)

- [ ] **Step 5: Run all tests**

```bash
cd incubator/backend && pytest -v && ruff check .
```

Expected: all pass, no lint errors.

- [ ] **Step 6: Commit**

```bash
git add incubator/backend/app/services/scaffolder.py incubator/backend/tests/test_scaffolder.py
git commit -m "feat: add scaffolder service that renders Jinja2 templates to disk"
```

---

## Phase 2 Complete

**What was built:**
- Full Jinja2 template library for Expo mobile (auth, routing, API client, SecureStore session, analytics hook, payments placeholder)
- Full Jinja2 template library for FastAPI backend (auth, JWT security, DB, models, schemas, billing stubs)
- Module manifest mapping module names to template files
- `ScaffolderService` rendering templates to disk from a `Blueprint`

**Review questions:**
1. Any screens or modules missing from the templates you know you'll need?
2. Backend templates use `python-jose` for JWT — OK or prefer `PyJWT`?
