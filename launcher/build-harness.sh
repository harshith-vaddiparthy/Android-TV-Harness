#!/usr/bin/env bash
# Build only: device installation must use a harness plan.
set -euo pipefail
cd "$(dirname "$0")/.."
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
export ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
python3 -m harness configure config/launcher.json
cd launcher
./gradlew assembleDebug testDebugUnitTest lintDebug --console=plain
