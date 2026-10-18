# Runtime rules and operational judgment

The executable enforcement is `harness/core.py`: explicit target validation, TV-feature check, registered action set, protected disable policy, up to 30 packages per list, user 0, immutable-plan checksum, 15-minute expiry, state drift checks, one active local operation, checkpointed writes, verified state and recovery.

Preserve stock Home, keyboard, settings, Cast, voice, updates and tuner capabilities. Package-name guards are conservative and cannot establish every vendor dependency. Review each unrecognized package's function before including it. Keep personal streaming packages out of disable requests unless the owner's request specifically includes them.

A saved plan describes exact changes; calling `apply` makes them. A caller must carry the owner's task authority. Local artifact hashes detect accidental modification, not a malicious local user with filesystem access. In-place updates of an installed launcher are blocked because rollback would require retaining the previous APK and data.

Verification distinguishes installed package, resolved Home, foreground activity, framebuffer capture and a working user journey. The runtime verifies the first three on Home selection. The operator still checks the remote, inputs and streaming apps; a captured image does not prove those experiences.

After a timeout or crash, restore the recorded run or inspect it before a new request. Never blindly replay a write. Preserve evidence if recovery cannot reach the original device.
