# Acceptance rubric

The executable cases are in `tests/test_harness.py` and `launcher/app/src/test/`. Pass every Python case and Android JVM test. Build the APK and run lint. Verify output protocol with a real stdio process. Confirm the APK ID, Home intent and configured button label with apkanalyzer.

Release software criteria: read-only planning, rejected unsafe targets/actions, expired/tampered/drifted plan refusal, replay refusal, exact restoration, partial-failure recovery, crash journal recovery, original-device enforcement, launcher lifecycle recovery and restricted workspace targets all pass.

Hardware criteria: paired target inventory, install, Home resolution, foreground activity, D-pad navigation, streaming and optional workspace handoff have direct TV evidence. Mark each hardware criterion untested until observed. No synthetic test result establishes a physical TV installation.
