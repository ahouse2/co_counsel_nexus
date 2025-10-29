import argparse
import json
from pathlib import Path
from typing import Callable

from backend.app.config import get_settings
from backend.app.storage.forensics_chain import ForensicsChainLedger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify the forensic chain-of-custody ledger")
    parser.add_argument(
        "--path",
        type=str,
        help="Optional ledger path override; defaults to configured forensics chain path",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit verification summary as JSON",
    )
    return parser


def _load_ledger(path: Path | None) -> ForensicsChainLedger:
    settings = get_settings()
    ledger_path = Path(path) if path else settings.forensics_chain_path
    return ForensicsChainLedger(ledger_path)


def main(argv: list[str] | None = None, *, ledger_factory: Callable[[Path | None], ForensicsChainLedger] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    factory = ledger_factory or _load_ledger
    ledger = factory(Path(args.path) if args.path else None)
    ok, issues = ledger.verify()
    entries = list(ledger.iter_entries())
    summary = {
        "path": str(ledger.path),
        "entries": len(entries),
        "ok": ok,
        "issues": issues,
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        status = "verified" if ok else "FAILED"
        detail = f"issues={len(issues)}" if issues else ""
        print(f"Ledger {status}: path={summary['path']} entries={summary['entries']} {detail}".strip())
    return 0 if ok else 2


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
