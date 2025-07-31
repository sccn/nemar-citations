"""
Embedding storage manager for file operations and embedding generation.
"""

import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime
import logging
import hashlib

from .embedding_registry import EmbeddingRegistry

logger = logging.getLogger(__name__)


class EmbeddingStorageManager:
    """
    Manager for embedding file storage, retrieval, and generation.

    Handles:
    - Saving and loading embedding files
    - Integration with EmbeddingRegistry
    - File naming conventions and directory structure
    - Batch operations for efficiency
    """

    def __init__(self, embeddings_dir: Union[str, Path]):
        """
        Initialize storage manager.

        Args:
            embeddings_dir: Path to embeddings directory
        """
        self.embeddings_dir = Path(embeddings_dir)
        self.registry = EmbeddingRegistry(embeddings_dir)

        # Create subdirectories
        self.dataset_dir = self.embeddings_dir / "dataset_embeddings"
        self.citation_dir = self.embeddings_dir / "citation_embeddings"
        self.composite_dir = self.embeddings_dir / "composite_embeddings"
        self.analysis_dir = self.embeddings_dir / "analysis"

        # Ensure directories exist
        for dir_path in [
            self.dataset_dir,
            self.citation_dir,
            self.composite_dir,
            self.analysis_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Create analysis subdirectories
        (self.analysis_dir / "umap_projections").mkdir(exist_ok=True)
        (self.analysis_dir / "clustering").mkdir(exist_ok=True)
        (self.composite_dir / "confidence_pairs").mkdir(exist_ok=True)

    def save_embedding(
        self, embedding: np.ndarray, file_path: Union[str, Path], compress: bool = True
    ) -> Path:
        """
        Save embedding to file with optional compression.

        Args:
            embedding: Numpy array containing embedding
            file_path: Path to save file (relative to embeddings_dir)
            compress: Whether to use compression

        Returns:
            Full path to saved file
        """
        full_path = self.embeddings_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Save with pickle and optional compression
        protocol = pickle.HIGHEST_PROTOCOL
        if compress:
            import gzip

            with gzip.open(full_path, "wb") as f:
                pickle.dump(embedding, f, protocol=protocol)
        else:
            with open(full_path, "wb") as f:
                pickle.dump(embedding, f, protocol=protocol)

        logger.debug(f"Saved embedding to: {full_path}")
        return full_path

    def load_embedding(self, file_path: Union[str, Path]) -> np.ndarray:
        """
        Load embedding from file.

        Args:
            file_path: Path to embedding file (relative to embeddings_dir)

        Returns:
            Numpy array containing embedding
        """
        full_path = self.embeddings_dir / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"Embedding file not found: {full_path}")

        # Try compressed format first, then uncompressed
        try:
            import gzip

            with gzip.open(full_path, "rb") as f:
                embedding = pickle.load(f)
        except (gzip.BadGzipFile, OSError, pickle.UnpicklingError):
            with open(full_path, "rb") as f:
                embedding = pickle.load(f)

        logger.debug(f"Loaded embedding from: {full_path}")
        return embedding

    def generate_dataset_filename(
        self, dataset_id: str, date: Optional[str] = None
    ) -> str:
        """
        Generate filename for dataset embedding.

        Args:
            dataset_id: BIDS dataset ID
            date: Date string (YYYYMMDD), defaults to today

        Returns:
            Filename string
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        # Get next version number
        current_embedding = self.registry.get_current_dataset_embedding(dataset_id)
        if current_embedding:
            version = current_embedding["version"] + 1
        else:
            version = 1

        return f"{dataset_id}_v{version}_{date}.pkl"

    def generate_citation_filename(
        self, citation_hash: str, date: Optional[str] = None
    ) -> str:
        """
        Generate filename for citation embedding.

        Args:
            citation_hash: Citation hash (first 8 chars of content hash)
            date: Date string (YYYYMMDD), defaults to today

        Returns:
            Filename string
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        # Get next version number
        current_embedding = self.registry.get_current_citation_embedding(citation_hash)
        if current_embedding:
            version = current_embedding["version"] + 1
        else:
            version = 1

        return f"citation_{citation_hash}_v{version}_{date}.pkl"

    def store_dataset_embedding(
        self,
        dataset_id: str,
        embedding: np.ndarray,
        content_sources: Dict[str, str],
        model: str = "Qwen/Qwen3-Embedding-0.6B",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Store dataset embedding with registry tracking.

        Args:
            dataset_id: BIDS dataset ID
            embedding: Embedding array
            content_sources: Dict mapping source files to content
            model: Embedding model used
            metadata: Additional metadata

        Returns:
            Registry record for the stored embedding
        """
        # Generate filename
        filename = self.generate_dataset_filename(dataset_id)
        file_path = f"dataset_embeddings/{filename}"

        # Save embedding file
        self.save_embedding(embedding, file_path)

        # Register in registry
        record = self.registry.register_dataset_embedding(
            dataset_id=dataset_id,
            embedding_file=file_path,
            content_sources=content_sources,
            model=model,
            metadata=metadata,
        )

        logger.info(f"Stored dataset embedding: {dataset_id} -> {file_path}")
        return record

    def store_citation_embedding(
        self,
        citation_text: str,
        title: str,
        embedding: np.ndarray,
        text_sources: Dict[str, str],
        model: str = "Qwen/Qwen3-Embedding-0.6B",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Store citation embedding with registry tracking.

        Args:
            citation_text: Full citation text (title + abstract)
            title: Citation title
            embedding: Embedding array
            text_sources: Dict mapping text source types to content
            model: Embedding model used
            metadata: Additional metadata

        Returns:
            Registry record for the stored embedding
        """
        # Generate citation hash
        citation_hash = hashlib.sha256(citation_text.encode()).hexdigest()[:8]

        # Generate filename
        filename = self.generate_citation_filename(citation_hash)
        file_path = f"citation_embeddings/{filename}"

        # Save embedding file
        self.save_embedding(embedding, file_path)

        # Register in registry
        record = self.registry.register_citation_embedding(
            citation_hash=citation_hash,
            title=title,
            embedding_file=file_path,
            text_sources=text_sources,
            model=model,
            metadata=metadata,
        )

        logger.info(f"Stored citation embedding: {citation_hash} -> {file_path}")
        return record

    def store_composite_embedding(
        self,
        dataset_id: str,
        citation_hash: str,
        embedding: np.ndarray,
        confidence_score: float,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Store composite embedding for dataset-citation confidence scoring.

        Args:
            dataset_id: BIDS dataset ID
            citation_hash: Citation hash
            embedding: Combined embedding array
            confidence_score: Calculated confidence score
            metadata: Additional metadata

        Returns:
            Path to stored file
        """
        # Generate filename
        filename = f"{dataset_id}_cite{citation_hash}_v1.pkl"
        file_path = f"composite_embeddings/confidence_pairs/{filename}"

        # Prepare data to store
        composite_data = {
            "embedding": embedding,
            "confidence_score": confidence_score,
            "dataset_id": dataset_id,
            "citation_hash": citation_hash,
            "created": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        # Save composite data
        full_path = self.embeddings_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            pickle.dump(composite_data, f, protocol=pickle.HIGHEST_PROTOCOL)

        logger.info(
            f"Stored composite embedding: {dataset_id} + {citation_hash} -> {file_path}"
        )
        return file_path

    def load_dataset_embedding(
        self, dataset_id: str, version: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """
        Load dataset embedding by ID.

        Args:
            dataset_id: BIDS dataset ID
            version: Specific version to load (defaults to current)

        Returns:
            Embedding array or None if not found
        """
        if version is None:
            # Get current version
            embedding_info = self.registry.get_current_dataset_embedding(dataset_id)
        else:
            # Get specific version
            embedding_info = None
            if dataset_id in self.registry.registry["datasets"]:
                for emb in self.registry.registry["datasets"][dataset_id]["embeddings"]:
                    if emb["version"] == version:
                        embedding_info = emb
                        break

        if not embedding_info:
            logger.warning(f"No embedding found for dataset {dataset_id}")
            return None

        try:
            return self.load_embedding(embedding_info["file"])
        except FileNotFoundError:
            logger.error(f"Embedding file not found: {embedding_info['file']}")
            return None

    def load_citation_embedding(
        self, citation_hash: str, version: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """
        Load citation embedding by hash.

        Args:
            citation_hash: Citation hash ID
            version: Specific version to load (defaults to current)

        Returns:
            Embedding array or None if not found
        """
        if version is None:
            # Get current version
            embedding_info = self.registry.get_current_citation_embedding(citation_hash)
        else:
            # Get specific version
            embedding_info = None
            if citation_hash in self.registry.registry["citations"]:
                for emb in self.registry.registry["citations"][citation_hash][
                    "embeddings"
                ]:
                    if emb["version"] == version:
                        embedding_info = emb
                        break

        if not embedding_info:
            logger.warning(f"No embedding found for citation {citation_hash}")
            return None

        try:
            return self.load_embedding(embedding_info["file"])
        except FileNotFoundError:
            logger.error(f"Embedding file not found: {embedding_info['file']}")
            return None

    def get_all_current_embeddings(
        self, embedding_type: str = "both"
    ) -> Dict[str, np.ndarray]:
        """
        Load all current embeddings of specified type.

        Args:
            embedding_type: 'datasets', 'citations', or 'both'

        Returns:
            Dict mapping IDs to embedding arrays
        """
        embeddings = {}

        if embedding_type in ["datasets", "both"]:
            for dataset_id in self.registry.registry["datasets"]:
                emb = self.load_dataset_embedding(dataset_id)
                if emb is not None:
                    embeddings[f"dataset_{dataset_id}"] = emb

        if embedding_type in ["citations", "both"]:
            for citation_hash in self.registry.registry["citations"]:
                emb = self.load_citation_embedding(citation_hash)
                if emb is not None:
                    embeddings[f"citation_{citation_hash}"] = emb

        return embeddings

    def cleanup_obsolete_embeddings(
        self, dry_run: bool = True, older_than_days: int = 90
    ) -> Dict[str, List[str]]:
        """
        Clean up obsolete embedding files.

        Args:
            dry_run: If True, only report what would be deleted
            older_than_days: Only delete embeddings older than this many days

        Returns:
            Dict with lists of deleted (or would-be-deleted) files
        """
        obsolete = self.registry.check_obsolete_embeddings()
        deleted = {"datasets": [], "citations": [], "analysis": []}

        for category, files in obsolete.items():
            for file_desc in files:
                # Parse file description to get file path
                if ":" in file_desc:
                    item_id, file_path = file_desc.split(": ", 1)
                    full_path = self.embeddings_dir / file_path

                    if full_path.exists():
                        # Check age
                        file_age = (
                            datetime.now().timestamp() - full_path.stat().st_mtime
                        ) / (24 * 3600)

                        if file_age > older_than_days:
                            if not dry_run:
                                full_path.unlink()
                                logger.info(f"Deleted obsolete embedding: {file_path}")
                            deleted[category].append(file_path)

        if dry_run:
            logger.info(
                f"Dry run: would delete {sum(len(files) for files in deleted.values())} obsolete embedding files"
            )
        else:
            logger.info(
                f"Deleted {sum(len(files) for files in deleted.values())} obsolete embedding files"
            )

        return deleted

    def get_storage_stats(self) -> Dict:
        """
        Get storage statistics.

        Returns:
            Dict with storage statistics
        """
        stats = self.registry.get_registry_stats()

        # Add file system stats
        total_size = 0
        file_count = 0

        for directory in [
            self.dataset_dir,
            self.citation_dir,
            self.composite_dir,
            self.analysis_dir,
        ]:
            if directory.exists():
                for file_path in directory.rglob("*.pkl"):
                    total_size += file_path.stat().st_size
                    file_count += 1

        stats.update(
            {
                "total_file_size_mb": total_size / (1024 * 1024),
                "total_files": file_count,
                "directories": {
                    "dataset_embeddings": len(list(self.dataset_dir.glob("*.pkl")))
                    if self.dataset_dir.exists()
                    else 0,
                    "citation_embeddings": len(list(self.citation_dir.glob("*.pkl")))
                    if self.citation_dir.exists()
                    else 0,
                    "composite_embeddings": len(list(self.composite_dir.rglob("*.pkl")))
                    if self.composite_dir.exists()
                    else 0,
                    "analysis": len(list(self.analysis_dir.rglob("*.pkl")))
                    if self.analysis_dir.exists()
                    else 0,
                },
            }
        )

        return stats
