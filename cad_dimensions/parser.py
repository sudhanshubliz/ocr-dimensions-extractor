from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .models import DimensionRow


PAIR_RE = re.compile(
    r"(?P<prefix>R|max|Rmax|Ø|⌀|dia|diam)?\s*"
    r"(?P<nom>\(?\d+(?:[.,]\d+)?\)?)\s*"
    r"(?P<sign>±|\+/-|\+|/)\s*"
    r"(?P<tol>\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
UNILATERAL_RE = re.compile(
    r"(?P<nom>\d+(?:[.,]\d+)?)\s*\+\s*(?P<up>\d+(?:[.,]\d+)?)\s*(?:-|/-|/)\s*(?P<dn>\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
REFERENCE_RE = re.compile(r"\((?P<nom>\d+(?:[.,]\d+)?)\)")
MULT_RE = re.compile(r"\((?P<count>\d{1,2})\s*x\)|(?P<count2>\d{1,2})\s*x", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedDimension:
    row: DimensionRow
    raw_text: str


def _to_decimal(text: str) -> Decimal | None:
    cleaned = text.strip().strip("()").replace(",", ".")
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _repair_tolerance(raw: str, value: Decimal) -> Decimal:
    cleaned = raw.strip().replace(",", ".")
    if "." not in cleaned and cleaned.startswith("0") and len(cleaned) > 1:
        return Decimal(cleaned) / (Decimal(10) ** (len(cleaned) - 1))
    return value


def _repair_nominal(raw: str, nominal: Decimal, tolerance: Decimal, text: str) -> Decimal:
    cleaned = raw.strip().strip("()")
    if "," in cleaned or "." in cleaned:
        return nominal
    if nominal >= 1000 and tolerance < 1:
        return nominal / Decimal("10")
    if nominal >= 100 and tolerance < 1 and re.search(r"\b0[1-9]\b", text):
        # Low-confidence OCR repair: 115 +08 often means 11,5 +0,8 in these plots.
        return nominal / Decimal("10")
    return nominal


def _multiplicity(text: str) -> int | None:
    match = MULT_RE.search(text)
    if not match:
        return None
    return int(match.group("count") or match.group("count2"))


def _accuracy(raw_nominal: str, raw_tolerance: str, repaired: bool, avg_conf: int) -> int:
    score = max(30, min(89, avg_conf))
    if repaired:
        score = min(score, 72)
    if "," in raw_nominal or "." in raw_nominal:
        score = min(89, score + 5)
    if "," in raw_tolerance or "." in raw_tolerance:
        score = min(89, score + 5)
    return int(score)


def parse_dimensions(text: str, zone: str, avg_conf: int = 70) -> list[ParsedDimension]:
    out: list[ParsedDimension] = []
    normalized = text.replace("£", "±").replace("—", "-").replace("–", "-")
    multiplicity = _multiplicity(normalized)
    consumed_spans: list[tuple[int, int]] = []

    for match in UNILATERAL_RE.finditer(normalized):
        nom = _to_decimal(match.group("nom"))
        up = _to_decimal(match.group("up"))
        dn = _to_decimal(match.group("dn"))
        if nom is None or up is None or dn is None:
            continue
        up = _repair_tolerance(match.group("up"), up)
        dn = _repair_tolerance(match.group("dn"), dn)
        out.append(ParsedDimension(
            DimensionRow(zone, nom, f"+{up}/-{dn}", max(up, dn), dn, up, multiplicity, min(90, avg_conf), "ocr"),
            match.group(0),
        ))
        consumed_spans.append(match.span())

    for match in PAIR_RE.finditer(normalized):
        if any(match.start() < end and match.end() > start for start, end in consumed_spans):
            continue
        nom = _to_decimal(match.group("nom"))
        tol = _to_decimal(match.group("tol"))
        if nom is None or tol is None:
            continue
        raw_nom = match.group("nom")
        raw_tol = match.group("tol")
        tol2 = _repair_tolerance(raw_tol, tol)
        nom2 = _repair_nominal(raw_nom, nom, tol2, normalized)
        repaired = nom2 != nom or tol2 != tol
        if nom2 <= 0 or tol2 < 0:
            continue
        if tol2 > max(nom2 * Decimal("0.6"), Decimal("10")):
            continue
        prefix = (match.group("prefix") or "").lower()
        tolerance_text = f"+/-{tol2}"
        source = "ocr"
        accuracy = _accuracy(raw_nom, raw_tol, repaired, avg_conf)
        if prefix in {"rmax", "max"}:
            tolerance_text = "Rmax"
            source = "ocr_reference"
        out.append(ParsedDimension(
            DimensionRow(zone, nom2, tolerance_text, tol2, tol2, tol2, multiplicity, accuracy, source),
            match.group(0),
        ))

    # Reference dimensions are useful but should remain review-level confidence.
    for match in REFERENCE_RE.finditer(normalized):
        nom = _to_decimal(match.group("nom"))
        if nom is None or nom <= 0:
            continue
        out.append(ParsedDimension(
            DimensionRow(zone, nom, "Reference", None, None, None, multiplicity, min(70, avg_conf), "ocr_reference"),
            match.group(0),
        ))
    return out
