"""
Embedding registry system for tracking embedding versions and metadata.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class EmbeddingRegistry:
    """
    Registry system for tracking embedding files, versions, and metadata.

    Manages the embedding_registry.json file and provides methods for:
    - Registering new embeddings
    - Checking for obsolete embeddings
    - Managing versions and content hashes
    - Tracking dependency relationships
    """

    def __init__(self, embeddings_dir: Union[str, Path]):
        """
        Initialize embedding registry.

        Args:
            embeddings_dir: Path to embeddings directory
        """
        self.embeddings_dir = Path(embeddings_dir)
        self.metadata_dir = self.embeddings_dir / "metadata"
        self.registry_file = self.metadata_dir / "embedding_registry.json"
        self.dataset_hashes_file = self.metadata_dir / "dataset_metadata_hashes.json"
        self.citation_hashes_file = self.metadata_dir / "citation_content_hashes.json"

        # Ensure directories exist
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        # Load or initialize registry
        self._load_registry()

    def _load_registry(self):
        """Load registry from JSON file or initialize empty registry."""
        if self.registry_file.exists():
            with open(self.registry_file, "r") as f:
                self.registry = json.load(f)
        else:
            self.registry = {
                "datasets": {},
                "citations": {},
                "analysis": {"umap_projections": [], "clustering": []},
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                },
            }
            self._save_registry()

    def _save_registry(self):
        """Save registry to JSON file."""
        self.registry["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(self.registry_file, "w") as f:
            json.dump(self.registry, f, indent=2)

    def generate_content_hash(self, content: str) -> str:
        """
        Generate SHA256 hash for content.

        Args:
            content: String content to hash

        Returns:
            First 16 characters of SHA256 hash
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def register_dataset_embedding(
        self,
        dataset_id: str,
        embedding_file: str,
        content_sources: Dict[str, str],
        model: str = "Qwen/Qwen3-Embedding-0.6B",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Register a new dataset embedding.

        Args:
            dataset_id: BIDS dataset ID (e.g., 'ds000117')
            embedding_file: Relative path to embedding file
            content_sources: Dict mapping source files to their content
            model: Embedding model used
            metadata: Additional metadata

        Returns:
            Dict with embedding registration details
        """
        # Generate content hash from all sources
        combined_content = "".join(content_sources.values())
        content_hash = self.generate_content_hash(combined_content)

        # Determine version number
        if dataset_id in self.registry["datasets"]:
            current_version = self.registry["datasets"][dataset_id]["current_version"]
            new_version = current_version + 1

            # Mark previous version as obsolete
            for emb in self.registry["datasets"][dataset_id]["embeddings"]:
                if emb["status"] == "current":
                    emb["status"] = "obsolete"
                    emb["obsoleted_by"] = embedding_file
                    emb["obsoleted_reason"] = "new version created"
                    emb["obsoleted_date"] = datetime.now().isoformat()
        else:
            new_version = 1
            self.registry["datasets"][dataset_id] = {
                "current_version": new_version,
                "embeddings": [],
            }

        # Create embedding record
        embedding_record = {
            "version": new_version,
            "file": embedding_file,
            "created": datetime.now().isoformat(),
            "content_hash": content_hash,
            "metadata_sources": list(content_sources.keys()),
            "model": model,
            "status": "current",
        }

        if metadata:
            embedding_record["metadata"] = metadata

        # Add to registry
        self.registry["datasets"][dataset_id]["embeddings"].append(embedding_record)
        self.registry["datasets"][dataset_id]["current_version"] = new_version

        # Update content hashes
        self._update_dataset_hashes(dataset_id, content_sources, content_hash)

        # Save registry
        self._save_registry()

        logger.info(f"Registered dataset embedding: {dataset_id} v{new_version}")
        return embedding_record

    def register_citation_embedding(
        self,
        citation_hash: str,
        title: str,
        embedding_file: str,
        text_sources: Dict[str, str],
        model: str = "Qwen/Qwen3-Embedding-0.6B",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Register a new citation embedding.

        Args:
            citation_hash: Unique hash for citation (first 8 chars of title+abstract hash)
            title: Citation title for reference
            embedding_file: Relative path to embedding file
            text_sources: Dict mapping text source types to content
            model: Embedding model used
            metadata: Additional metadata

        Returns:
            Dict with embedding registration details
        """
        # Generate content hash
        combined_content = "".join(text_sources.values())
        content_hash = self.generate_content_hash(combined_content)

        # Determine version number
        if citation_hash in self.registry["citations"]:
            current_version = self.registry["citations"][citation_hash][
                "current_version"
            ]
            new_version = current_version + 1
        else:
            new_version = 1
            self.registry["citations"][citation_hash] = {
                "current_version": new_version,
                "title": title,
                "embeddings": [],
            }

        # Create embedding record
        embedding_record = {
            "version": new_version,
            "file": embedding_file,
            "created": datetime.now().isoformat(),
            "content_hash": content_hash,
            "text_sources": list(text_sources.keys()),
            "model": model,
            "status": "current",
        }

        if metadata:
            embedding_record["metadata"] = metadata

        # Add to registry
        self.registry["citations"][citation_hash]["embeddings"].append(embedding_record)
        self.registry["citations"][citation_hash]["current_version"] = new_version

        # Update content hashes
        self._update_citation_hashes(citation_hash, text_sources, content_hash)

        # Save registry
        self._save_registry()

        logger.info(f"Registered citation embedding: {citation_hash} v{new_version}")
        return embedding_record

    def _update_dataset_hashes(
        self, dataset_id: str, content_sources: Dict[str, str], combined_hash: str
    ):
        """Update dataset content hashes."""
        # Load existing hashes
        if self.dataset_hashes_file.exists():
            with open(self.dataset_hashes_file, "r") as f:
                hashes = json.load(f)
        else:
            hashes = {}

        # Update hashes
        if dataset_id not in hashes:
            hashes[dataset_id] = {"history": []}

        # Add to history if hash changed
        if hashes[dataset_id].get("current_hash") != combined_hash:
            if "current_hash" in hashes[dataset_id]:
                hashes[dataset_id]["history"].append(
                    {
                        "hash": hashes[dataset_id]["current_hash"],
                        "date": hashes[dataset_id]["last_checked"],
                        "change_reason": "content updated",
                    }
                )

        hashes[dataset_id].update(
            {
                "current_hash": combined_hash,
                "last_checked": datetime.now().isoformat(),
                "content_sources": {
                    source: self.generate_content_hash(content)
                    for source, content in content_sources.items()
                },
            }
        )

        # Save hashes
        with open(self.dataset_hashes_file, "w") as f:
            json.dump(hashes, f, indent=2)

    def _update_citation_hashes(
        self, citation_hash: str, text_sources: Dict[str, str], combined_hash: str
    ):
        """Update citation content hashes."""
        # Load existing hashes
        if self.citation_hashes_file.exists():
            with open(self.citation_hashes_file, "r") as f:
                hashes = json.load(f)
        else:
            hashes = {}

        # Update hashes
        if citation_hash not in hashes:
            hashes[citation_hash] = {"history": []}

        hashes[citation_hash].update(
            {
                "current_hash": combined_hash,
                "last_checked": datetime.now().isoformat(),
                "text_sources": {
                    source: self.generate_content_hash(content)
                    for source, content in text_sources.items()
                },
            }
        )

        # Save hashes
        with open(self.citation_hashes_file, "w") as f:
            json.dump(hashes, f, indent=2)

    def get_current_dataset_embedding(self, dataset_id: str) -> Optional[Dict]:
        """
        Get current embedding info for a dataset.

        Args:
            dataset_id: BIDS dataset ID

        Returns:
            Dict with current embedding info or None if not found
        """
        if dataset_id not in self.registry["datasets"]:
            return None

        for emb in self.registry["datasets"][dataset_id]["embeddings"]:
            if emb["status"] == "current":
                return emb
        return None

    def get_current_citation_embedding(self, citation_hash: str) -> Optional[Dict]:
        """
        Get current embedding info for a citation.

        Args:
            citation_hash: Citation hash ID

        Returns:
            Dict with current embedding info or None if not found
        """
        if citation_hash not in self.registry["citations"]:
            return None

        for emb in self.registry["citations"][citation_hash]["embeddings"]:
            if emb["status"] == "current":
                return emb
        return None

    def check_obsolete_embeddings(self) -> Dict[str, List[str]]:
        """
        Check for obsolete embeddings that can be cleaned up.

        Returns:
            Dict with categories of obsolete embeddings
        """
        obsolete = {"datasets": [], "citations": [], "analysis": []}

        # Check dataset embeddings
        for dataset_id, dataset_info in self.registry["datasets"].items():
            for emb in dataset_info["embeddings"]:
                if emb["status"] == "obsolete":
                    # Check if older than grace period (30 days)
                    obsolete_date = datetime.fromisoformat(
                        emb.get("obsoleted_date", emb["created"])
                    )
                    days_old = (datetime.now() - obsolete_date).days
                    if days_old > 30:
                        obsolete["datasets"].append(f"{dataset_id}: {emb['file']}")

        # Check citation embeddings
        for citation_hash, citation_info in self.registry["citations"].items():
            for emb in citation_info["embeddings"]:
                if emb["status"] == "obsolete":
                    obsolete_date = datetime.fromisoformat(
                        emb.get("obsoleted_date", emb["created"])
                    )
                    days_old = (datetime.now() - obsolete_date).days
                    if days_old > 30:
                        obsolete["citations"].append(f"{citation_hash}: {emb['file']}")

        return obsolete

    def mark_as_obsolete(
        self, embedding_type: str, item_id: str, reason: str = "manual"
    ):
        """
        Mark an embedding as obsolete.

        Args:
            embedding_type: 'dataset' or 'citation'
            item_id: Dataset ID or citation hash
            reason: Reason for marking obsolete
        """
        if embedding_type == "dataset" and item_id in self.registry["datasets"]:
            for emb in self.registry["datasets"][item_id]["embeddings"]:
                if emb["status"] == "current":
                    emb["status"] = "obsolete"
                    emb["obsoleted_reason"] = reason
                    emb["obsoleted_date"] = datetime.now().isoformat()

        elif embedding_type == "citation" and item_id in self.registry["citations"]:
            for emb in self.registry["citations"][item_id]["embeddings"]:
                if emb["status"] == "current":
                    emb["status"] = "obsolete"
                    emb["obsoleted_reason"] = reason
                    emb["obsoleted_date"] = datetime.now().isoformat()

        self._save_registry()
        logger.info(f"Marked {embedding_type} {item_id} as obsolete: {reason}")

    def get_registry_stats(self) -> Dict:
        """
        Get statistics about the embedding registry.

        Returns:
            Dict with registry statistics
        """
        stats = {
            "total_datasets": len(self.registry["datasets"]),
            "total_citations": len(self.registry["citations"]),
            "total_embeddings": 0,
            "current_embeddings": 0,
            "obsolete_embeddings": 0,
            "analysis_files": len(self.registry["analysis"]["umap_projections"])
            + len(self.registry["analysis"]["clustering"]),
        }

        # Count dataset embeddings
        for dataset_info in self.registry["datasets"].values():
            for emb in dataset_info["embeddings"]:
                stats["total_embeddings"] += 1
                if emb["status"] == "current":
                    stats["current_embeddings"] += 1
                elif emb["status"] == "obsolete":
                    stats["obsolete_embeddings"] += 1

        # Count citation embeddings
        for citation_info in self.registry["citations"].values():
            for emb in citation_info["embeddings"]:
                stats["total_embeddings"] += 1
                if emb["status"] == "current":
                    stats["current_embeddings"] += 1
                elif emb["status"] == "obsolete":
                    stats["obsolete_embeddings"] += 1

        return stats
