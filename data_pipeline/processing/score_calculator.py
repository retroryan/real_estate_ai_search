"""
Fixed score calculation processor using simple Pandas UDFs.

This module provides efficient score calculation using Pandas UDFs with proper
data type handling for Spark arrays and null values.
"""

import logging
from typing import List, Optional, Any
import pandas as pd

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import pandas_udf, col, lit
from pyspark.sql.types import FloatType

logger = logging.getLogger(__name__)


def safe_list_check(value: Any) -> List[str]:
    """Safely convert value to a list of strings."""
    if value is None:
        return []
    
    # Handle numpy arrays from Pandas UDFs
    if hasattr(value, '__iter__') and not isinstance(value, str):
        try:
            return [str(item) for item in value if item is not None]
        except (TypeError, ValueError):
            return []
    
    return []


def calculate_nightlife_score(amenities: Any, tags: Any = None) -> float:
    """Calculate nightlife score for a single record."""
    try:
        amenities_list = safe_list_check(amenities)
        if not amenities_list:
            return 0.0
        
        nightlife_keywords = {
            "bar", "pub", "club", "nightclub", "lounge", "brewery",
            "wine", "cocktail", "music venue", "theater", "cinema"
        }
        
        score = 0.0
        amenities_lower = [a.lower() for a in amenities_list]
        
        # Count nightlife amenities
        for amenity in amenities_lower:
            for keyword in nightlife_keywords:
                if keyword in amenity:
                    score += 1.0
                    break
        
        # Check lifestyle tags if provided
        tags_list = safe_list_check(tags)
        if tags_list:
            tags_lower = [t.lower() for t in tags_list]
            if any("nightlife" in tag or "entertainment" in tag for tag in tags_lower):
                score += 2.0
        
        # Normalize to 0-10 scale
        return min(score * 1.5, 10.0)
        
    except Exception as e:
        logger.warning(f"Error calculating nightlife score: {e}")
        return 0.0


def calculate_family_score(school_rating: Any, safety_rating: Any, amenities: Any, tags: Any = None) -> float:
    """Calculate family-friendly score for a single record."""
    try:
        score = 0.0
        weight_count = 0
        
        # School rating contributes 40%
        if school_rating is not None and pd.notna(school_rating):
            score += float(school_rating) * 0.4
            weight_count += 0.4
        
        # Safety rating contributes 30%
        if safety_rating is not None and pd.notna(safety_rating):
            score += float(safety_rating) * 0.3
            weight_count += 0.3
        
        # Family amenities contribute 30%
        amenities_list = safe_list_check(amenities)
        if amenities_list:
            family_keywords = {
                "school", "park", "playground", "library", "community center",
                "daycare", "pediatric", "family", "youth", "recreation"
            }
            
            amenities_lower = [a.lower() for a in amenities_list]
            amenity_score = 0.0
            
            for amenity in amenities_lower:
                for keyword in family_keywords:
                    if keyword in amenity:
                        amenity_score += 1.0
                        break
            
            # Normalize amenity score
            normalized_amenity = min(amenity_score * 2, 10.0)
            score += normalized_amenity * 0.3
            weight_count += 0.3
        
        # Adjust for tags if provided
        tags_list = safe_list_check(tags)
        if tags_list:
            tags_lower = [t.lower() for t in tags_list]
            if any("family" in tag or "quiet" in tag for tag in tags_lower):
                score = min(score + 1.0, 10.0)
        
        # Normalize by actual weights used
        if weight_count > 0:
            return score / weight_count * 10.0 if weight_count < 1 else score
        return 0.0
        
    except Exception as e:
        logger.warning(f"Error calculating family score: {e}")
        return 0.0


def calculate_cultural_score(amenities: Any, topics: Any = None) -> float:
    """Calculate cultural score for a single record."""
    try:
        amenities_list = safe_list_check(amenities)
        if not amenities_list:
            return 0.0
        
        cultural_keywords = {
            "museum", "art", "gallery", "theater", "theatre", "music",
            "concert", "cultural", "heritage", "historic", "library",
            "exhibition", "festival", "opera", "symphony"
        }
        
        score = 0.0
        amenities_lower = [a.lower() for a in amenities_list]
        
        for amenity in amenities_lower:
            for keyword in cultural_keywords:
                if keyword in amenity:
                    score += 1.0
                    break
        
        # Boost for Wikipedia topics
        topics_list = safe_list_check(topics)
        if topics_list:
            topics_lower = [t.lower() for t in topics_list]
            topic_boost = sum(1 for t in topics_lower if any(k in t for k in cultural_keywords))
            score += topic_boost * 0.5
        
        # Normalize to 0-10 scale
        return min(score * 1.5, 10.0)
        
    except Exception as e:
        logger.warning(f"Error calculating cultural score: {e}")
        return 0.0


def calculate_green_space_score(amenities: Any, tags: Any = None) -> float:
    """Calculate green space score for a single record."""
    try:
        amenities_list = safe_list_check(amenities)
        if not amenities_list:
            return 0.0
        
        green_keywords = {
            "park", "garden", "trail", "beach", "forest", "nature",
            "outdoor", "recreation", "green", "golf", "lake", "river",
            "hiking", "biking", "open space"
        }
        
        score = 0.0
        amenities_lower = [a.lower() for a in amenities_list]
        
        for amenity in amenities_lower:
            for keyword in green_keywords:
                if keyword in amenity:
                    score += 1.0
                    break
        
        # Check tags for outdoor lifestyle
        tags_list = safe_list_check(tags)
        if tags_list:
            tags_lower = [t.lower() for t in tags_list]
            if any("outdoor" in tag or "nature" in tag for tag in tags_lower):
                score += 2.0
        
        # Normalize to 0-10 scale
        return min(score * 1.5, 10.0)
        
    except Exception as e:
        logger.warning(f"Error calculating green space score: {e}")
        return 0.0


def calculate_knowledge_score(wikipedia_count: Any, topics_count: Any, amenities_count: Any) -> float:
    """Calculate knowledge score for a single record."""
    try:
        wiki_count = int(wikipedia_count) if wikipedia_count is not None and pd.notna(wikipedia_count) else 0
        topic_count = int(topics_count) if topics_count is not None and pd.notna(topics_count) else 0
        amenity_count = int(amenities_count) if amenities_count is not None and pd.notna(amenities_count) else 0
        
        # Base score from Wikipedia coverage
        wiki_score = min(wiki_count / 10.0, 0.5)  # Max 0.5 from Wikipedia
        
        # Topic diversity score
        topic_score = min(topic_count / 20.0, 0.3)  # Max 0.3 from topics
        
        # Amenity extraction score
        amenity_score = min(amenity_count / 20.0, 0.2)  # Max 0.2 from amenities
        
        return wiki_score + topic_score + amenity_score
        
    except Exception as e:
        logger.warning(f"Error calculating knowledge score: {e}")
        return 0.0


def calculate_overall_confidence(location_confidence: Any, extraction_confidence: Any, content_ratio: Any) -> float:
    """Calculate overall confidence for a single record."""
    try:
        loc_conf = float(location_confidence) if location_confidence is not None and pd.notna(location_confidence) else 0.5
        ext_conf = float(extraction_confidence) if extraction_confidence is not None and pd.notna(extraction_confidence) else 0.5
        cont_ratio = float(content_ratio) if content_ratio is not None and pd.notna(content_ratio) else 0.5
        
        # Weighted average
        confidence = (
            loc_conf * 0.5 +
            ext_conf * 0.3 +
            cont_ratio * 0.2
        )
        
        return min(confidence, 1.0)
        
    except Exception as e:
        logger.warning(f"Error calculating overall confidence: {e}")
        return 0.5  # Default moderate confidence


# Pandas UDFs
@pandas_udf(returnType=FloatType())
def nightlife_score_udf(amenities_series: pd.Series, tags_series: pd.Series) -> pd.Series:
    """Pandas UDF for nightlife score calculation."""
    return pd.Series([
        calculate_nightlife_score(amenities, tags)
        for amenities, tags in zip(amenities_series, tags_series)
    ])


@pandas_udf(returnType=FloatType())
def family_friendly_score_udf(
    school_rating_series: pd.Series,
    safety_rating_series: pd.Series, 
    amenities_series: pd.Series,
    tags_series: pd.Series
) -> pd.Series:
    """Pandas UDF for family-friendly score calculation."""
    return pd.Series([
        calculate_family_score(school, safety, amenities, tags)
        for school, safety, amenities, tags in zip(
            school_rating_series, safety_rating_series, 
            amenities_series, tags_series
        )
    ])


@pandas_udf(returnType=FloatType())
def cultural_score_udf(amenities_series: pd.Series, topics_series: pd.Series) -> pd.Series:
    """Pandas UDF for cultural score calculation."""
    return pd.Series([
        calculate_cultural_score(amenities, topics)
        for amenities, topics in zip(amenities_series, topics_series)
    ])


@pandas_udf(returnType=FloatType())
def green_space_score_udf(amenities_series: pd.Series, tags_series: pd.Series) -> pd.Series:
    """Pandas UDF for green space score calculation."""
    return pd.Series([
        calculate_green_space_score(amenities, tags)
        for amenities, tags in zip(amenities_series, tags_series)
    ])


@pandas_udf(returnType=FloatType())
def knowledge_score_udf(
    wiki_count_series: pd.Series,
    topic_count_series: pd.Series,
    amenity_count_series: pd.Series
) -> pd.Series:
    """Pandas UDF for knowledge score calculation."""
    return pd.Series([
        calculate_knowledge_score(wiki, topic, amenity)
        for wiki, topic, amenity in zip(
            wiki_count_series, topic_count_series, amenity_count_series
        )
    ])


@pandas_udf(returnType=FloatType())
def overall_confidence_udf(
    location_conf_series: pd.Series,
    extraction_conf_series: pd.Series,
    content_ratio_series: pd.Series
) -> pd.Series:
    """Pandas UDF for overall confidence calculation."""
    return pd.Series([
        calculate_overall_confidence(loc, ext, content)
        for loc, ext, content in zip(
            location_conf_series, extraction_conf_series, content_ratio_series
        )
    ])


class ScoreCalculator:
    """Score calculator using fixed Pandas UDFs."""
    
    def __init__(self, spark: SparkSession):
        """Initialize the score calculator."""
        self.spark = spark
        logger.info("Initialized ScoreCalculator with fixed Pandas UDFs")
    
    def add_lifestyle_scores(self, df: DataFrame) -> DataFrame:
        """Add all lifestyle scores to a DataFrame."""
        logger.info("Adding lifestyle scores using fixed Pandas UDFs")
        
        # Handle missing columns gracefully
        null_tags = lit(None).cast("array<string>")
        null_float = lit(None).cast("float")
        
        # Add nightlife score
        df_with_scores = df.withColumn(
            "nightlife_score",
            nightlife_score_udf(
                col("amenities"), 
                col("tags") if "tags" in df.columns else null_tags
            )
        )
        
        # Add family-friendly score
        df_with_scores = df_with_scores.withColumn(
            "family_friendly_score",
            family_friendly_score_udf(
                col("school_rating") if "school_rating" in df.columns else null_float,
                col("safety_rating") if "safety_rating" in df.columns else null_float,
                col("amenities"),
                col("tags") if "tags" in df.columns else null_tags
            )
        )
        
        # Add cultural score
        df_with_scores = df_with_scores.withColumn(
            "cultural_score",
            cultural_score_udf(
                col("amenities"),
                col("aggregated_topics") if "aggregated_topics" in df.columns else null_tags
            )
        )
        
        # Add green space score
        df_with_scores = df_with_scores.withColumn(
            "green_space_score",
            green_space_score_udf(
                col("amenities"),
                col("tags") if "tags" in df.columns else null_tags
            )
        )
        
        logger.info("Successfully added all lifestyle scores")
        return df_with_scores
    
    def add_knowledge_scores(self, df: DataFrame) -> DataFrame:
        """Add knowledge-based scores to a DataFrame."""
        logger.info("Adding knowledge scores using fixed Pandas UDFs")
        
        null_int = lit(0).cast("int")
        
        # Add knowledge score
        df_with_knowledge = df.withColumn(
            "knowledge_score",
            knowledge_score_udf(
                col("wikipedia_count") if "wikipedia_count" in df.columns else null_int,
                col("topic_count") if "topic_count" in df.columns else null_int,
                col("amenity_count") if "amenity_count" in df.columns else null_int
            )
        )
        
        logger.info("Successfully added knowledge scores")
        return df_with_knowledge
    
    def add_confidence_scores(self, df: DataFrame) -> DataFrame:
        """Add confidence scores to a DataFrame."""
        logger.info("Adding confidence scores using fixed Pandas UDFs")
        
        null_float = lit(0.5).cast("float")
        
        # Add overall confidence
        df_with_confidence = df.withColumn(
            "overall_confidence",
            overall_confidence_udf(
                col("location_confidence") if "location_confidence" in df.columns else null_float,
                col("extraction_confidence") if "extraction_confidence" in df.columns else null_float,
                col("content_ratio") if "content_ratio" in df.columns else null_float
            )
        )
        
        logger.info("Successfully added confidence scores")
        return df_with_confidence