from __future__ import annotations

import asyncio
import ipaddress
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None


class WebFetcher:
    USER_AGENT = "Jarvis Assistant Bot 1.0"

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def fetch_page(self, url: str) -> dict[str, Any]:
        self._validate_url(url)

        headers = {"User-Agent": self.USER_AGENT}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
        except httpx.TimeoutException:
            return self._error_payload(url, "Page took too long to load")
        except httpx.HTTPError:
            return self._error_payload(url, "Unable to fetch page")

        if response.status_code == 404:
            return self._error_payload(url, "Page not found")
        if response.status_code >= 400:
            return self._error_payload(url, f"HTTP {response.status_code}")

        html = response.text
        title, content = self._extract_content(html)

        words = content.split()
        truncated = False
        if len(words) > 5000:
            content = " ".join(words[:5000]) + " ..."
            truncated = True

        return {
            "title": title,
            "content": content,
            "url": str(response.url),
            "word_count": min(len(words), 5000),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "truncated": truncated,
        }

    async def fetch_multiple(self, urls: list[str], max_concurrent: int = 3) -> list[dict[str, Any]]:
        unique_urls = list(dict.fromkeys(urls))[:3]
        semaphore = asyncio.Semaphore(max(1, max_concurrent))

        async def _worker(target: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    return await self.fetch_page(target)
                except Exception as exc:
                    return self._error_payload(target, str(exc))

        tasks = [asyncio.create_task(_worker(url)) for url in unique_urls]
        return await asyncio.gather(*tasks)

    def _extract_content(self, html: str) -> tuple[str, str]:
        title = "Untitled"
        content = ""

        try:
            from readability import Document

            doc = Document(html)
            title = (doc.short_title() or "Untitled").strip()
            summary_html = doc.summary(html_partial=True)
            content = self._html_to_text(summary_html)
            if content.strip():
                return title, content
        except Exception:
            pass

        if BeautifulSoup is None:
            title = self._simple_title(html)
            return title, self._simple_text(html)

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.text:
            title = soup.title.text.strip()

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        chunks: list[str] = []
        for node in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            text = node.get_text(" ", strip=True)
            if text:
                chunks.append(text)
        content = "\n".join(chunks)
        return title, content

    def _html_to_text(self, html: str) -> str:
        if BeautifulSoup is None:
            return self._simple_text(html)
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
        chunks: list[str] = []
        for node in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            text = node.get_text(" ", strip=True)
            if text:
                chunks.append(text)
        return "\n".join(chunks)

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only HTTP/HTTPS URLs are allowed")

        host = parsed.hostname
        if not host:
            raise ValueError("Invalid URL host")

        self._assert_public_host(host)

    def _assert_public_host(self, host: str) -> None:
        try:
            addresses = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise ValueError(f"Unable to resolve host: {host}") from exc

        for entry in addresses:
            ip_str = entry[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                raise ValueError("Blocked URL: private/local addresses are not allowed")

    def _error_payload(self, url: str, message: str) -> dict[str, Any]:
        return {
            "title": "",
            "content": "",
            "url": url,
            "word_count": 0,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "error": message,
        }

    def _simple_text(self, html: str) -> str:
        text = html
        for tag in ("script", "style"):
            while True:
                start = text.lower().find(f"<{tag}")
                if start == -1:
                    break
                end = text.lower().find(f"</{tag}>", start)
                if end == -1:
                    text = text[:start]
                    break
                text = text[:start] + text[end + len(tag) + 3 :]

        out = []
        in_tag = False
        for char in text:
            if char == "<":
                in_tag = True
                out.append(" ")
                continue
            if char == ">":
                in_tag = False
                continue
            if not in_tag:
                out.append(char)

        return " ".join("".join(out).split())

    def _simple_title(self, html: str) -> str:
        lower = html.lower()
        start = lower.find("<title>")
        end = lower.find("</title>")
        if start != -1 and end != -1 and end > start:
            return html[start + 7 : end].strip() or "Untitled"
        return "Untitled"
