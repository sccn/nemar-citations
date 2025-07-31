"""Neo4j loader functions for dataset citations graph database."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from neo4j import Driver, ManagedTransaction
from neo4j.exceptions import Neo4jError


logger = logging.getLogger(__name__)


def create_constraints(tx: ManagedTransaction) -> None:
    """
    Create constraints in the Neo4j database for dataset citations.

    Args:
        tx: A Neo4j transaction object
    """
    tx.run("CREATE CONSTRAINT FOR (d:Dataset) REQUIRE d.uid IS UNIQUE")
    tx.run("CREATE CONSTRAINT FOR (c:Citation) REQUIRE c.uid IS UNIQUE")
    tx.run("CREATE CONSTRAINT FOR (y:Year) REQUIRE y.value IS UNIQUE")


def create_indexes(tx: ManagedTransaction) -> None:
    """
    Create indexes in the Neo4j database for dataset citations.

    Args:
        tx: A Neo4j transaction object
    """
    tx.run("CREATE INDEX FOR (d:Dataset) ON (d.name)")
    tx.run("CREATE INDEX FOR (d:Dataset) ON (d.data_type)")
    tx.run("CREATE INDEX FOR (d:Dataset) ON (d.modality)")
    tx.run("CREATE INDEX FOR (c:Citation) ON (c.title)")
    tx.run("CREATE INDEX FOR (c:Citation) ON (c.year)")
    tx.run("CREATE INDEX FOR (c:Citation) ON (c.confidence_score)")
    tx.run("CREATE INDEX FOR (c:Citation) ON (c.dataset_id)")


def create_vector_index(
    driver: Driver,
    index_name: str,
    label: str,
    property_name: str,
    dimensions: int,
    similarity_function: str = "cosine",
) -> None:
    """
    Create a vector index in Neo4j for embedding searches.

    Args:
        driver: The Neo4j driver instance
        index_name: The name of the index
        label: The label of the nodes to index
        property_name: The name of the property containing the vector
        dimensions: The dimensionality of the vectors
        similarity_function: The similarity function to use
    """
    with driver.session() as session:
        session.run(
            f"""
            CREATE VECTOR INDEX {index_name} IF NOT EXISTS
            FOR (n:{label})
            ON n.{property_name}
            OPTIONS {{indexConfig: {{
                `vector.dimensions`: {dimensions},
                `vector.similarity_function`: '{similarity_function}'
            }}}}
        """
        )


def execute_query_with_logging(
    tx: ManagedTransaction, query: str, params: Optional[Dict] = None
) -> None:
    """
    Execute a Neo4j query with logging.

    Args:
        tx: The transaction object used to run the query
        query: The Cypher query to be executed
        params: Parameters for the query

    Raises:
        Neo4jError: If there is an error executing the query in Neo4j
    """
    try:
        result = tx.run(query, params or {})
        summary = result.consume()
        logger.debug(
            f"Query executed successfully. Affected records: {summary.counters}"
        )
    except Neo4jError as e:
        logger.error(f"Neo4j Error: {e.message}. Query: {query}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}. Query: {query}")
        raise


def batch_add_datasets(tx: ManagedTransaction, datasets: List[Dict]) -> None:
    """
    Batch add datasets to the Neo4j database.

    Args:
        tx: A Neo4j transaction object
        datasets: A list of dataset dictionaries
    """
    query = """
    UNWIND $datasets as dataset
    MERGE (d:Dataset {uid: dataset.uid})
    SET d.name = dataset.name,
        d.description = dataset.description,
        d.authors = dataset.authors,
        d.num_citations = dataset.num_citations,
        d.total_cumulative_citations = dataset.total_cumulative_citations,
        d.date_last_updated = dataset.date_last_updated,
        d.bids_version = dataset.bids_version,
        d.data_type = dataset.data_type,
        d.modality = dataset.modality
    """
    execute_query_with_logging(tx, query, {"datasets": datasets})


def batch_add_citations(tx: ManagedTransaction, citations: List[Dict]) -> None:
    """
    Batch add citations to the Neo4j database.

    Args:
        tx: A Neo4j transaction object
        citations: A list of citation dictionaries
    """
    query = """
    UNWIND $citations as citation
    MERGE (c:Citation {uid: citation.uid})
    SET c.title = citation.title,
        c.author = citation.author,
        c.venue = citation.venue,
        c.year = citation.year,
        c.abstract = citation.abstract,
        c.cited_by = citation.cited_by,
        c.confidence_score = citation.confidence_score,
        c.url = citation.url,
        c.dataset_id = citation.dataset_id,
        c.is_high_confidence = CASE 
            WHEN citation.confidence_score >= 0.4 THEN true 
            ELSE false 
        END
    """
    execute_query_with_logging(tx, query, {"citations": citations})


def batch_add_years(tx: ManagedTransaction, years: List[Dict]) -> None:
    """
    Batch add year nodes to the Neo4j database.

    Args:
        tx: A Neo4j transaction object
        years: A list of year dictionaries
    """
    query = """
    UNWIND $years as year
    MERGE (y:Year {value: year.value})
    """
    execute_query_with_logging(tx, query, {"years": years})


def batch_add_dataset_cites_citation(
    tx: ManagedTransaction, relationships: List[Dict]
) -> None:
    """
    Batch connect datasets to citations in the Neo4j database.

    Args:
        tx: A Neo4j transaction object
        relationships: A list of dataset-citation relationships
    """
    query = """
    UNWIND $relationships as rel
    MATCH (d:Dataset {uid: rel.dataset_uid}), (c:Citation {uid: rel.citation_uid})
    MERGE (d)-[:CITES]->(c)
    """
    execute_query_with_logging(tx, query, {"relationships": relationships})


def batch_add_citation_cited_in_year(
    tx: ManagedTransaction, relationships: List[Dict]
) -> None:
    """
    Batch connect citations to years in the Neo4j database.

    Args:
        tx: A Neo4j transaction object
        relationships: A list of citation-year relationships
    """
    query = """
    UNWIND $relationships as rel
    MATCH (c:Citation {uid: rel.citation_uid}), (y:Year {value: rel.year_value})
    MERGE (c)-[:CITED_IN]->(y)
    """
    execute_query_with_logging(tx, query, {"relationships": relationships})


def load_datasets_from_json(
    citations_dir: Path, datasets_dir: Optional[Path] = None
) -> List[Dict]:
    """
    Load dataset information from citation and dataset JSON files.

    Args:
        citations_dir: Directory containing citation JSON files
        datasets_dir: Optional directory containing dataset metadata JSON files

    Returns:
        List of dataset dictionaries for Neo4j loading
    """
    datasets = {}

    # Load basic dataset info from citation files
    json_files = list(citations_dir.glob("*.json"))
    logger.info(f"Loading dataset info from {len(json_files)} citation files...")

    for json_file in json_files:
        dataset_id = json_file.stem.replace("_citations", "")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract metadata if available
            metadata = data.get("metadata", {})

            datasets[dataset_id] = {
                "uid": dataset_id,
                "name": dataset_id,  # Default to dataset ID
                "description": None,
                "authors": None,
                "num_citations": data.get("num_citations", 0),
                "total_cumulative_citations": metadata.get(
                    "total_cumulative_citations", 0
                ),
                "date_last_updated": data.get("date_last_updated"),
                "bids_version": None,
                "data_type": None,
                "modality": None,
            }

        except Exception as e:
            logger.error(f"Error loading {json_file}: {e}")
            continue

    # Enhance with dataset metadata if available
    if datasets_dir and datasets_dir.exists():
        metadata_files = list(datasets_dir.glob("*.json"))
        logger.info(f"Enhancing with metadata from {len(metadata_files)} files...")

        for metadata_file in metadata_files:
            dataset_id = metadata_file.stem.replace("_datasets", "")

            if dataset_id in datasets:
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)

                    dataset_desc = metadata.get("dataset_description", {})
                    datasets[dataset_id].update(
                        {
                            "name": dataset_desc.get("Name", dataset_id),
                            "description": dataset_desc.get("Description"),
                            "authors": dataset_desc.get("Authors"),
                            "bids_version": dataset_desc.get("BIDSVersion"),
                            "data_type": dataset_desc.get("DatasetType"),
                        }
                    )

                except Exception as e:
                    logger.error(f"Error loading metadata {metadata_file}: {e}")
                    continue

    return list(datasets.values())


def load_citations_from_json(
    citations_dir: Path, confidence_threshold: float = 0.4
) -> List[Dict]:
    """
    Load citation information from citation JSON files.

    Args:
        citations_dir: Directory containing citation JSON files
        confidence_threshold: Minimum confidence score to include citations

    Returns:
        List of citation dictionaries for Neo4j loading
    """
    citations = []
    json_files = list(citations_dir.glob("*.json"))
    logger.info(f"Loading citations from {len(json_files)} files...")

    for json_file in json_files:
        dataset_id = json_file.stem.replace("_citations", "")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            citation_details = data.get("citation_details", [])

            for i, citation in enumerate(citation_details):
                confidence = citation.get("confidence_score", 0.0)

                # Only include high-confidence citations
                if confidence < confidence_threshold:
                    continue

                citation_uid = f"{dataset_id}_citation_{i}"
                citations.append(
                    {
                        "uid": citation_uid,
                        "title": citation.get("title", ""),
                        "author": citation.get("author"),
                        "venue": citation.get("venue"),
                        "year": citation.get("year"),
                        "abstract": citation.get("abstract"),
                        "cited_by": citation.get("cited_by", 0),
                        "confidence_score": confidence,
                        "url": citation.get("url"),
                        "dataset_id": dataset_id,
                    }
                )

        except Exception as e:
            logger.error(f"Error loading citations from {json_file}: {e}")
            continue

    logger.info(f"Loaded {len(citations)} high-confidence citations")
    return citations


def initialize_database(driver: Driver) -> None:
    """
    Initialize the Neo4j database with constraints and indexes.

    Args:
        driver: Neo4j driver instance
    """
    with driver.session() as session:
        session.execute_write(create_constraints)
        session.execute_write(create_indexes)

    logger.info("Database initialized with constraints and indexes")


def load_citation_graph(
    driver: Driver,
    citations_dir: Path,
    datasets_dir: Optional[Path] = None,
    confidence_threshold: float = 0.4,
    batch_size: int = 1000,
) -> None:
    """
    Load the complete citation graph into Neo4j.

    Args:
        driver: Neo4j driver instance
        citations_dir: Directory containing citation JSON files
        datasets_dir: Optional directory containing dataset metadata
        confidence_threshold: Minimum confidence score for citations
        batch_size: Batch size for Neo4j operations
    """
    logger.info("Starting citation graph loading...")

    # Initialize database
    initialize_database(driver)

    # Load datasets
    datasets = load_datasets_from_json(citations_dir, datasets_dir)
    logger.info(f"Loading {len(datasets)} datasets...")

    with driver.session() as session:
        for i in range(0, len(datasets), batch_size):
            batch = datasets[i : i + batch_size]
            session.execute_write(batch_add_datasets, batch)

    # Load citations
    citations = load_citations_from_json(citations_dir, confidence_threshold)
    logger.info(f"Loading {len(citations)} citations...")

    with driver.session() as session:
        for i in range(0, len(citations), batch_size):
            batch = citations[i : i + batch_size]
            session.execute_write(batch_add_citations, batch)

    # Create years and relationships
    years = sorted(
        {c["year"] for c in citations if c["year"] and 1900 <= c["year"] <= 2030}
    )
    year_dicts = [{"value": year} for year in years]

    with driver.session() as session:
        session.execute_write(batch_add_years, year_dicts)

    # Create dataset-citation relationships
    dataset_citation_rels = [
        {"dataset_uid": c["dataset_id"], "citation_uid": c["uid"]} for c in citations
    ]

    with driver.session() as session:
        for i in range(0, len(dataset_citation_rels), batch_size):
            batch = dataset_citation_rels[i : i + batch_size]
            session.execute_write(batch_add_dataset_cites_citation, batch)

    # Create citation-year relationships
    citation_year_rels = [
        {"citation_uid": c["uid"], "year_value": c["year"]}
        for c in citations
        if c["year"] and 1900 <= c["year"] <= 2030
    ]

    with driver.session() as session:
        for i in range(0, len(citation_year_rels), batch_size):
            batch = citation_year_rels[i : i + batch_size]
            session.execute_write(batch_add_citation_cited_in_year, batch)

    logger.info("Citation graph loading completed successfully")
