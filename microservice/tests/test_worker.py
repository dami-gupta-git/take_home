"""
Tests for the background worker, including the error path.
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.anyio
async def test_worker_posts_error_callback_on_exception():
    """If get_routes raises, worker must post a final callback with error_message set."""
    mock_client = AsyncMock()
    callback_url = "http://backend/api/search/123/update"

    with (
        patch("app.worker.get_routes", side_effect=RuntimeError("search exploded")),
        patch("app.worker.http") as mock_http,
    ):
        mock_http.client = mock_client

        from app.worker import run_search
        await run_search("CCO", callback_url)

    mock_client.post.assert_awaited_once()
    _, kwargs = mock_client.post.call_args
    payload = kwargs["json"]
    assert payload["is_complete"] is True
    assert payload["error_message"] is not None
    assert payload["routes"] == []
