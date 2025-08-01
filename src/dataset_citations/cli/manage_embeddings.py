"""
CLI command for embedding management and maintenance operations.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict
import json
import time

from ..embeddings.storage_manager import EmbeddingStorageManager


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def show_embedding_stats(embeddings_dir: Path) -> Dict:
    """
    Display comprehensive embedding statistics.

    Args:
        embeddings_dir: Path to embeddings directory

    Returns:
        Statistics dictionary
    """
    logging.info("Gathering embedding statistics...")

    storage_manager = EmbeddingStorageManager(embeddings_dir)
    registry_stats = storage_manager.registry.get_registry_stats()
    storage_stats = storage_manager.get_storage_stats()

    # Combine statistics
    combined_stats = {**registry_stats, **storage_stats}

    # Display formatted statistics
    print("\n" + "=" * 60)
    print("EMBEDDING STORAGE STATISTICS")
    print("=" * 60)

    print("📊 Registry Overview:")
    print(f"   • Total datasets tracked: {registry_stats['total_datasets']}")
    print(f"   • Total citations tracked: {registry_stats['total_citations']}")
    print(f"   • Total embeddings: {registry_stats['total_embeddings']}")
    print(f"   • Current embeddings: {registry_stats['current_embeddings']}")
    print(f"   • Obsolete embeddings: {registry_stats['obsolete_embeddings']}")
    print(f"   • Analysis files: {registry_stats['analysis_files']}")

    print("\n💾 Storage Overview:")
    print(f"   • Total files: {storage_stats['total_files']}")
    print(f"   • Total size: {storage_stats['total_file_size_mb']:.1f} MB")
    print(
        f"   • Dataset embeddings: {storage_stats['directories']['dataset_embeddings']}"
    )
    print(
        f"   • Citation embeddings: {storage_stats['directories']['citation_embeddings']}"
    )
    print(
        f"   • Composite embeddings: {storage_stats['directories']['composite_embeddings']}"
    )
    print(f"   • Analysis files: {storage_stats['directories']['analysis']}")

    # Show obsolete embeddings if any
    obsolete = storage_manager.registry.check_obsolete_embeddings()
    if any(obsolete.values()):
        print("\n🧹 Cleanup Opportunities:")
        for category, items in obsolete.items():
            if items:
                print(f"   • {category.title()}: {len(items)} obsolete embeddings")

    print("=" * 60)
    return combined_stats


def check_embedding_health(embeddings_dir: Path) -> Dict:
    """
    Check health of embedding storage system.

    Args:
        embeddings_dir: Path to embeddings directory

    Returns:
        Health check results
    """
    logging.info("Running embedding health check...")

    storage_manager = EmbeddingStorageManager(embeddings_dir)
    health_results = {
        "errors": [],
        "warnings": [],
        "info": [],
        "missing_files": [],
        "orphaned_files": [],
        "status": "healthy",
    }

    # Check registry file integrity
    try:
        registry = storage_manager.registry
        registry_data = registry.registry
        health_results["info"].append("Registry file loaded successfully")
    except Exception as e:
        health_results["errors"].append(f"Registry file error: {e}")
        health_results["status"] = "error"
        return health_results

    # Check for missing embedding files
    for dataset_id, dataset_info in registry_data["datasets"].items():
        for emb in dataset_info["embeddings"]:
            if emb["status"] == "current":
                file_path = embeddings_dir / emb["file"]
                if not file_path.exists():
                    health_results["missing_files"].append(emb["file"])
                    health_results["errors"].append(
                        f"Missing dataset embedding: {emb['file']}"
                    )

    for citation_hash, citation_info in registry_data["citations"].items():
        for emb in citation_info["embeddings"]:
            if emb["status"] == "current":
                file_path = embeddings_dir / emb["file"]
                if not file_path.exists():
                    health_results["missing_files"].append(emb["file"])
                    health_results["errors"].append(
                        f"Missing citation embedding: {emb['file']}"
                    )

    # Check for orphaned files (files not in registry)
    registered_files = set()
    for dataset_info in registry_data["datasets"].values():
        for emb in dataset_info["embeddings"]:
            registered_files.add(emb["file"])

    for citation_info in registry_data["citations"].values():
        for emb in citation_info["embeddings"]:
            registered_files.add(emb["file"])

    # Scan actual files
    for directory in [
        "dataset_embeddings",
        "citation_embeddings",
        "composite_embeddings",
    ]:
        dir_path = embeddings_dir / directory
        if dir_path.exists():
            for file_path in dir_path.rglob("*.pkl"):
                relative_path = str(file_path.relative_to(embeddings_dir))
                if relative_path not in registered_files:
                    health_results["orphaned_files"].append(relative_path)
                    health_results["warnings"].append(f"Orphaned file: {relative_path}")

    # Set overall status
    if health_results["errors"]:
        health_results["status"] = "error"
    elif health_results["warnings"]:
        health_results["status"] = "warning"

    # Display results
    print("\n" + "=" * 60)
    print("EMBEDDING HEALTH CHECK")
    print("=" * 60)

    status_emoji = {"healthy": "✅", "warning": "⚠️", "error": "❌"}

    print(
        f"{status_emoji[health_results['status']]} Overall Status: {health_results['status'].upper()}"
    )

    if health_results["errors"]:
        print(f"\n❌ Errors ({len(health_results['errors'])}):")
        for error in health_results["errors"]:
            print(f"   • {error}")

    if health_results["warnings"]:
        print(f"\n⚠️  Warnings ({len(health_results['warnings'])}):")
        for warning in health_results["warnings"]:
            print(f"   • {warning}")

    if health_results["info"]:
        print("\n✅ Info:")
        for info in health_results["info"]:
            print(f"   • {info}")

    print("=" * 60)
    return health_results


def cleanup_obsolete_embeddings(
    embeddings_dir: Path, older_than_days: int = 90, dry_run: bool = True
) -> Dict:
    """
    Clean up obsolete embeddings.

    Args:
        embeddings_dir: Path to embeddings directory
        older_than_days: Only clean files older than this many days
        dry_run: If True, only show what would be deleted

    Returns:
        Cleanup results
    """
    storage_manager = EmbeddingStorageManager(embeddings_dir)

    action = "Would delete" if dry_run else "Deleting"
    logging.info(f"{action} obsolete embeddings older than {older_than_days} days...")

    # Perform cleanup
    deleted_files = storage_manager.cleanup_obsolete_embeddings(
        dry_run=dry_run, older_than_days=older_than_days
    )

    # Display results
    print("\n" + "=" * 60)
    print(f"EMBEDDING CLEANUP {'(DRY RUN)' if dry_run else ''}")
    print("=" * 60)

    total_deleted = sum(len(files) for files in deleted_files.values())

    if total_deleted == 0:
        print("✅ No obsolete embeddings found for cleanup")
    else:
        print(f"🧹 {action} {total_deleted} obsolete embedding files:")

        for category, files in deleted_files.items():
            if files:
                print(f"\n{category.title()} ({len(files)} files):")
                for file_path in files:
                    print(f"   • {file_path}")

    if dry_run and total_deleted > 0:
        print("\n💡 To actually delete these files, run with --execute")

    print("=" * 60)
    return deleted_files


def export_embedding_metadata(embeddings_dir: Path, output_file: Path) -> Dict:
    """
    Export embedding metadata for external analysis.

    Args:
        embeddings_dir: Path to embeddings directory
        output_file: Output file path

    Returns:
        Export results
    """
    logging.info(f"Exporting embedding metadata to {output_file}")

    storage_manager = EmbeddingStorageManager(embeddings_dir)
    registry = storage_manager.registry.registry

    # Prepare export data
    export_data = {
        "metadata": {
            "export_timestamp": time.time(),
            "embeddings_dir": str(embeddings_dir),
            "registry_version": registry["metadata"]["version"],
            "last_updated": registry["metadata"]["last_updated"],
        },
        "statistics": storage_manager.get_storage_stats(),
        "datasets": {},
        "citations": {},
        "analysis": registry["analysis"],
    }

    # Export dataset embeddings info
    for dataset_id, dataset_info in registry["datasets"].items():
        current_emb = None
        for emb in dataset_info["embeddings"]:
            if emb["status"] == "current":
                current_emb = emb
                break

        export_data["datasets"][dataset_id] = {
            "current_version": dataset_info["current_version"],
            "total_versions": len(dataset_info["embeddings"]),
            "current_embedding": current_emb,
            "has_obsolete": any(
                emb["status"] == "obsolete" for emb in dataset_info["embeddings"]
            ),
        }

    # Export citation embeddings info
    for citation_hash, citation_info in registry["citations"].items():
        current_emb = None
        for emb in citation_info["embeddings"]:
            if emb["status"] == "current":
                current_emb = emb
                break

        export_data["citations"][citation_hash] = {
            "title": citation_info["title"],
            "current_version": citation_info["current_version"],
            "total_versions": len(citation_info["embeddings"]),
            "current_embedding": current_emb,
            "has_obsolete": any(
                emb["status"] == "obsolete" for emb in citation_info["embeddings"]
            ),
        }

    # Save export
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(export_data, f, indent=2, default=str)

    print(f"\n✅ Exported embedding metadata to: {output_file}")
    print(f"   • {len(export_data['datasets'])} datasets")
    print(f"   • {len(export_data['citations'])} citations")
    print(
        f"   • {len(export_data['analysis']['umap_projections']) + len(export_data['analysis']['clustering'])} analysis files"
    )

    return export_data


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage and maintain embedding storage system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show embedding statistics
  dataset-citations-manage-embeddings --stats

  # Check system health
  dataset-citations-manage-embeddings --health-check

  # Clean up obsolete embeddings (dry run)
  dataset-citations-manage-embeddings --cleanup --older-than 30

  # Actually delete obsolete embeddings
  dataset-citations-manage-embeddings --cleanup --older-than 90 --execute

  # Export metadata for analysis
  dataset-citations-manage-embeddings --export metadata_export.json

  # Combined health check and cleanup
  dataset-citations-manage-embeddings --health-check --cleanup --stats
        """,
    )

    parser.add_argument(
        "--embeddings-dir",
        type=Path,
        default="embeddings",
        help="Path to embeddings directory (default: embeddings)",
    )

    # Action options
    parser.add_argument(
        "--stats", action="store_true", help="Show embedding storage statistics"
    )

    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Run health check on embedding system",
    )

    parser.add_argument(
        "--cleanup", action="store_true", help="Clean up obsolete embeddings"
    )

    parser.add_argument(
        "--export", type=Path, help="Export embedding metadata to JSON file"
    )

    # Cleanup options
    parser.add_argument(
        "--older-than",
        type=int,
        default=90,
        help="Clean up files older than N days (default: 90)",
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform cleanup (default is dry run)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Validate inputs
    if not args.embeddings_dir.exists():
        logging.error(f"Embeddings directory not found: {args.embeddings_dir}")
        return 1

    # If no action specified, show stats by default
    if not any([args.stats, args.health_check, args.cleanup, args.export]):
        args.stats = True

    try:
        results = {}

        # Show statistics
        if args.stats:
            results["stats"] = show_embedding_stats(args.embeddings_dir)

        # Run health check
        if args.health_check:
            results["health"] = check_embedding_health(args.embeddings_dir)

        # Clean up obsolete embeddings
        if args.cleanup:
            results["cleanup"] = cleanup_obsolete_embeddings(
                embeddings_dir=args.embeddings_dir,
                older_than_days=args.older_than,
                dry_run=not args.execute,
            )

        # Export metadata
        if args.export:
            results["export"] = export_embedding_metadata(
                embeddings_dir=args.embeddings_dir, output_file=args.export
            )

        # Final summary
        if (
            len(
                [
                    action
                    for action in [
                        args.stats,
                        args.health_check,
                        args.cleanup,
                        args.export,
                    ]
                    if action
                ]
            )
            > 1
        ):
            print("\n" + "=" * 60)
            print("MANAGEMENT OPERATIONS COMPLETE")
            print("=" * 60)

        return 0

    except Exception as e:
        logging.error(f"Error during embedding management: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
