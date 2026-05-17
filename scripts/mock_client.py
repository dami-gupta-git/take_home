import argparse
import sys
import time
from typing import Any

import requests


class RetrosynthesisClient:

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def create_search(self, smiles: str) -> str:
        response = self.session.post(
            f"{self.base_url}/api/search", json={"smiles": smiles}
        )
        response.raise_for_status()
        data = response.json()
        return data["id"]

    def get_search_status(self, search_id: str) -> dict[str, Any]:
        response = self.session.get(f"{self.base_url}/api/search/{search_id}/status")
        response.raise_for_status()
        return response.json()

    def get_search_results(
        self, search_id: str, min_score: float | None = None
    ) -> dict[str, Any]:
        params = {}
        if min_score is not None:
            params["min_score"] = min_score

        response = self.session.get(
            f"{self.base_url}/api/search/{search_id}/results", params=params
        )
        response.raise_for_status()
        return response.json()

    def poll_until_complete(self, search_id: str, timeout: int = 60) -> dict[str, Any]:
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_search_status(search_id)

            print(f"Status: {status['status']}")

            if status["status"] in ["completed", "failed"]:
                return status

            time.sleep(2)

        raise TimeoutError(f"Search did not complete within {timeout} seconds")


def count_tree_molecules(
    node: dict[str, Any], visited: set[str] | None = None
) -> tuple[int, int]:
    if visited is None:
        visited = set()

    smiles = node["smiles"]
    if smiles in visited:
        return 0, 0

    visited.add(smiles)
    total = 1
    purchasable = 1 if node["is_purchasable"] else 0

    for reaction in node["reactions"]:
        for reactant in reaction["reactants"]:
            sub_total, sub_purchasable = count_tree_molecules(reactant, visited)
            total += sub_total
            purchasable += sub_purchasable

    return total, purchasable


def count_steps(node: dict[str, Any]) -> int:
    if not node["reactions"]:
        return 0

    max_depth = 0
    for reaction in node["reactions"]:
        for reactant in reaction["reactants"]:
            depth = count_steps(reactant)
            max_depth = max(max_depth, depth)

    return max_depth + 1


def display_results(results: dict[str, Any], max_routes: int = 5) -> None:
    print(f"\nFound {results['total_routes']} routes")

    for i, route in enumerate(results["routes"][:max_routes], 1):
        print(f"\nRoute {i}:")
        print(f"  Score: {route['score']:.4f}")
        print(f"  Target: {route['root']['smiles']}")

        total_molecules, purchasable_molecules = count_tree_molecules(route["root"])
        steps = count_steps(route["root"])
        print(f"  Steps: {steps}")
        print(f"  Molecules: {total_molecules} ({purchasable_molecules} purchasable)")

    if results["total_routes"] > max_routes:
        print(f"\n({results['total_routes'] - max_routes} more routes not shown)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the retrosynthesis backend API")
    parser.add_argument("smiles", help="SMILES string of target molecule")
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend API URL",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        help="Minimum route score to retrieve",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds",
    )

    args = parser.parse_args()
    client = RetrosynthesisClient(args.backend_url)

    try:
        print(f"Starting search for: {args.smiles}")
        search_id = client.create_search(args.smiles)
        print(f"Search ID: {search_id}")

        print(f"\nPolling for completion (timeout: {args.timeout}s)...")
        final_status = client.poll_until_complete(search_id, timeout=args.timeout)

        if final_status["status"] == "failed":
            print(f"Search failed: {final_status.get('error_message')}")
            sys.exit(1)

        print("\nRetrieving results...")
        results = client.get_search_results(search_id, min_score=args.min_score)
        display_results(results)

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {args.backend_url}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
