from datetime import datetime
from pydantic import BaseModel

from retrosynthesis_search import SearchStatus


class CatalogEntry(BaseModel):
    vendor_id: str
    catalog_name: str
    lead_time_weeks: float


class ReactionNode(BaseModel):
    name: str
    reactants: list["MoleculeNode"]


class MoleculeNode(BaseModel):
    smiles: str
    catalog_entries: list[CatalogEntry]
    is_purchasable: bool
    reactions: list[ReactionNode]


class RetrosynthesisTree(BaseModel):
    score: float
    root: MoleculeNode


class Reaction(BaseModel):
    name: str
    target: str
    sources: list[str]


class Molecule(BaseModel):
    smiles: str
    catalog_entries: list[CatalogEntry]


class SearchRequest(BaseModel):
    id: str
    smiles: str
    status: SearchStatus
    progress: float
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None


class Route(BaseModel):
    score: float
    molecules: list[Molecule]
    reactions: list[Reaction]


class SearchUpdate(BaseModel):
    routes: list[Route]
    is_complete: bool = False
    error_message: str | None = None


class SearchCreateRequest(BaseModel):
    smiles: str


class SearchCreateResponse(BaseModel):
    id: str


class SearchStatusResponse(BaseModel):
    id: str
    smiles: str
    status: SearchStatus
    created_at: str
    updated_at: str
    error_message: str | None = None


class UpdateResponse(BaseModel):
    status: str


class SearchResultsResponse(BaseModel):
    search_id: str
    total_routes: int
    routes: list[RetrosynthesisTree]


class HealthResponse(BaseModel):
    status: str
