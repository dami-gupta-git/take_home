from unittest.mock import patch

from get_routes import load_example_routes, get_routes


def test_load_example_routes():
    routes = load_example_routes()

    assert isinstance(routes, list)
    assert len(routes) > 0
    assert "score" in routes[0]
    assert "molecules" in routes[0]
    assert "reactions" in routes[0]


def test_get_routes():
    mock_routes = [
        {
            "score": 0.9995,
            "molecules": [
                {
                    "smiles": "A",
                    "catalog_entries": [],
                },
                {
                    "smiles": "B",
                    "catalog_entries": [
                        {
                            "vendor_id": "VENDOR-1",
                            "catalog_name": "catalog_1",
                            "lead_time_weeks": 12.0,
                        }
                    ],
                },
            ],
            "reactions": [
                {
                    "name": "Reaction1",
                    "target": "A",
                    "sources": ["B", "C"],
                }
            ],
        },
        {
            "score": 0.8201,
            "molecules": [
                {"smiles": "D", "catalog_entries": []},
                {"smiles": "E", "catalog_entries": []},
            ],
            "reactions": [
                {
                    "name": "Reaction2",
                    "target": "F",
                    "sources": ["D", "G"],
                }
            ],
        },
        {
            "score": 0.7543,
            "molecules": [
                {
                    "smiles": "H",
                    "catalog_entries": [
                        {
                            "vendor_id": "VENDOR-2",
                            "catalog_name": "catalog_2",
                            "lead_time_weeks": 0.0,
                        }
                    ],
                }
            ],
            "reactions": [],
        },
    ]

    with patch("get_routes.load_example_routes", return_value=mock_routes):
        batches = list(get_routes("CCO", batch_size=1))

        assert len(batches) == 3

        batch1, is_last1 = batches[0]
        assert len(batch1) == 1
        assert is_last1 is False

        batch2, is_last2 = batches[1]
        assert len(batch2) == 1
        assert is_last2 is False

        batch3, is_last3 = batches[2]
        assert len(batch3) == 1
        assert is_last3 is True
