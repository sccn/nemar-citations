"""CLI command for loading dataset citations into Neo4j graph database."""

import argparse
import logging
import os
from pathlib import Path
from typing import Optional

from neo4j import GraphDatabase

from ..graph.neo4j_loader import load_citation_graph

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def get_neo4j_credentials() -> tuple[str, str, str]:
    """
    Get Neo4j connection credentials from environment variables.

    Returns:
        Tuple of (uri, username, password)

    Raises:
        ValueError: If required credentials are not found
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError(
            "Neo4j password is required. Set NEO4J_PASSWORD environment variable "
            "or use --password argument"
        )

    return uri, username, password


def test_neo4j_connection(uri: str, username: str, password: str) -> bool:
    """
    Test Neo4j database connection.

    Args:
        uri: Neo4j URI
        username: Neo4j username
        password: Neo4j password

    Returns:
        True if connection successful, False otherwise
    """
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        logger.info("✅ Neo4j connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        return False


def clear_database(driver, confirm: bool = False) -> None:
    """
    Clear all data from the Neo4j database.

    Args:
        driver: Neo4j driver instance
        confirm: If True, skip confirmation prompt
    """
    if not confirm:
        response = input(
            "⚠️  This will delete ALL data in the Neo4j database. Continue? (yes/no): "
        )
        if response.lower() != "yes":
            print("Database clear cancelled.")
            return

    logger.info("Clearing Neo4j database...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    logger.info("Database cleared successfully")


def run_graph_loading(
    citations_dir: Path,
    neo4j_uri: str,
    neo4j_username: str,
    neo4j_password: str,
    datasets_dir: Optional[Path] = None,
    confidence_threshold: float = 0.4,
    batch_size: int = 1000,
    clear_db: bool = False,
    verbose: bool = False,
) -> None:
    """
    Load dataset citations into Neo4j graph database.

    Args:
        citations_dir: Directory containing citation JSON files
        neo4j_uri: Neo4j database URI
        neo4j_username: Neo4j username
        neo4j_password: Neo4j password
        datasets_dir: Optional directory containing dataset metadata
        confidence_threshold: Minimum confidence score for citations
        batch_size: Batch size for Neo4j operations
        clear_db: Whether to clear the database before loading
        verbose: Enable verbose logging
    """
    setup_logging(verbose)

    if not citations_dir.exists():
        raise FileNotFoundError(f"Citations directory not found: {citations_dir}")

    if datasets_dir and not datasets_dir.exists():
        logger.warning(f"Datasets directory not found: {datasets_dir}")
        datasets_dir = None

    logger.info("Starting Neo4j graph loading...")
    logger.info(f"Citations directory: {citations_dir}")
    logger.info(f"Datasets directory: {datasets_dir}")
    logger.info(f"Confidence threshold: {confidence_threshold}")
    logger.info(f"Neo4j URI: {neo4j_uri}")

    # Test connection
    if not test_neo4j_connection(neo4j_uri, neo4j_username, neo4j_password):
        raise ConnectionError("Cannot connect to Neo4j database")

    # Create driver
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

    try:
        # Clear database if requested
        if clear_db:
            clear_database(driver, confirm=False)

        # Load the citation graph
        load_citation_graph(
            driver=driver,
            citations_dir=citations_dir,
            datasets_dir=datasets_dir,
            confidence_threshold=confidence_threshold,
            batch_size=batch_size,
        )

        logger.info("✅ Graph loading completed successfully!")
        print("\n🎉 Citation graph loaded into Neo4j!")
        print(f"   🔗 Connect to: {neo4j_uri}")
        print(f"   👤 Username: {neo4j_username}")
        print("   📊 You can now use Neo4j Browser or Bloom for visualization")

    finally:
        driver.close()


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Load dataset citations into Neo4j graph database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "citations_dir",
        type=Path,
        help="Directory containing citation JSON files (e.g., citations/json/)",
    )

    parser.add_argument(
        "--datasets-dir",
        type=Path,
        help="Directory containing dataset metadata JSON files (e.g., datasets/)",
    )

    parser.add_argument(
        "--neo4j-uri", default="bolt://localhost:7687", help="Neo4j database URI"
    )

    parser.add_argument("--neo4j-username", default="neo4j", help="Neo4j username")

    parser.add_argument(
        "--neo4j-password", help="Neo4j password (or set NEO4J_PASSWORD env var)"
    )

    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.4,
        help="Minimum confidence score for including citations",
    )

    parser.add_argument(
        "--batch-size", type=int, default=1000, help="Batch size for Neo4j operations"
    )

    parser.add_argument(
        "--clear-db",
        action="store_true",
        help="Clear database before loading (WARNING: deletes all data)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Get Neo4j password
    neo4j_password = args.neo4j_password
    if not neo4j_password:
        try:
            _, _, neo4j_password = get_neo4j_credentials()
        except ValueError as e:
            logger.error(f"❌ {e}")
            parser.print_help()
            return

    try:
        run_graph_loading(
            citations_dir=args.citations_dir,
            neo4j_uri=args.neo4j_uri,
            neo4j_username=args.neo4j_username,
            neo4j_password=neo4j_password,
            datasets_dir=args.datasets_dir,
            confidence_threshold=args.confidence_threshold,
            batch_size=args.batch_size,
            clear_db=args.clear_db,
            verbose=args.verbose,
        )
    except Exception as e:
        logger.error(f"❌ Graph loading failed: {e}")
        raise


if __name__ == "__main__":
    main()
