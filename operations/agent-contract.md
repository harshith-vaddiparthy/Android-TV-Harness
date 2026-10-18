# Future agent contract

Hermes configuration is intentionally absent. The harness can be called through JSON CLI output or launched as a stdio MCP process from the repository working directory: `python3 -m harness mcp`.

| MCP tool | Effect | Required inputs |
| --- | --- | --- |
| tv_inventory | Read TV state | serial |
| tv_plan | Read TV and persist local plan | serial, request |
| tv_apply | Execute exact plan, verify, recover on failure | serial, id |
| tv_restore | Restore recorded original states | serial, id |
| tv_run | Read journal | id |
| tv_screenshot | Read framebuffer into private artifact | serial |

`tools/list` supplies JSON schemas. MCP uses newline-delimited JSON-RPC over stdio; no network listener or credentials are created. Protocol versions 2024-11-05, 2025-03-26 and 2025-06-18 are accepted. Tool errors set `isError` and include a structured failure string. The caller owns requester authentication, task authorization and displaying evidence to the owner.

The on-TV @J.A.R.V.I.S. button is separate from this tool transport: it launches a configured existing app or browser destination. The current build leaves that destination empty.
