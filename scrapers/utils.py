from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup


def fetch_html(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BankAnalizBot/1.0)"}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def extract_section(text: str, start_heading: str, end_heading: str | None) -> str:
    start_idx = text.find(start_heading)
    if start_idx == -1:
        return ""
    start_idx += len(start_heading)
    if end_heading:
        end_idx = text.find(end_heading, start_idx)
        if end_idx == -1:
            end_idx = len(text)
    else:
        end_idx = len(text)
    return text[start_idx:end_idx]


def extract_percentages(text: str) -> list[float]:
    matches = re.findall(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%", text)
    values = [float(m.replace(",", ".")) for m in matches]
    seen: list[float] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


def extract_term_months(text: str) -> list[int]:
    matches = re.findall(r"(\d{1,3})\s*oy", text)
    values = sorted({int(m) for m in matches if int(m) <= 120})
    return values


def extract_amount_som(text: str) -> int | None:
    mln_matches = re.findall(r"(\d{1,5})\s*mln\.?\s*so", text, flags=re.IGNORECASE)
    mlrd_matches = re.findall(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*mlrd\.?\s*so", text, flags=re.IGNORECASE)
    amounts = [int(m) * 1_000_000 for m in mln_matches]
    amounts += [int(float(m.replace(",", "."))) * 1_000_000_000 for m in mlrd_matches]
    return max(amounts) if amounts else None


def has_collateral_requirement(text: str) -> bool:
    lowered = text.lower()
    if "mavjud emas" in lowered or "garovsiz" in lowered:
        return False
    return "garov" in lowered
