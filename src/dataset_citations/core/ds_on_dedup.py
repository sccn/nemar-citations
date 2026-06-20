"""Deduplicate ds-*/on-* citation records (epic #180, phase 4, issue #126).

When an OpenNeuro `ds-*` dataset is imported into NEMAR it gains an `on-*`
catalog id, and the original `ds-*` accession survives only as the on-* row's
`source_id` (the standalone `ds-*` catalog row is dropped). From then on,
`dataset-citations-discover --source catalog` emits only the `on-*` id, so no
new duplicate is produced. But a `ds<N>_citations.json` written before the
mirror existed lingers on disk and double-counts: every downstream glob
(`find-mentions`, `score`, the dashboard aggregator) counts both the stale
`ds<N>` file and its `on<N>` replacement.

These pure functions identify those stale duplicates from the catalog so the
`dataset-citations-prune-mirrored` CLI can remove them. No I/O or network here;
the CLI owns catalog fetching and file deletion.
"""

from __future__ import annotations

from pathlib import Path

from dataset_citations.sources.nemar_catalog import CatalogRow


def ds_to_on_mirror_map(rows: list[CatalogRow]) -> dict[str, str]:
    """Map each mirrored `ds-*` accession to its `on-*` dataset id.

    Builds `{ds-alias: on-id}` from every catalog row that is an `on-*` dataset
    carrying a `ds-*` `source_id` (the OpenNeuro accession it was imported
    from). This is the inverse of the catalog's on->ds `source_id` link and is
    what marks a `ds-*` citation file as superseded by an `on-*` mirror.
    """
    mapping: dict[str, str] = {}
    for row in rows:
        source_id = row.source_id
        if (
            row.dataset_id.startswith("on")
            and isinstance(source_id, str)
            and source_id.startswith("ds")
        ):
            mapping[source_id] = row.dataset_id
    return mapping


def find_mirrored_duplicates(
    citations_dir: Path, ds_to_on: dict[str, str]
) -> list[Path]:
    """Return the `ds-*` citation files made redundant by an `on-*` mirror.

    A `ds<alias>_citations.json` is prunable only when BOTH it and its mirror
    `on<id>_citations.json` exist in `citations_dir`. Requiring the on-* file to
    be present is the safety invariant: the on-* record is the canonical
    replacement, so we never delete a `ds-*` record before its replacement is in
    place (a freshly mirrored dataset whose on-* citation JSON has not been
    produced yet keeps its ds-* file for one more cycle).

    Returns a sorted, deterministic list of paths.
    """
    duplicates: list[Path] = []
    for ds_alias, on_id in ds_to_on.items():
        ds_file = citations_dir / f"{ds_alias}_citations.json"
        on_file = citations_dir / f"{on_id}_citations.json"
        if ds_file.is_file() and on_file.is_file():
            duplicates.append(ds_file)
    return sorted(duplicates)
