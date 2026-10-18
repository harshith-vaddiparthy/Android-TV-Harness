# Output contract

CLI stdout contains JSON; exit 1 marks failure, recovery required or missing dependencies. MCP wraps the same JSON in text content and `isError`. Plans contain `id`, timestamps, inventory, prior package states, steps and integrity hash. Runs contain `id`, `status`, plan, attempted actions, verified actions and recovery evidence; completed runs also include after-inventory.

States: `running`, `completed`, `failed`, `restoring`, `restored`, `failed_rolled_back`, `recovery_required`. An interrupted `running` or `restoring` run is unfinished and must be reconciled. Recovery records remain inspectable with `run ID`.

Report the observed status, local artifact path/ID, TV target, actual verification, unresolved capabilities and next required action. Keep personal device information out of public reports. Hardware completion requires real-device evidence and a check of the requested user journey. Local test/build success is software completion only.
