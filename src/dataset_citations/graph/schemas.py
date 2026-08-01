"""Pydantic schemas for dataset citations graph database."""

from pydantic import BaseModel, ConfigDict


class Dataset(BaseModel):
    """BIDS dataset schema for graph database."""

    model_config = ConfigDict(extra="forbid")

    uid: str  # Dataset ID (e.g., ds000117)
    name: str  # Dataset name from dataset_description.json
    description: str | None = None  # Dataset description
    authors: list[str] | None = None  # Dataset authors
    num_citations: int = 0  # Direct citations to this dataset
    total_cumulative_citations: int = 0  # Sum of all citation impacts
    date_last_updated: str | None = None  # Last update from citations JSON
    bids_version: str | None = None  # BIDS specification version
    data_type: str | None = None  # Type of neuroimaging data
    modality: str | None = None  # Imaging modality (fMRI, EEG, etc.)


class Citation(BaseModel):
    """Research paper citation schema for graph database."""

    model_config = ConfigDict(extra="forbid")

    uid: str  # Unique identifier for this citation
    title: str  # Paper title
    author: str | None = None  # Primary author or authors string
    venue: str | None = None  # Journal or conference name
    year: int | None = None  # Publication year
    abstract: str | None = None  # Paper abstract
    cited_by: int = 0  # Number of times this paper is cited
    confidence_score: float | None = None  # Our confidence scoring (0.0-1.0)
    url: str | None = None  # Link to paper
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
    parameters: dict[str, str]  # Algorithm parameters
    clusters: dict[int, list[str]]  # Cluster ID -> List of citation/dataset UIDs
    silhouette_score: float | None = None
    davies_bouldin_score: float | None = None
    calinski_harabasz_score: float | None = None


class DimensionReductionResult(BaseModel):
    """Dimension reduction results schema."""

    model_config = ConfigDict(extra="forbid")

    method: str  # Method used (e.g., "UMAP")
    params: UMAPParams  # Parameters used
    item_uids: list[str]  # UIDs of items (citations/datasets)
    reduced_dimensions: list[list[float]]  # 2D coordinates


class ExtendedDataset(Dataset):
    """Dataset with analysis data for visualization."""

    model_config = ConfigDict(extra="forbid")

    # Embeddings from dataset metadata (description + README)
    embedding: list[float] | None = None

    # Clustering results
    kmeans_clusters: dict[str, int] | None = None
    dbscan_clusters: dict[str, int] | None = None
    agglomerative_clusters: dict[str, int] | None = None

    # Dimensionality reduction coordinates
    umap: list[float] | None = None
    tsne: list[float] | None = None
    pca: list[float] | None = None

    # Temporal analysis
    first_citation_year: int | None = None
    last_citation_year: int | None = None
    citation_years: list[int] | None = None


class ExtendedCitation(Citation):
    """Citation with analysis data for visualization."""

    model_config = ConfigDict(extra="forbid")

    # Embeddings from abstract and title
    embedding: list[float] | None = None

    # Clustering results (thematic groupings)
    kmeans_clusters: dict[str, int] | None = None
    dbscan_clusters: dict[str, int] | None = None
    agglomerative_clusters: dict[str, int] | None = None

    # Dimensionality reduction coordinates
    umap: list[float] | None = None
    tsne: list[float] | None = None
    pca: list[float] | None = None

    # Filtering criteria
    is_high_confidence: bool = False  # confidence_score >= 0.4
