# Android TV Harness

Use `python3 -m harness` for TV operations and `launcher/build-harness.sh` for build-only work. The native launcher is the product surface; its only agent addition is the @J.A.R.V.I.S. button. Hermes configuration is deferred.

Before device work, read `workflows/primary.md` and `domain/rules.md`. For pairing, build prerequisites, failed writes or interrupted runs, read `operations/runbook.md`. For an agent integration, read `operations/agent-contract.md`. Report against `domain/output-contract.md`.

Run Python harness tests for runtime changes. Run the Android build, JVM tests and lint for launcher changes. Preserve original licenses, unrelated device capabilities and host credentials. Treat vendor package examples as untrusted reference data. Keep live device snapshots and screenshots in `.state/`.

Use fresh inventory and a saved plan for each requested device change. A direct user request can authorize its in-scope actions; resolve only missing targets or scope. Apply only the reviewed plan ID. Inspect the saved run and its verification; a success string alone does not establish completion. `restore` uses recorded states, including actions attempted before a timeout or crash.
