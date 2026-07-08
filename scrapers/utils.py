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


_TERM_RANGE_RE = re.compile(r"(\d{1,3})\s*oydan\s*(\d{1,3})\s*oygacha")
_TERM_SINGLE_RE = re.compile(r"(\d{1,3})\s*oygacha")


def extract_term_months(text: str) -> list[int]:
    """Muddat oralig'ini "N oydan M oygacha" (masalan, "12 oydan 60 oygacha")
    range shaklidan topadi. Agar range topilmasa, yagona "N oygacha"
    ko'rsatkichiga tushadi.

    Range topilganda undan tashqaridagi bitta "N oygacha" iboralari (masalan,
    "Imtiyozli davr: 6 oygacha" kabi imtiyozli davr ko'rsatkichlari) e'tiborga
    olinmaydi — aks holda ular asosiy muddat oralig'iga aralashib, noto'g'ri
    term_min/term_max qiymatlarini keltirib chiqaradi.
    """
    range_matches = _TERM_RANGE_RE.findall(text)
    if range_matches:
        values = {int(lo) for lo, hi in range_matches} | {int(hi) for lo, hi in range_matches}
    else:
        values = {int(m) for m in _TERM_SINGLE_RE.findall(text)}
    return sorted(v for v in values if v <= 120)


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
