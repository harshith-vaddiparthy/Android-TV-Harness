# Primary workflow

1. Establish the requested TV target and exact desired change. Pairing needs an on-TV authorization; see the runbook. Finish when one authorized serial is available.
2. Run inventory. Finish when the TV feature, identity, installed packages and Home component are observed.
3. Configure and build the launcher if needed. Finish when profile validation, build, JVM tests and lint pass and the APK package ID is confirmed.
4. Create a plan from a JSON request. Review protected capabilities and exact action list within existing user authority. Finish when the saved plan represents only the request and its recovery snapshot is present.
5. Apply that plan ID. The runtime saves intent before each write and verifies the result. Finish only when the run status and all requested checks are known.
6. Capture the screen and check remote navigation, Home, inputs and streaming applications on the TV. Finish when the requested experience is observed; report untested items explicitly.
7. Preserve the run evidence. On failure or interruption, restore the run; finish when original states are verified or `recovery_required` describes the remaining blocker.
