from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from markdownify import markdownify as md


def _normalize_image_sources(soup: BeautifulSoup, base_url: str | None) -> None:
    if not base_url:
        return
    for image in soup.find_all("img"):
        source = image.get("src")
        if source:
            image["src"] = urljoin(base_url, source)


def _replace_math_scripts(soup: BeautifulSoup) -> None:
    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").lower()
        if "math/tex" not in script_type:
            continue
        formula = script.get_text(strip=True)
        if not formula:
            script.decompose()
            continue
        if "mode=display" in script_type:
            script.replace_with(f"\n\n$${formula}$$\n\n")
        else:
            script.replace_with(f"${formula}$")


def _unwrap_heading_links(soup: BeautifulSoup) -> None:
    for heading in soup.find_all(re.compile("^h[1-6]$")):
        links = heading.find_all("a", recursive=False)
        if len(links) == 1 and heading.get_text(" ", strip=True) == links[0].get_text(" ", strip=True):
            links[0].replace_with(links[0].get_text(" ", strip=True))


def _clean_markdown(markdown: str) -> str:
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    return markdown.strip() + "\n"


def html_to_markdown(html: str, base_url: str | None = None) -> str:
    soup = BeautifulSoup(html, "html.parser")
    _replace_math_scripts(soup)
    _unwrap_heading_links(soup)
    _normalize_image_sources(soup, base_url)
    markdown = md(
        str(soup),
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"],
    )
    return _clean_markdown(markdown)
