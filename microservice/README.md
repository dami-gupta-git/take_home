# Retrosynthesis Microservice

This microservice simulates a retrosynthesis search that generates synthetic routes for a given molecule. It processes routes from test data and posts results incrementally to the backend.

## API

All request/response schemas are defined in [models.py](models.py).

### POST /start_search

Accepts a search request and asynchronously posts route batches to the callback URL.

- **Request**: `SearchRequest`
- **Response**: 202 Accepted

**Expected Behavior:**
1. Load routes from `data/example_routes.json` using `get_routes(smiles, batch_size)`
2. POST each batch to the callback URL as `SearchUpdate`
3. Simulate processing latency between batches (e.g., 0.5-2 seconds per batch)
4. Set `is_complete: true` on the final batch
