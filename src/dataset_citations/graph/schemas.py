"""Pydantic schemas for dataset citations graph database."""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class Dataset(BaseModel):
    """BIDS dataset schema for graph database."""

    model_config = ConfigDict(extra="forbid")

    uid: str  # Dataset ID (e.g., ds000117)
    name: str  # Dataset name from dataset_description.json
    description: Optional[str] = None  # Dataset description
    authors: Optional[List[str]] = None  # Dataset authors
    num_citations: int = 0  # Direct citations to this dataset
    total_cumulative_citations: int = 0  # Sum of all citation impacts
    date_last_updated: Optional[str] = None  # Last update from citations JSON
    bids_version: Optional[str] = None  # BIDS specification version
    data_type: Optional[str] = None  # Type of neuroimaging data
    modality: Optional[str] = None  # Imaging modality (fMRI, EEG, etc.)


class Citation(BaseModel):
    """Research paper citation schema for graph database."""

    model_config = ConfigDict(extra="forbid")

    uid: str  # Unique identifier for this citation
    title: str  # Paper title
    author: Optional[str] = None  # Primary author or authors string
    venue: Optional[str] = None  # Journal or conference name
    year: Optional[int] = None  # Publication year
    abstract: Optional[str] = None  # Paper abstract
    cited_by: int = 0  # Number of times this paper is cited
    confidence_score: Optional[float] = None  # Our confidence scoring (0.0-1.0)
    url: Optional[str] = None  # Link to paper
    dataset_id: str  # Which dataset this citation references


class Year(BaseModel):
    """Year node for temporal analysis."""

    model_config = ConfigDict(extra="forbid")

    value: int  # Year value (e.g., 2023)


class DatasetCitesCitation(BaseModel):
    """Relationship: Dataset is cited by Citation."""

    model_config = ConfigDict(extra="forbid")

    dataset_uid: str  # Dataset being cited
    citation_uid: str  # Citation that references the dataset


class CitationCitedInYear(BaseModel):
    """Relationship: Citation was published in Year."""

    model_config = ConfigDict(extra="forbid")

    citation_uid: str  # Citation being referenced
    year_value: int  # Year of publication


class UMAPParams(BaseModel):
    """UMAP parameters for dimensionality reduction."""

    n_neighbors: int = 15
    n_components: int = 2
    metric: str = "euclidean"
    min_dist: float = 0.1
    random_state: int = 42


class ClusterAnalysis(BaseModel):
    """Clustering analysis results schema."""

    model_config = ConfigDict(extra="forbid")

    algorithm: str  # Clustering algorithm used
    parameters: Dict[str, str]  # Algorithm parameters
    clusters: Dict[int, List[str]]  # Cluster ID -> List of citation/dataset UIDs
    silhouette_score: Optional[float] = None
    davies_bouldin_score: Optional[float] = None
    calinski_harabasz_score: Optional[float] = None


class DimensionReductionResult(BaseModel):
    """Dimension reduction results schema."""

    model_config = ConfigDict(extra="forbid")

    method: str  # Method used (e.g., "UMAP")
    params: UMAPParams  # Parameters used
    item_uids: List[str]  # UIDs of items (citations/datasets)
    reduced_dimensions: List[List[float]]  # 2D coordinates


class ExtendedDataset(Dataset):
    """Dataset with analysis data for visualization."""

    model_config = ConfigDict(extra="forbid")

    # Embeddings from dataset metadata (description + README)
    embedding: Optional[List[float]] = None

    # Clustering results
    kmeans_clusters: Optional[Dict[str, int]] = None
    dbscan_clusters: Optional[Dict[str, int]] = None
    agglomerative_clusters: Optional[Dict[str, int]] = None

    # Dimensionality reduction coordinates
    umap: Optional[List[float]] = None
    tsne: Optional[List[float]] = None
    pca: Optional[List[float]] = None

    # Temporal analysis
    first_citation_year: Optional[int] = None
    last_citation_year: Optional[int] = None
    citation_years: Optional[List[int]] = None


class ExtendedCitation(Citation):
    """Citation with analysis data for visualization."""

    model_config = ConfigDict(extra="forbid")

    # Embeddings from abstract and title
    embedding: Optional[List[float]] = None

    # Clustering results (thematic groupings)
    kmeans_clusters: Optional[Dict[str, int]] = None
    dbscan_clusters: Optional[Dict[str, int]] = None
    agglomerative_clusters: Optional[Dict[str, int]] = None

    # Dimensionality reduction coordinates
    umap: Optional[List[float]] = None
    tsne: Optional[List[float]] = None
    pca: Optional[List[float]] = None

    # Filtering criteria
    is_high_confidence: bool = False  # confidence_score >= 0.4
