# Backend API Service

This service manages retrosynthesis search requests, coordinates with the microservice, and stores/retrieves results.

## API

All request/response schemas are defined in [models.py](models.py).

### POST /api/search

Creates a new retrosynthesis search. Should initiate an async request to the microservice's `/start_search` endpoint.

- **Request**: `SearchCreateRequest`
- **Response**: `SearchCreateResponse`

### GET /api/search/{id}/status

Returns the current status of a search.

- **Response**: `SearchStatusResponse`

### GET /api/search/{id}/results

Returns search results ordered by score (descending) with optional filtering.

- **Query Parameters**: `min_score` (float, optional) - filter routes by minimum score
- **Response**: `SearchResultsResponse`

### POST /api/search/{id}/update

Callback endpoint for the microservice to post incremental results. Accepts and persists routes to the database.

- **Request**: `SearchUpdate`
- **Response**: `UpdateResponse`


## Requirements

- **Web Framework**: Choose any framework (FastAPI, Flask, Django, etc.)
- **Persistence Layer**: Required - use any database/ORM (PostgreSQL, SQLite, etc.)
- **API Contract**: See [models.py](models.py) for request/response schemas
- **Business Logic**: [retrosynthesis_search.py](retrosynthesis_search.py) contains helper functions for processing routes - use as much or as little as you'd like
