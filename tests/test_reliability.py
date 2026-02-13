"""Unit tests for retry logic and rate limiting."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from saiten_mcp.server import RateLimiter


# ---------------------------------------------------------------------------
# Rate Limiter tests
# ---------------------------------------------------------------------------
class TestRateLimiter:
    """Tests for the sliding-window rate limiter."""

    def test_allows_within_limit(self):
        rl = RateLimiter(max_calls=5, window_seconds=60.0)
        for _ in range(5):
            rl.check("test_tool")  # Should not raise

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_calls=3, window_seconds=60.0)
        for _ in range(3):
            rl.check("test_tool")
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            rl.check("test_tool")

    def test_separate_tools_independent(self):
        rl = RateLimiter(max_calls=2, window_seconds=60.0)
        rl.check("tool_a")
        rl.check("tool_a")
        # tool_a is at limit, but tool_b should still work
        rl.check("tool_b")
        with pytest.raises(ValueError):
            rl.check("tool_a")

    def test_reset_clears_all(self):
        rl = RateLimiter(max_calls=1, window_seconds=60.0)
        rl.check("test_tool")
        with pytest.raises(ValueError):
            rl.check("test_tool")
        rl.reset()
        rl.check("test_tool")  # Should work after reset

    def test_error_message_contains_tool_name(self):
        rl = RateLimiter(max_calls=1, window_seconds=60.0)
        rl.check("my_tool")
        with pytest.raises(ValueError, match="my_tool"):
            rl.check("my_tool")


# ---------------------------------------------------------------------------
# Retry logic tests
# ---------------------------------------------------------------------------
class TestRetryLogic:
    """Tests for the gh CLI retry mechanism."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        """Normal execution should not retry."""
        from saiten_mcp.tools.submissions import _run_gh

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _run_gh("api", "test")

        assert result == "output"

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit(self):
        """Rate limit errors (429) should trigger retry."""
        from saiten_mcp.tools.submissions import _run_gh

        # First call: fails with rate limit, second call: succeeds
        fail_proc = AsyncMock()
        fail_proc.returncode = 1
        fail_proc.communicate = AsyncMock(
            return_value=(b"", b"HTTP 429: rate limit exceeded")
        )

        success_proc = AsyncMock()
        success_proc.returncode = 0
        success_proc.communicate = AsyncMock(return_value=(b"ok", b""))

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return fail_proc if call_count == 1 else success_proc

        with (
            patch("asyncio.create_subprocess_exec", side_effect=mock_exec),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await _run_gh("api", "test", max_retries=3)

        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_fails_fast_on_non_retryable(self):
        """Non-retryable errors should fail immediately."""
        from saiten_mcp.tools.submissions import _run_gh

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"Not Found (HTTP 404)")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="gh command failed"):
                await _run_gh("api", "test", max_retries=3)

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        """After max retries, should raise the last error."""
        from saiten_mcp.tools.submissions import _run_gh

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"HTTP 500 Internal Server Error")
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(RuntimeError, match="gh command failed"):
                await _run_gh("api", "test", max_retries=2)

    @pytest.mark.asyncio
    async def test_gh_not_found(self):
        """Missing gh CLI should give a helpful error message."""
        from saiten_mcp.tools.submissions import _run_gh

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("gh not found"),
        ):
            with pytest.raises(RuntimeError, match="gh CLI not found"):
                await _run_gh("api", "test")
