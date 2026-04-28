# Pattern: Expo Auth Flow

**Use when**: Adding login/signup screens with JWT token storage.

## Session Manager

```tsx
// lib/storage/session.tsx  (must be .tsx not .ts — uses JSX)
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

## Login Screen

```tsx
// app/(auth)/login.tsx
import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import { useRouter } from 'expo-router'
import { api } from '@/lib/api/client'
import { useSession } from '@/lib/storage/session'

export default function LoginScreen() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { signIn } = useSession()
  const router = useRouter()

  const handleLogin = async () => {
    setError(null)
    setLoading(true)
    try {
      const { access_token, refresh_token } = await api.auth.login(email, password)
      await signIn(access_token, refresh_token)
      router.replace('/(tabs)')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Sign in</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <TextInput style={styles.input} placeholder="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
      <TextInput style={styles.input} placeholder="Password" value={password} onChangeText={setPassword} secureTextEntry />
      <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Sign in</Text>}
      </TouchableOpacity>
      <TouchableOpacity onPress={() => router.push('/(auth)/signup')}>
        <Text style={styles.link}>Don't have an account? Sign up</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center' },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 24 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 12, marginBottom: 12 },
  button: { backgroundColor: '#6366f1', borderRadius: 8, padding: 14, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '600' },
  error: { color: '#ef4444', marginBottom: 12 },
  link: { marginTop: 16, textAlign: 'center', color: '#6366f1' },
})
```

## Dependencies
- `expo-secure-store` — token storage (use `npx expo install`)
