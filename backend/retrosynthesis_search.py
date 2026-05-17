import uuid
from collections import defaultdict
from enum import Enum
from typing import TypedDict
from datetime import datetime, timezone


class SearchStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SearchRequestData(TypedDict):
    id: str
    smiles: str
    status: SearchStatus
    created_at: datetime
    updated_at: datetime
    error_message: None


class CurrentSearchData(TypedDict):
    status: str


class SearchUpdateData(TypedDict):
    updated_at: datetime
    status: SearchStatus
    error_message: str | None


class CatalogEntryData(TypedDict):
    vendor_id: str
    catalog_name: str
    lead_time_weeks: float


class MoleculeData(TypedDict):
    smiles: str
    catalog_entries: list[CatalogEntryData]


class EnrichedMoleculeData(TypedDict):
    smiles: str
    catalog_entries: list[CatalogEntryData]
    is_purchasable: bool


class ReactionData(TypedDict):
    name: str
    target: str
    sources: list[str]


class RouteData(TypedDict):
    score: float
    molecules: list[MoleculeData]
    reactions: list[ReactionData]


class EnrichedRouteData(TypedDict):
    score: float
    molecules: list[EnrichedMoleculeData]
    reactions: list[ReactionData]


class ReactionNode(TypedDict):
    name: str
    reactants: list["MoleculeNode"]


class MoleculeNode(TypedDict):
    smiles: str
    catalog_entries: list[CatalogEntryData]
    is_purchasable: bool
    reactions: list[ReactionNode]


class RetrosynthesisTree(TypedDict):
    score: float
    root: MoleculeNode


def create_search_request(smiles: str) -> SearchRequestData:
    now = datetime.now(timezone.utc)
    return {
        "id": str(uuid.uuid4()),
        "smiles": smiles,
        "status": SearchStatus.PENDING,
        "created_at": now,
        "updated_at": now,
        "error_message": None,
    }


def update_search_progress(
    current_data: CurrentSearchData,
    new_results: list[RouteData],
    is_complete: bool = False,
    error_message: str | None = None,
) -> SearchUpdateData:
    now = datetime.now(timezone.utc)

    if error_message:
        return {
            "updated_at": now,
            "status": SearchStatus.FAILED,
            "error_message": error_message,
        }

    if is_complete:
        return {
            "updated_at": now,
            "status": SearchStatus.COMPLETED,
            "error_message": None,
        }

    if new_results:
        return {
            "updated_at": now,
            "status": SearchStatus.IN_PROGRESS,
            "error_message": None,
        }

    return {
        "updated_at": now,
        "status": SearchStatus(current_data["status"]),
        "error_message": None,
    }


def build_retrosynthesis_tree(route: RouteData) -> RetrosynthesisTree:
    molecule_map: dict[str, MoleculeData] = {m["smiles"]: m for m in route["molecules"]}
    reactions_by_target: dict[str, list[ReactionData]] = defaultdict(list)
    targets: set[str] = set()
    sources: set[str] = set()

    for r in route["reactions"]:
        reactions_by_target[r["target"]].append(r)
        targets.add(r["target"])
        sources.update(r["sources"])

    roots = targets - sources
    if len(roots) != 1:
        raise ValueError(
            "Found 0 or multiple potential root smiles. A valid retrosynthesis tree must have exactly one root."
        )

    root_smiles = next(iter(roots))

    def build_molecule_node(smiles: str, visited: set[str]) -> MoleculeNode:
        mol = molecule_map.get(smiles, {"smiles": smiles, "catalog_entries": []})
        catalog_entries = mol.get("catalog_entries", [])

        if smiles in visited:
            raise ValueError(
                "Cycle detected. A valid retrosynthesis tree cannot contain cycles."
            )

        visited.add(smiles)

        reactions: list[ReactionNode] = [
            {
                "name": r["name"],
                "reactants": [
                    build_molecule_node(src, visited.copy()) for src in r["sources"]
                ],
            }
            for r in reactions_by_target.get(smiles, [])
        ]

        return {
            "smiles": smiles,
            "catalog_entries": catalog_entries,
            "is_purchasable": bool(catalog_entries),
            "reactions": reactions,
        }

    return {
        "score": route["score"],
        "root": build_molecule_node(root_smiles, set()),
    }
