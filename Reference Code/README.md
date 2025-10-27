# Reference Code Workspace

This workspace vendors upstream SDKs and tooling that our agents depend on. The files checked into Git describe **how** to obtain
and update those upstream sources — the upstream repositories themselves are not committed to keep this repo lightweight.

## Layout
- `catalog.yaml` — authoritative list of upstream repositories, revisions, and licensing metadata.
- `sync_reference_code.py` — automation script that performs shallow clones/updates for every catalog entry.
- `.gitignore` — ensures cloned repositories remain untracked.

## Usage
```bash
python Reference\ Code/sync_reference_code.py --dest Reference\ Code/vendor
```

The script will create the destination directory (default: `Reference Code/vendor`) and either clone or fetch every catalog entry.
It performs shallow clones (`--depth 1`) and pins the commit hash recorded in `catalog.yaml` to ensure reproducibility.

## Adding New Sources
1. Update `catalog.yaml` with the repository metadata and license.
2. Run the sync script to populate the source locally.
3. Review the upstream license before integrating code into this repository.

## License Compliance
Each catalog entry contains SPDX identifiers. Verify compatibility with our licensing policy before promoting code into
first-party packages. When in doubt, consult the legal/compliance team.
