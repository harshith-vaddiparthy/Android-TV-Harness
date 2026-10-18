# Readiness and recovery

## Pairing

Enable Developer options and debugging on the TV. Android TV 14 commonly uses separate wireless pairing and connection ports, shown on the TV; they can change. Keep pairing codes out of logs and repository files.

```bash
adb pair TV_ADDRESS:PAIRING_PORT
adb connect TV_ADDRESS:CONNECTION_PORT
adb devices
python3 -m harness --serial TV_ADDRESS:CONNECTION_PORT inventory
```

ADB prompts for the code interactively. Older network-debugging devices may use port 5555 and an on-screen “Allow debugging” prompt. Connect only to the specified TV. The upstream pure-Python transport does not implement modern wireless TLS pairing; it is not used by this harness.

Run `python3 -m harness doctor` for binaries. On macOS put the installed JDK 17 in `JAVA_HOME` or let the harness use the Homebrew JDK for APK inspection. `launcher/build-harness.sh` sets local build environment variables without editing shell profiles or global model settings.

## Evidence

`.state/plans/` stores snapshots; `.state/runs/` stores action/recovery journals; `.state/screenshots/` stores PNGs. They may contain private device identifiers and app lists. Preserve access restrictions and exclude them from version control. The local runtime lock prevents simultaneous harness writes; it does not coordinate independent ADB users or multiple hosts.

## Interrupted or failed writes

Read the recorded run with `python3 -m harness run ID`. A timeout may have changed the TV even without a confirmed response. The attempted action is retained before every write.

```bash
python3 -m harness --serial ORIGINAL_TARGET restore ID
```

Restore is retryable: it returns already restored runs and rechecks unfinished recovery. It resets exact enabled-state integers, restores original Home when changed, and removes a newly installed launcher. It does not restore app data, firmware, arbitrary system settings or prior APK versions. Those actions are not in the runtime's supported write set.

If the original target cannot be reached, the record remains `recovery_required`. Reconnect the same target or reestablish its address and identity carefully; the current implementation binds recovery to both identity and serial, so changed ports require an explicit operator reconciliation rather than silently retargeting a run.

## TV acceptance

Observe Home returning to the new launcher; use the D-pad to reach @J.A.R.V.I.S., Inputs, Wi-Fi, Settings and the dock. Test the requested streaming apps. With no workspace connected, clicking @J.A.R.V.I.S. must show the short disconnected message. With a future configured destination, observe the existing app/browser opening and returning to the button.

A screenshot taken during HDMI/Live TV may be unavailable. The harness reports an invalid PNG rather than treating an empty file as proof. Navigate Home with the remote and capture again if that is within the task.
