"""
CLI command for generating embeddings from existing dataset and citation data.
"""

import argparse
import logging
from pathlib import Path
from typing import Optional
import json
import time

from ..core.citation_utils import load_citations_from_json
from ..quality.confidence_scoring import SentenceTransformerModel
from ..embeddings.storage_manager import EmbeddingStorageManager


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def load_dataset_metadata(dataset_id: str, datasets_dir: Path) -> Optional[str]:
    """
    Load dataset metadata text for embedding generation.

    Args:
        dataset_id: BIDS dataset ID
        datasets_dir: Path to datasets directory

    Returns:
        Combined dataset metadata text or None if not found
    """
    dataset_file = datasets_dir / f"{dataset_id}_datasets.json"

    if not dataset_file.exists():
        logging.warning(f"Dataset metadata not found: {dataset_file}")
        return None

    try:
        with open(dataset_file, "r") as f:
            dataset_data = json.load(f)

        # Combine relevant metadata fields
        metadata_parts = []

        if "description" in dataset_data:
            metadata_parts.append(dataset_data["description"])

        if "readme_content" in dataset_data:
            metadata_parts.append(dataset_data["readme_content"])

        if "dataset_description" in dataset_data:
            desc = dataset_data["dataset_description"]
            if isinstance(desc, dict):
                for field in ["Name", "Description", "TaskName", "Instructions"]:
                    if field in desc:
                        metadata_parts.append(str(desc[field]))

        combined_text = " ".join(metadata_parts).strip()

        if not combined_text:
            logging.warning(f"No metadata text found for dataset {dataset_id}")
            return None

        logging.debug(
            f"Loaded {len(combined_text)} characters of metadata for {dataset_id}"
        )
        return combined_text

    except Exception as e:
        logging.error(f"Error loading dataset metadata for {dataset_id}: {e}")
        return None


def generate_dataset_embeddings(
    datasets_dir: Path,
    embeddings_dir: Path,
    model_name: str = "Qwen/Qwen3-Embedding-0.6B",
    batch_size: int = 10,
    force_regenerate: bool = False,
) -> int:
    """
    Generate embeddings for all datasets.

    Args:
        datasets_dir: Path to datasets directory
        embeddings_dir: Path to embeddings directory
        model_name: Sentence transformer model name
        batch_size: Number of datasets to process at once
        force_regenerate: Whether to regenerate existing embeddings

    Returns:
        Number of embeddings generated
    """
    logging.info("Starting dataset embedding generation...")

    # Initialize components
    storage_manager = EmbeddingStorageManager(embeddings_dir)
    model = SentenceTransformerModel(model_name=model_name)

    # Find all dataset files
    dataset_files = list(datasets_dir.glob("ds*_datasets.json"))
    total_datasets = len(dataset_files)

    if total_datasets == 0:
        logging.error(f"No dataset files found in {datasets_dir}")
        return 0

    logging.info(f"Found {total_datasets} dataset files")

    generated_count = 0
    skipped_count = 0

    # Process datasets in batches
    for i in range(0, total_datasets, batch_size):
        batch_files = dataset_files[i : i + batch_size]

        logging.info(
            f"Processing batch {i // batch_size + 1}/{(total_datasets + batch_size - 1) // batch_size}"
        )

        for dataset_file in batch_files:
            dataset_id = dataset_file.stem.replace("_datasets", "")

            # Check if embedding already exists
            if not force_regenerate:
                existing = storage_manager.registry.get_current_dataset_embedding(
                    dataset_id
                )
                if existing:
                    logging.debug(f"Skipping {dataset_id} - embedding already exists")
                    skipped_count += 1
                    continue

            # Load dataset metadata
            metadata_text = load_dataset_metadata(dataset_id, datasets_dir)
            if not metadata_text:
                logging.warning(f"Skipping {dataset_id} - no metadata available")
                continue

            try:
                # Generate embedding
                logging.info(f"Generating embedding for {dataset_id}")
                embedding = model.encode([metadata_text])[0]

                # Store embedding
                storage_manager.store_dataset_embedding(
                    dataset_id=dataset_id,
                    embedding=embedding,
                    content_sources={"combined_metadata": metadata_text},
                    model=model_name,
                    metadata={
                        "text_length": len(metadata_text),
                        "embedding_dim": len(embedding),
                    },
                )

                generated_count += 1
                logging.info(f"Generated embedding for {dataset_id}")

            except Exception as e:
                logging.error(f"Error generating embedding for {dataset_id}: {e}")
                continue

    logging.info(
        f"Dataset embedding generation complete: {generated_count} generated, {skipped_count} skipped"
    )
    return generated_count


def generate_citation_embeddings(
    citations_dir: Path,
    embeddings_dir: Path,
    model_name: str = "Qwen/Qwen3-Embedding-0.6B",
    batch_size: int = 50,
    force_regenerate: bool = False,
    min_confidence: float = 0.4,
) -> int:
    """
    Generate embeddings for all high-confidence citations.

    Args:
        citations_dir: Path to citations directory
        embeddings_dir: Path to embeddings directory
        model_name: Sentence transformer model name
        batch_size: Number of citations to process at once
        force_regenerate: Whether to regenerate existing embeddings
        min_confidence: Minimum confidence score for citations

    Returns:
        Number of embeddings generated
    """
    logging.info("Starting citation embedding generation...")

    # Initialize components
    storage_manager = EmbeddingStorageManager(embeddings_dir)
    model = SentenceTransformerModel(model_name=model_name)

    # Find all citation files
    citation_files = list((citations_dir / "json").glob("ds*_citations.json"))
    total_files = len(citation_files)

    if total_files == 0:
        logging.error(f"No citation files found in {citations_dir / 'json'}")
        return 0

    logging.info(f"Found {total_files} citation files")

    generated_count = 0
    skipped_count = 0
    batch_texts = []
    batch_metadata = []

    # Process all citation files
    for file_idx, citation_file in enumerate(citation_files):
        dataset_id = citation_file.stem.replace("_citations", "")

        try:
            # Load citations
            citations_data = load_citations_from_json(citation_file)

            if "citation_details" not in citations_data:
                logging.warning(f"No citation details in {citation_file}")
                continue

            # Process each citation
            for citation in citations_data["citation_details"]:
                # Check confidence score
                confidence = citation.get("confidence_score", 0.0)
                if confidence < min_confidence:
                    continue

                # Prepare citation text
                title = citation.get("title", "")
                abstract = citation.get("abstract", "")
                citation_text = f"{title} {abstract}".strip()

                if not citation_text:
                    continue

                # Generate citation hash for uniqueness
                import hashlib

                citation_hash = hashlib.sha256(citation_text.encode()).hexdigest()[:8]

                # Check if embedding already exists
                if not force_regenerate:
                    existing = storage_manager.registry.get_current_citation_embedding(
                        citation_hash
                    )
                    if existing:
                        skipped_count += 1
                        continue

                # Add to batch
                batch_texts.append(citation_text)
                batch_metadata.append(
                    {
                        "citation_hash": citation_hash,
                        "title": title,
                        "dataset_id": dataset_id,
                        "confidence_score": confidence,
                        "text_length": len(citation_text),
                    }
                )

                # Process batch when full
                if len(batch_texts) >= batch_size:
                    generated_count += process_citation_batch(
                        batch_texts, batch_metadata, model, storage_manager, model_name
                    )
                    batch_texts = []
                    batch_metadata = []

        except Exception as e:
            logging.error(f"Error processing citation file {citation_file}: {e}")
            continue

        # Progress logging
        if (file_idx + 1) % 10 == 0:
            logging.info(f"Processed {file_idx + 1}/{total_files} citation files")

    # Process remaining batch
    if batch_texts:
        generated_count += process_citation_batch(
            batch_texts, batch_metadata, model, storage_manager, model_name
        )

    logging.info(
        f"Citation embedding generation complete: {generated_count} generated, {skipped_count} skipped"
    )
    return generated_count


def process_citation_batch(
    batch_texts, batch_metadata, model, storage_manager, model_name
):
    """Process a batch of citations for embedding generation."""
    try:
        # Generate embeddings for batch
        logging.debug(
            f"Generating embeddings for batch of {len(batch_texts)} citations"
        )
        embeddings = model.encode(batch_texts)

        # Store each embedding
        batch_generated = 0
        for i, (embedding, metadata) in enumerate(zip(embeddings, batch_metadata)):
            try:
                storage_manager.store_citation_embedding(
                    citation_text=batch_texts[i],
                    title=metadata["title"],
                    embedding=embedding,
                    text_sources={"title_abstract": batch_texts[i]},
                    model=model_name,
                    metadata={
                        "dataset_id": metadata["dataset_id"],
                        "confidence_score": metadata["confidence_score"],
                        "text_length": metadata["text_length"],
                        "embedding_dim": len(embedding),
                    },
                )
                batch_generated += 1

            except Exception as e:
                logging.error(
                    f"Error storing embedding for citation {metadata['citation_hash']}: {e}"
                )

        logging.info(
            f"Generated {batch_generated}/{len(batch_texts)} embeddings in batch"
        )
        return batch_generated

    except Exception as e:
        logging.error(f"Error processing citation batch: {e}")
        return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for BIDS dataset citations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all embeddings
  dataset-citations-generate-embeddings --datasets datasets/ --citations citations/

  # Generate only dataset embeddings
  dataset-citations-generate-embeddings --datasets datasets/ --embedding-type datasets

  # Force regenerate with custom model
  dataset-citations-generate-embeddings --datasets datasets/ --citations citations/ \\
    --force-regenerate --model Qwen/Qwen3-Embedding-0.6B

  # Generate with higher confidence threshold
  dataset-citations-generate-embeddings --citations citations/ \\
    --min-confidence 0.6 --embedding-type citations
        """,
    )

    parser.add_argument(
        "--datasets",
        type=Path,
        default="datasets",
        help="Path to datasets directory (default: datasets)",
    )

    parser.add_argument(
        "--citations",
        type=Path,
        default="citations",
        help="Path to citations directory (default: citations)",
    )

    parser.add_argument(
        "--embeddings-dir",
        type=Path,
        default="embeddings",
        help="Path to embeddings storage directory (default: embeddings)",
    )

    parser.add_argument(
        "--embedding-type",
        choices=["datasets", "citations", "both"],
        default="both",
        help="Type of embeddings to generate (default: both)",
    )

    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-Embedding-0.6B",
        help="Sentence transformer model name (default: Qwen/Qwen3-Embedding-0.6B)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for processing (default: 50)",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.4,
        help="Minimum confidence score for citations (default: 0.4)",
    )

    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Force regeneration of existing embeddings",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Validate inputs
    if args.embedding_type in ["datasets", "both"] and not args.datasets.exists():
        logging.error(f"Datasets directory not found: {args.datasets}")
        return 1

    if args.embedding_type in ["citations", "both"] and not args.citations.exists():
        logging.error(f"Citations directory not found: {args.citations}")
        return 1

    # Create embeddings directory
    args.embeddings_dir.mkdir(parents=True, exist_ok=True)

    # Track total generated
    total_generated = 0
    start_time = time.time()

    try:
        # Generate dataset embeddings
        if args.embedding_type in ["datasets", "both"]:
            logging.info("=" * 60)
            logging.info("GENERATING DATASET EMBEDDINGS")
            logging.info("=" * 60)

            dataset_count = generate_dataset_embeddings(
                datasets_dir=args.datasets,
                embeddings_dir=args.embeddings_dir,
                model_name=args.model,
                batch_size=args.batch_size // 5,  # Smaller batch for datasets
                force_regenerate=args.force_regenerate,
            )
            total_generated += dataset_count

        # Generate citation embeddings
        if args.embedding_type in ["citations", "both"]:
            logging.info("=" * 60)
            logging.info("GENERATING CITATION EMBEDDINGS")
            logging.info("=" * 60)

            citation_count = generate_citation_embeddings(
                citations_dir=args.citations,
                embeddings_dir=args.embeddings_dir,
                model_name=args.model,
                batch_size=args.batch_size,
                force_regenerate=args.force_regenerate,
                min_confidence=args.min_confidence,
            )
            total_generated += citation_count

        # Final summary
        elapsed_time = time.time() - start_time
        logging.info("=" * 60)
        logging.info("EMBEDDING GENERATION COMPLETE")
        logging.info("=" * 60)
        logging.info(f"Total embeddings generated: {total_generated}")
        logging.info(f"Total time: {elapsed_time:.1f} seconds")

        # Show storage stats
        storage_manager = EmbeddingStorageManager(args.embeddings_dir)
        stats = storage_manager.get_storage_stats()
        logging.info(
            f"Storage stats: {stats['total_files']} files, {stats['total_file_size_mb']:.1f} MB"
        )

        return 0

    except Exception as e:
        logging.error(f"Error during embedding generation: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
