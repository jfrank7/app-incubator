# Pattern: Expo API Client

**Use when**: Making authenticated HTTP requests to the FastAPI backend.

## API Client

```ts
// lib/api/client.ts
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
  // Add app-specific endpoints here
}
```

## Environment Variable
```
EXPO_PUBLIC_API_URL=http://localhost:8000
```

Must be set in `.env` at the mobile app root. `EXPO_PUBLIC_` prefix required for Expo to expose to JS bundle.

## Notes
- All requests attach JWT from SecureStore automatically
- Throws on non-2xx with status code + body text
- Extend the `api` object with resource-specific methods
