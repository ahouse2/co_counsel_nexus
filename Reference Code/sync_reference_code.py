"""Synchronise upstream reference repositories declared in catalog.yaml.

Usage
-----
python Reference Code/sync_reference_code.py --dest Reference Code/vendor

The script performs shallow clones when possible and always checks out the
revision recorded in the catalog to guarantee reproducibility.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

CATALOG_DEFAULT = Path(__file__).with_name("catalog.yaml")


class CatalogError(RuntimeError):
    """Raised when the catalog is invalid or cannot be parsed."""


@dataclass
class Source:
    name: str
    repo: str
    revision: str
    license: str
    destination: Path
    description: str


def load_catalog(path: Path) -> List[Source]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency hint path
        raise SystemExit(
            "PyYAML is required to parse the catalog. Install it with `pip install pyyaml`."
        ) from exc

    if not path.exists():
        raise CatalogError(f"Catalog file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh)

    if not payload or "sources" not in payload:
        raise CatalogError("Catalog must define a top-level 'sources' list")

    sources: List[Source] = []
    for idx, raw in enumerate(payload["sources"], start=1):
        try:
            destination = Path(raw["destination"])
            source = Source(
                name=str(raw["name"]),
                repo=str(raw["repo"]),
                revision=str(raw["revision"]),
                license=str(raw["license"]),
                destination=destination,
                description=str(raw.get("description", "")),
            )
        except KeyError as exc:
            raise CatalogError(f"Catalog entry #{idx} missing field: {exc}") from exc
        sources.append(source)

    return sources


def run_git(args: Iterable[str], cwd: Path | None = None) -> None:
    command = ["git", *args]
    proc = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        raise RuntimeError(
            "Git command failed:\n"
            f"  cwd: {cwd or Path.cwd()}\n  command: {' '.join(command)}\n"
            f"  stdout: {stdout}\n  stderr: {stderr}"
        )


def ensure_repo(source: Source, base_dest: Path, shallow: bool = True) -> None:
    destination = base_dest / source.destination
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        # Refresh existing clone.
        run_git(["fetch", "origin", source.revision], cwd=destination)
    else:
        clone_args = ["clone", source.repo, str(destination)]
        if shallow:
            clone_args.insert(1, "--depth")
            clone_args.insert(2, "1")
        run_git(clone_args)

    # Checkout requested revision and ensure working tree is clean.
    run_git(["checkout", source.revision], cwd=destination)
    run_git(["reset", "--hard", source.revision], cwd=destination)


def sync_sources(sources: Iterable[Source], dest: Path, no_shallow: bool) -> None:
    for source in sources:
        print(f"Synchronising {source.name} → {dest / source.destination}")
        ensure_repo(source, dest, shallow=not no_shallow)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=CATALOG_DEFAULT,
        help="Path to catalog.yaml (default: alongside this script)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("Reference Code/vendor"),
        help="Directory where upstream repositories will be cloned",
    )
    parser.add_argument(
        "--no-shallow",
        action="store_true",
        help="Disable shallow clones (fetch full history)",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        sources = load_catalog(args.catalog)
        sync_sources(sources, args.dest, args.no_shallow)
    except CatalogError as exc:
        parser.error(str(exc))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
