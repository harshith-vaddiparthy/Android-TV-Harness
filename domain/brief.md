# Android TV home operations

Primary user: TV owner. Future caller: Hermes or another authorized agent. Execution: a host with native ADB and a paired TV. Product: the native Java tv-vibehack launcher plus one @J.A.R.V.I.S. button.

Inputs: one explicit ADB target, requested package changes or first-install APK/Home selection, and the launcher build profile. Outputs: a saved plan, a run with direct checks, and optional screenshot evidence. TV user profile is fixed to user 0.

TV capabilities and package dependencies vary across manufacturers. OS version alone does not establish third-party launcher support. Firmware flashing, rooting, system-app uninstall, network discovery and agent/email implementation are outside this harness.
