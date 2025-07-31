"""Neo4j-based network analysis for dataset citations using Cypher queries."""

import logging
from typing import Tuple

import pandas as pd
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class Neo4jNetworkAnalyzer:
    """Network analyzer using Neo4j graph database."""

    def __init__(self, uri: str, username: str, password: str):
        """
        Initialize Neo4j network analyzer.

        Args:
            uri: Neo4j database URI
            username: Neo4j username
            password: Neo4j password
        """
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def find_multi_dataset_citations(
        self, confidence_threshold: float = 0.4
    ) -> pd.DataFrame:
        """
        Find citations that appear across multiple datasets using Neo4j.

        Args:
            confidence_threshold: Minimum confidence score for citations

        Returns:
            DataFrame with multi-dataset citation analysis
        """
        query = """
        MATCH (d:Dataset)-[:HAS_CITATION]->(c:Citation)
        WHERE c.confidence_score >= $confidence_threshold
        WITH c, collect(DISTINCT d.uid) as datasets
        WHERE size(datasets) > 1
        RETURN c.title as citation_title,
               c.author as citation_author,
               c.year as citation_year,
               c.cited_by as citation_impact,
               c.confidence_score as confidence_score,
               datasets,
               size(datasets) as num_datasets_cited
        ORDER BY num_datasets_cited DESC, citation_impact DESC
        """

        with self.driver.session() as session:
            result = session.run(query, confidence_threshold=confidence_threshold)
            data = [record.data() for record in result]

        df = pd.DataFrame(data)
        logger.info(f"Found {len(df)} citations that appear across multiple datasets")
        return df

    def analyze_dataset_co_citations(
        self, confidence_threshold: float = 0.4
    ) -> pd.DataFrame:
        """
        Analyze which datasets are commonly co-cited together.

        Args:
            confidence_threshold: Minimum confidence score for citations

        Returns:
            DataFrame with dataset co-citation analysis
        """
        query = """
        MATCH (d1:Dataset)-[:HAS_CITATION]->(c:Citation)<-[:HAS_CITATION]-(d2:Dataset)
        WHERE c.confidence_score >= $confidence_threshold 
        AND d1.uid < d2.uid  // Avoid duplicate pairs
        WITH d1, d2, count(c) as shared_citations, collect(c.title) as shared_citation_titles
        RETURN d1.uid as dataset1,
               d1.name as dataset1_name,
               d1.total_cumulative_citations as dataset1_total_citations,
               d2.uid as dataset2, 
               d2.name as dataset2_name,
               d2.total_cumulative_citations as dataset2_total_citations,
               shared_citations,
               shared_citation_titles
        ORDER BY shared_citations DESC
        """

        with self.driver.session() as session:
            result = session.run(query, confidence_threshold=confidence_threshold)
            data = [record.data() for record in result]

        df = pd.DataFrame(data)
        logger.info(f"Found {len(df)} dataset pairs with shared citations")
        return df

    def analyze_author_collaboration_networks(
        self, confidence_threshold: float = 0.4
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Analyze author collaboration networks between dataset creators and citation authors.

        Args:
            confidence_threshold: Minimum confidence score for citations

        Returns:
            Tuple of (author_overlap_df, author_influence_df)
        """
        # Find authors who are both dataset creators and appear in citations
        overlap_query = """
        MATCH (d:Dataset)-[:HAS_CITATION]->(c:Citation)
        WHERE c.confidence_score >= $confidence_threshold
        AND any(author IN d.authors WHERE c.author CONTAINS author OR author CONTAINS c.author)
        WITH d, c, [author IN d.authors WHERE c.author CONTAINS author OR author CONTAINS c.author] as matching_authors
        WHERE size(matching_authors) > 0
        RETURN d.uid as dataset_id,
               d.name as dataset_name,
               c.title as citation_title,
               c.author as citation_author,
               matching_authors,
               c.cited_by as citation_impact,
               c.confidence_score as confidence_score
        ORDER BY citation_impact DESC
        """

        # Analyze author influence across multiple datasets
        influence_query = """
        MATCH (d:Dataset)-[:HAS_CITATION]->(c:Citation)
        WHERE c.confidence_score >= $confidence_threshold
        WITH c.author as author, 
             collect(DISTINCT d.uid) as datasets_cited,
             sum(c.cited_by) as total_citation_impact,
             avg(c.confidence_score) as avg_confidence,
             count(c) as total_citations
        WHERE size(datasets_cited) > 1  // Authors who cite multiple datasets
        RETURN author,
               datasets_cited,
               size(datasets_cited) as num_datasets_cited,
               total_citations,
               total_citation_impact,
               avg_confidence
        ORDER BY num_datasets_cited DESC, total_citation_impact DESC
        """

        with self.driver.session() as session:
            # Get author overlaps
            overlap_result = session.run(
                overlap_query, confidence_threshold=confidence_threshold
            )
            overlap_data = [record.data() for record in overlap_result]

            # Get author influence
            influence_result = session.run(
                influence_query, confidence_threshold=confidence_threshold
            )
            influence_data = [record.data() for record in influence_result]

        overlap_df = pd.DataFrame(overlap_data)
        influence_df = pd.DataFrame(influence_data)

        logger.info(
            f"Found {len(overlap_df)} author overlaps and {len(influence_df)} influential cross-dataset authors"
        )
        return overlap_df, influence_df

    def analyze_citation_impact_rankings(
        self, confidence_threshold: float = 0.4, limit: int = 50
    ) -> pd.DataFrame:
        """
        Analyze citation impact rankings with dataset context.

        Args:
            confidence_threshold: Minimum confidence score for citations
            limit: Maximum number of results to return

        Returns:
            DataFrame with citation impact analysis
        """
        query = """
        MATCH (d:Dataset)-[:HAS_CITATION]->(c:Citation)
        WHERE c.confidence_score >= $confidence_threshold
        RETURN c.title as citation_title,
               c.author as citation_author,
               c.year as citation_year,
               c.venue as venue,
               c.cited_by as citation_impact,
               c.confidence_score as confidence_score,
               d.uid as dataset_id,
               d.name as dataset_name,
               d.total_cumulative_citations as dataset_total_citations
        ORDER BY c.cited_by DESC
        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                query, confidence_threshold=confidence_threshold, limit=limit
            )
            data = [record.data() for record in result]

        df = pd.DataFrame(data)
        logger.info(f"Generated impact rankings for top {len(df)} citations")
        return df

    def analyze_dataset_popularity_trends(self) -> pd.DataFrame:
        """
        Analyze dataset popularity and citation trends.

        Returns:
            DataFrame with dataset popularity analysis
        """
        query = """
        MATCH (d:Dataset)
        OPTIONAL MATCH (d)-[:HAS_CITATION]->(c:Citation)
        WHERE c.confidence_score >= 0.4
        WITH d, 
             count(c) as high_confidence_citations,
             avg(c.confidence_score) as avg_confidence,
             sum(c.cited_by) as total_citation_impact,
             max(c.cited_by) as max_single_citation_impact,
             collect(c.year) as citation_years
        RETURN d.uid as dataset_id,
               d.name as dataset_name,
               d.num_citations as total_citations,
               d.total_cumulative_citations as cumulative_citations,
               high_confidence_citations,
               avg_confidence,
               total_citation_impact,
               max_single_citation_impact,
               [year IN citation_years WHERE year IS NOT NULL | year] as citation_years_list
        ORDER BY cumulative_citations DESC
        """

        with self.driver.session() as session:
            result = session.run(query)
            data = [record.data() for record in result]

        df = pd.DataFrame(data)
        logger.info(f"Generated popularity analysis for {len(df)} datasets")
        return df

    def find_bridge_papers_and_research_themes(
        self, confidence_threshold: float = 0.4
    ) -> pd.DataFrame:
        """
        Find papers that bridge different research areas by citing multiple datasets.

        Args:
            confidence_threshold: Minimum confidence score for citations

        Returns:
            DataFrame with bridge paper analysis
        """
        query = """
        MATCH (d:Dataset)-[:HAS_CITATION]->(c:Citation)
        WHERE c.confidence_score >= $confidence_threshold
        WITH c, collect(DISTINCT d.uid) as datasets, collect(DISTINCT d.data_type) as data_types
        WHERE size(datasets) >= 2
        RETURN c.title as bridge_paper_title,
               c.author as bridge_paper_author,
               c.year as bridge_paper_year,
               c.venue as venue,
               c.cited_by as citation_impact,
               c.confidence_score as confidence_score,
               datasets as datasets_bridged,
               size(datasets) as num_datasets_bridged,
               data_types as data_types_bridged,
               size(data_types) as num_data_types_bridged
        ORDER BY num_datasets_bridged DESC, citation_impact DESC
        """

        with self.driver.session() as session:
            result = session.run(query, confidence_threshold=confidence_threshold)
            data = [record.data() for record in result]

        df = pd.DataFrame(data)
        logger.info(f"Found {len(df)} bridge papers connecting multiple datasets")
        return df

    def get_temporal_network_evolution(
        self, confidence_threshold: float = 0.4
    ) -> pd.DataFrame:
        """
        Analyze how citation networks evolve over time.

        Args:
            confidence_threshold: Minimum confidence score for citations

        Returns:
            DataFrame with temporal network evolution analysis
        """
        query = """
        MATCH (d:Dataset)-[:HAS_CITATION]->(c:Citation)-[:CITED_IN_YEAR]->(y:Year)
        WHERE c.confidence_score >= $confidence_threshold
        WITH y.value as year, 
             count(DISTINCT c) as citations_count,
             count(DISTINCT d) as datasets_with_citations,
             avg(c.confidence_score) as avg_confidence,
             sum(c.cited_by) as total_impact,
             collect(DISTINCT d.data_type) as data_types_active
        WHERE year >= 2000  // Focus on recent years
        RETURN year,
               citations_count,
               datasets_with_citations,
               avg_confidence,
               total_impact,
               data_types_active,
               size(data_types_active) as num_data_types_active
        ORDER BY year
        """

        with self.driver.session() as session:
            result = session.run(query, confidence_threshold=confidence_threshold)
            data = [record.data() for record in result]

        df = pd.DataFrame(data)
        logger.info(f"Generated temporal network evolution for {len(df)} years")
        return df
