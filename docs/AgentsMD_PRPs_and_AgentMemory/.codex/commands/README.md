# Command Catalog

Automation commands standardise repeatable operational tasks (syncing reference assets, validating docs, etc.). Each manifest in
this directory is a YAML document with the following fields:

- `name` — unique command identifier.
- `description` — concise summary of the action performed.
- `tags` — list of discovery keywords.
- `env` — required environment variables (if any) with rationale.
- `steps` — ordered shell commands executed from repository root.
- `artifacts` — optional outputs to capture for audit trails.

To execute a command manually:

```bash
./tools/run_command.sh docs/AgentsMD_PRPs_and_AgentMemory/.codex/commands/sync-reference-assets.yaml
```

The helper script `tools/run_command.sh` is expected to:
1. Parse the manifest.
2. Export required environment variables.
3. Execute each step, aborting on failure.
4. Persist declared artifacts.

> _Note_: The helper script is not yet implemented in this repository. Until it exists, run the `steps` entries manually.

## Rapid-Development Experiments

- [`rapid-development/experimental/prp-analyze-run.md`](rapid-development/experimental/prp-analyze-run.md) — structured notes template for logging outcomes after executing rapid-development commands or ACE validation runs.
