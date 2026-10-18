# Verification — 2026-10-18

Software version: 2.1-harness. Source foundation: Gathin23/tv-vibehack at `9ef40c1de85b757cbf75dbea174a24b99a0e50a3`. Project: Android TV Harness. Android target: API 34; minimum: API 26.

## Passing checks

- 21 Python runtime tests, including read-only inventory/planning, protected package rejection, invalid input, plan expiry/integrity/drift/replay, partial-failure recovery, exact enabled-state restoration, crash recovery, offline recovery, pending-run refusal, silent-shell exit markers, component equivalence and APK lifecycle simulation.
- 2 Android JVM tests for valid workspace addresses and rejected executable/credential-bearing schemes.
- Gradle `assembleDebug testDebugUnitTest lintDebug`: successful. Lint has zero errors; upstream warnings about older dependency versions and resource/performance recommendations remain.
- Real stdio MCP process: initialize, notification handling, six tool schemas and unknown-tool rejection passed.
- APK inspection confirmed `com.gathin.tvhome`, version `2.1-harness`, target SDK 34, Android TV feature and Home/Leanback intents. Configured label: `@J.A.R.V.I.S.`.
- Isolated ARM64 Android TV 14 emulator: harness inventory, verified first APK installation, direct native activity launch, app discovery, visible button, D-pad focus and disconnected-button message observed. Screenshots are in `docs/`.
- The test installation was restored and the temporary emulator shut down.

## Observed limitation

The emulator's stock launcher declares HOME priority 2. Android's `set-home-activity` reports success and sets the HOME role holder, but resolution and the Home key still open the stock launcher. The harness detects the mismatch and returns `failed_rolled_back`; package/Home recovery was verified. Stock Home stays enabled. This build does not force Home selection by disabling the stock launcher. A TV's actual default-Home behavior must be evaluated separately before deployment.

The first upstream-targeted APK was blocked by Play Protect as targeting an older Android version. Target SDK 34 and modern package-discovery declarations corrected installation in the isolated emulator. No protection settings were disabled.

## Deferred checks

The owner's physical Android TV was never connected to, inventoried or changed. Physical remote, streaming apps, tuner/input behavior and vendor launcher selection remain untested. Hermes is not configured. Session/email access and a connected workspace handoff are deferred until a destination and integration task exist.

## Local artifact

`artifacts/android-tv-harness-debug.apk` is an installable debug build for testing, not a production signed release. SHA-256: `7dc08f8dee8327c574be5cf0679c29f1e429571b8b9d4c4fc6efa0afce16354a`.
