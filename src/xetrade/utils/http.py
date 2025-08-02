# src/utils/http.py
from __future__ import annotations
import asyncio
import json
import time
from typing import Any, Dict, Optional

import aiohttp

DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.5  # seconds, exponential

class HTTPClient:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure(self):
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=None, sock_connect=DEFAULT_TIMEOUT, sock_read=DEFAULT_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get_json(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retries: int = DEFAULT_RETRIES,
        backoff: float = DEFAULT_BACKOFF,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Any:
        await self._ensure()
        attempt = 0
        last_err: Exception | None = None

        while attempt <= retries:
            try:
                async with self._session.get(url, params=params, headers=headers, timeout=timeout) as resp:
                    if resp.status == 429:
                        # rate limited; honor Retry-After if present
                        ra = resp.headers.get("Retry-After")
                        delay = float(ra) if ra else backoff * (2 ** attempt)
                        await asyncio.sleep(delay)
                        attempt += 1
                        continue
                    if 200 <= resp.status < 300:
                        ctype = resp.headers.get("Content-Type", "")
                        if "application/json" in ctype:
                            return await resp.json()
                        text = await resp.text()
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            raise RuntimeError(f"Expected JSON from {url}, got: {ctype}")
                    # transient server/network errors => retry
                    if resp.status in (500, 502, 503, 504):
                        await asyncio.sleep(backoff * (2 ** attempt))
                        attempt += 1
                        continue
                    # other HTTP errors => raise
                    text = await resp.text()
                    raise RuntimeError(f"HTTP {resp.status} for {url}: {text[:200]}")
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_err = e
                if attempt >= retries:
                    break
                await asyncio.sleep(backoff * (2 ** attempt))
                attempt += 1

        raise RuntimeError(f"Request failed after {retries+1} attempts: {last_err}")

# single shared instance
http = HTTPClient()

# convenience function
async def get_json(*args, **kwargs) -> Any:
    return await http.get_json(*args, **kwargs)
