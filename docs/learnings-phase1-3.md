# App Incubator — Phase 1–3 Learnings

Hard-won lessons from building a Jinja2-template-based mobile app generation pipeline (Expo + FastAPI). The project is now pivoting away from templates to a fully agentic approach. These lessons are captured for future reference.

---

## Template / Generation Lessons

1. **Jinja2 `{{ }}` conflicts with JSX object props.** Syntax like `options={{ headerShown: false }}` causes a parse error: "expected end of print statement". Non-variable sections containing JSX object props must be wrapped in `{% raw %}...{% endraw %}` blocks.

2. **Hardcoded library versions go stale fast.** Expo SDK 51 templates broke on phones running SDK 54. A version-checking step is essential before any code generation.

3. **Templates that reference conditionally-generated files create mismatch bugs.** For example, `(tabs)/_layout.tsx` hardcoded a settings tab, but `settings.tsx` was only generated if the settings module was selected. Either make the reference conditional or always generate the referenced file.

4. **File extension matters for JSX.** A file named `session.ts` containing JSX content causes "SyntaxError: cannot use JSX without tsx extension". All files with JSX must use `.tsx`.

5. **Missing standard config files cause obscure runtime errors.** `babel.config.js` and `metro.config.js` are not optional — always generate them.

6. **The `adaptiveIcon` in `app.json` requires a real asset file.** Generating the config reference without the actual asset file produces warnings. Either generate the asset or omit the `adaptiveIcon` config entirely.

7. **Template approach creates tight coupling.** When the app architecture changes, every affected template must change individually. There is no abstraction layer.

---

## React Native / Expo Lessons

1. **`SessionProvider` must wrap the root layout.** Calling `useSession()` at the top level of `RootLayout` without a provider above it throws an error. The correct pattern: an inner component consumes the hook; the outer component provides the context.

2. **`PlatformConstants` TurboModule errors in Expo Go often point to missing config files or stale Metro cache.** Always clear Metro cache (`npx expo start --clear`) when debugging unexplained native module errors. Missing `babel.config.js` or `metro.config.js` are common culprits.

3. **Expo SDK version must match Expo Go on the device exactly.** `~54.0.0` targets the SDK 54 family. Generating SDK 51 code for a device running Expo Go for SDK 54 blocks the app from opening entirely.

4. **`react-native-screens` and `react-native-safe-area-context` must be explicitly installed even with `expo-router`.** Use `npx expo install` (not `npm install`) to get SDK-compatible versions.

5. **`expo-sqlite` v14 has ESM incompatibility with Node 22.** Avoid it in generated apps unless specifically required. Use AsyncStorage for lightweight local storage instead.

---

## Backend / Pipeline Lessons

1. **SSE `TimeoutError` must be caught *inside* the `while True` loop.** Catching it outside closes the stream after the first timeout rather than allowing it to continue. This caused live streaming to silently cut off.

2. **`_update_run()` should raise `RuntimeError` when the run isn't found, not silently no-op.** Silent failures hide bugs — missing run IDs are always a programming error and should surface immediately.

3. **CORS origins in pydantic-settings must be a JSON array string.** Use `["http://localhost:5173"]`, not a bare URL string. A bare URL causes CORS to silently reject all cross-origin requests.

4. **`asyncio.create_task` for fire-and-forget pipeline stages works well but requires the task to be retained.** If the task object is not held in a reference, it may be garbage-collected before it completes.

5. **`ContextVar` for async session injection enables clean test isolation.** It avoids monkeypatching and makes async context management explicit.

6. **FastAPI SSE with `asyncio.Queue` + a `None` sentinel for stream termination is a solid pattern.** The generator yields from the queue and exits cleanly when it receives `None`.

---

## Process Lessons

1. **Every library version needs live verification before use.** A dedicated version-checker agent (with web search) should run before code generation and update all package versions to current compatible releases.

2. **The template-based approach failed because templates are static code with holes.** They cannot adapt to app-specific patterns, cannot be tested independently, and accumulate technical debt rapidly. Any non-trivial variation requires a new template or increasingly complex conditional logic.

3. **Fully agentic generation is more robust.** Claude writing each file from scratch can adapt to context, use patterns from a curated library, and handle edge cases that templates structurally cannot.
