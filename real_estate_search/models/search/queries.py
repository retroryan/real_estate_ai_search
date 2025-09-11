"""
Query builder models.

Models for constructing Elasticsearch queries.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from ..enums import QueryType


class QueryClause(BaseModel):
    """Single query clause in a compound query."""
    type: QueryType = Field(..., description="Type of query")
    field: Optional[str] = Field(None, description="Field to query")
    value: Optional[str] = Field(None, description="Query value")
    params: dict = Field(default_factory=dict, description="Additional parameters")
    
    model_config = ConfigDict(extra="ignore", use_enum_values=True)
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch query clause."""
        if self.type == QueryType.MATCH:
            return {"match": {self.field: {"query": self.value, **self.params}}}
        elif self.type == QueryType.TERM:
            return {"term": {self.field: self.value}}
        elif self.type == QueryType.RANGE:
            return {"range": {self.field: self.value}}
        elif self.type == QueryType.MULTI_MATCH:
            return {"multi_match": {"query": self.value, **self.params}}
        elif self.type == QueryType.MATCH_PHRASE:
            return {"match_phrase": {self.field: {"query": self.value, **self.params}}}
        elif self.type == QueryType.GEO_DISTANCE:
            return {"geo_distance": {**self.params, self.field: self.value}}
        elif self.type == QueryType.KNN:
            return {"knn": {self.field: {"vector": self.value, **self.params}}}
        else:
            return {self.type.value: self.params}


class BoolQuery(BaseModel):
    """Boolean compound query for combining multiple query clauses."""
    must: List[QueryClause] = Field(default_factory=list, description="Must match all")
    should: List[QueryClause] = Field(default_factory=list, description="Should match any")
    must_not: List[QueryClause] = Field(default_factory=list, description="Must not match")
    filter: List[QueryClause] = Field(default_factory=list, description="Filter without scoring")
    minimum_should_match: Optional[int] = Field(None, description="Minimum should clauses")
    boost: Optional[float] = Field(None, description="Query boost factor")
    
    model_config = ConfigDict(extra="ignore")
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch bool query."""
        bool_query: dict = {}
        
        if self.must:
            bool_query["must"] = [clause.to_dict() for clause in self.must]
        if self.should:
            bool_query["should"] = [clause.to_dict() for clause in self.should]
        if self.must_not:
            bool_query["must_not"] = [clause.to_dict() for clause in self.must_not]
        if self.filter:
            bool_query["filter"] = [clause.to_dict() for clause in self.filter]
        if self.minimum_should_match is not None:
            bool_query["minimum_should_match"] = self.minimum_should_match
        if self.boost is not None:
            bool_query["boost"] = self.boost
            
        return {"bool": bool_query}


class MatchQuery(BaseModel):
    """Match query for full-text search."""
    field: str = Field(..., description="Field to search")
    query: str = Field(..., description="Search query")
    operator: Optional[str] = Field(None, description="Operator (and/or)")
    fuzziness: Optional[str] = Field(None, description="Fuzziness level")
    boost: Optional[float] = Field(None, description="Query boost")
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch match query."""
        params = {"query": self.query}
        if self.operator:
            params["operator"] = self.operator
        if self.fuzziness:
            params["fuzziness"] = self.fuzziness
        if self.boost:
            params["boost"] = self.boost
        return {"match": {self.field: params}}


class MultiMatchQuery(BaseModel):
    """Multi-match query for searching across multiple fields."""
    query: str = Field(..., description="Search query")
    fields: List[str] = Field(..., description="Fields to search")
    type: Optional[str] = Field(None, description="Multi-match type")
    operator: Optional[str] = Field(None, description="Operator (and/or)")
    fuzziness: Optional[str] = Field(None, description="Fuzziness level")
    boost: Optional[float] = Field(None, description="Query boost")
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch multi_match query."""
        query = {
            "multi_match": {
                "query": self.query,
                "fields": self.fields
            }
        }
        if self.type:
            query["multi_match"]["type"] = self.type
        if self.operator:
            query["multi_match"]["operator"] = self.operator
        if self.fuzziness:
            query["multi_match"]["fuzziness"] = self.fuzziness
        if self.boost:
            query["multi_match"]["boost"] = self.boost
        return query


class RangeQuery(BaseModel):
    """Range query for numeric or date ranges."""
    field: str = Field(..., description="Field to query")
    gte: Optional[float] = Field(None, description="Greater than or equal to")
    gt: Optional[float] = Field(None, description="Greater than")
    lte: Optional[float] = Field(None, description="Less than or equal to")
    lt: Optional[float] = Field(None, description="Less than")
    boost: Optional[float] = Field(None, description="Query boost")
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch range query."""
        params = {}
        if self.gte is not None:
            params["gte"] = self.gte
        if self.gt is not None:
            params["gt"] = self.gt
        if self.lte is not None:
            params["lte"] = self.lte
        if self.lt is not None:
            params["lt"] = self.lt
        if self.boost:
            params["boost"] = self.boost
        return {"range": {self.field: params}}


class TermQuery(BaseModel):
    """Term query for exact value matching."""
    field: str = Field(..., description="Field to query")
    value: str = Field(..., description="Exact value to match")
    boost: Optional[float] = Field(None, description="Query boost")
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch term query."""
        if self.boost:
            return {"term": {self.field: {"value": self.value, "boost": self.boost}}}
        return {"term": {self.field: self.value}}