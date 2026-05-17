import pytest
from retrosynthesis_search import (
    RouteData,
    update_search_progress,
    SearchStatus,
    build_retrosynthesis_tree,
    CurrentSearchData,
)


def test_update_search_progress_with_new_results():
    current_data: CurrentSearchData = {"status": "pending"}

    new_results: list[RouteData] = [
        {"score": 0.9, "molecules": [], "reactions": []},
        {"score": 0.8, "molecules": [], "reactions": []},
    ]

    updates = update_search_progress(
        current_data=current_data,
        new_results=new_results,
        is_complete=False,
        error_message=None,
    )

    assert updates["status"] == SearchStatus.IN_PROGRESS
    assert "updated_at" in updates
    assert updates.get("error_message") is None


def test_build_retrosynthesis_tree_one_step():
    route: RouteData = {
        "score": 0.95,
        "molecules": [
            {"smiles": "A", "catalog_entries": []},
            {
                "smiles": "B",
                "catalog_entries": [
                    {
                        "vendor_id": "V1",
                        "catalog_name": "Sigma",
                        "lead_time_weeks": 1.0,
                    }
                ],
            },
            {
                "smiles": "C",
                "catalog_entries": [
                    {
                        "vendor_id": "V2",
                        "catalog_name": "Sigma",
                        "lead_time_weeks": 1.0,
                    }
                ],
            },
        ],
        "reactions": [
            {"name": "Reduction", "target": "A", "sources": ["B", "C"]},
        ],
    }

    tree = build_retrosynthesis_tree(route)

    assert tree["root"]["smiles"] == "A"
    assert len(tree["root"]["reactions"]) == 1
    assert tree["root"]["reactions"][0]["name"] == "Reduction"
    assert len(tree["root"]["reactions"][0]["reactants"]) == 2


def test_build_retrosynthesis_tree_two_step():
    route: RouteData = {
        "score": 0.88,
        "molecules": [
            {"smiles": "A", "catalog_entries": []},
            {"smiles": "B", "catalog_entries": []},
            {
                "smiles": "C",
                "catalog_entries": [
                    {
                        "vendor_id": "V1",
                        "catalog_name": "Vendor",
                        "lead_time_weeks": 1.0,
                    }
                ],
            },
            {
                "smiles": "D",
                "catalog_entries": [
                    {
                        "vendor_id": "V2",
                        "catalog_name": "Vendor",
                        "lead_time_weeks": 1.0,
                    }
                ],
            },
        ],
        "reactions": [
            {"name": "Step1", "target": "B", "sources": ["C", "D"]},
            {"name": "Step2", "target": "A", "sources": ["B"]},
        ],
    }

    tree = build_retrosynthesis_tree(route)

    assert tree["root"]["smiles"] == "A"
    assert len(tree["root"]["reactions"]) == 1
    assert tree["root"]["reactions"][0]["name"] == "Step2"

    intermediate = tree["root"]["reactions"][0]["reactants"][0]
    assert intermediate["smiles"] == "B"
    assert len(intermediate["reactions"]) == 1
    assert intermediate["reactions"][0]["name"] == "Step1"
    assert len(intermediate["reactions"][0]["reactants"]) == 2


def test_build_retrosynthesis_tree_reactant_appears_multiple_times():
    route: RouteData = {
        "score": 0.85,
        "molecules": [
            {"smiles": "A", "catalog_entries": []},
            {"smiles": "B", "catalog_entries": []},
            {
                "smiles": "C",
                "catalog_entries": [
                    {
                        "vendor_id": "V1",
                        "catalog_name": "Vendor",
                        "lead_time_weeks": 1.0,
                    }
                ],
            },
            {
                "smiles": "D",
                "catalog_entries": [
                    {
                        "vendor_id": "V2",
                        "catalog_name": "Vendor",
                        "lead_time_weeks": 1.0,
                    }
                ],
            },
        ],
        "reactions": [
            {"name": "Step1", "target": "B", "sources": ["C", "D"]},
            {"name": "Step2", "target": "A", "sources": ["B", "C"]},
        ],
    }

    tree = build_retrosynthesis_tree(route)

    assert tree["root"]["smiles"] == "A"
    assert len(tree["root"]["reactions"]) == 1
    step2_reactants = tree["root"]["reactions"][0]["reactants"]
    assert len(step2_reactants) == 2

    reactant_smiles = {r["smiles"] for r in step2_reactants}
    assert "B" in reactant_smiles
    assert "C" in reactant_smiles

    c_node = next(r for r in step2_reactants if r["smiles"] == "C")
    assert c_node["is_purchasable"]
    assert len(c_node["reactions"]) == 0

    b_node = next(r for r in step2_reactants if r["smiles"] == "B")
    assert len(b_node["reactions"]) == 1
    assert b_node["reactions"][0]["name"] == "Step1"

    b_reactants = b_node["reactions"][0]["reactants"]
    b_reactant_smiles = {r["smiles"] for r in b_reactants}
    assert "C" in b_reactant_smiles
    assert "D" in b_reactant_smiles


def test_build_retrosynthesis_tree_raises_on_invalid_tree():
    route: RouteData = {
        "score": 0.85,
        "molecules": [
            {"smiles": "A", "catalog_entries": []},
            {"smiles": "B", "catalog_entries": []},
            {
                "smiles": "C",
                "catalog_entries": [
                    {
                        "vendor_id": "V1",
                        "catalog_name": "Vendor",
                        "lead_time_weeks": 1.0,
                    }
                ],
            },
        ],
        "reactions": [
            {"name": "Step1", "target": "A", "sources": ["C"]},
            {"name": "Step2", "target": "B", "sources": ["C"]},
        ],
    }

    with pytest.raises(ValueError, match="multiple potential root smiles"):
        build_retrosynthesis_tree(route)

def test_build_retrosynthesis_tree_raises_on_cycle():
    route: RouteData = {
        "score": 0.75,
        "molecules": [
            {"smiles": "A", "catalog_entries": []},
            {"smiles": "B", "catalog_entries": []},
            {"smiles": "C", "catalog_entries": []},
        ],
        "reactions": [
            {"name": "Step1", "target": "A", "sources": ["B"]},
            {"name": "Step2", "target": "B", "sources": ["C"]},
            {"name": "Step3", "target": "C", "sources": ["B"]},
        ],
    }

    with pytest.raises(ValueError, match="Cycle detected"):
        build_retrosynthesis_tree(route)

def test_update_search_progress_completion():
    current_data: CurrentSearchData = {"status": "in_progress"}

    updates = update_search_progress(
        current_data=current_data, new_results=[], is_complete=True, error_message=None
    )

    assert updates["status"] == SearchStatus.COMPLETED
    assert updates.get("error_message") is None


def test_update_search_progress_with_error():
    current_data: CurrentSearchData = {"status": "in_progress"}

    error_msg = "Test error"
    updates = update_search_progress(
        current_data=current_data,
        new_results=[],
        is_complete=False,
        error_message=error_msg,
    )

    assert updates["status"] == SearchStatus.FAILED
    assert updates["error_message"] == error_msg


def test_update_search_progress_no_changes():
    current_data: CurrentSearchData = {"status": "pending"}

    updates = update_search_progress(
        current_data=current_data, new_results=[], is_complete=False, error_message=None
    )

    assert updates["status"] == SearchStatus.PENDING
    assert "updated_at" in updates
    assert updates.get("error_message") is None
