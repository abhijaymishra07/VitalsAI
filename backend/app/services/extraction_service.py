import re
from datetime import datetime

from app.schemas.health import MetricPayload

LINE_METRIC_PATTERN = re.compile(
    r"^\s*(?P<name>[A-Za-z][A-Za-z0-9\- /%\.]{1,40}?)\s*[:=]\s*(?P<value>\d+\.?\d*)\s*(?P<unit>[A-Za-z/%μ\^0-9\.\-]+)?\s*(?:\((?:<?)?(?P<ref_min>\d+\.?\d*)\s*[-–]\s*(?P<ref_max>\d+\.?\d*)\))?\s*$",
    flags=re.IGNORECASE,
)

INLINE_METRIC_PATTERN = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9\- /%\.]{2,35}?)\s*[:=]\s*(?P<value>\d+\.?\d*)\s*(?P<unit>[A-Za-z/%μ\^0-9\.\-]+)?\s*\((?:<?)?(?P<ref_min>\d+\.?\d*)\s*[-–]\s*(?P<ref_max>\d+\.?\d*)\)",
    flags=re.IGNORECASE,
)

UPPER_ONLY_PATTERN = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9\- /%\.]{2,35}?)\s*[:=]\s*(?P<value>\d+\.?\d*)\s*(?P<unit>[A-Za-z/%μ\^0-9\.\-]+)?\s*\(\s*<\s*(?P<ref_max>\d+\.?\d*)\s*\)",
    flags=re.IGNORECASE,
)

LOOSE_LINE_PATTERN = re.compile(
    r"^\s*(?P<name>[A-Za-z][A-Za-z0-9\- /%\.]{2,35}?)\s*[:=]\s*(?P<value>\d+\.?\d*)\s*(?P<unit>[A-Za-z/%μ\^0-9\.\-]+)?\s*$",
    flags=re.IGNORECASE,
)

STACKED_REF_LINE = re.compile(
    r"^(?:\*)?\s*(?P<ref_min>\d+(?:\.\d+)?)\s*[-–]\s*(?P<ref_max>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z%/µμ\.\-]+)?\s*(?:\*)?\s*$",
    flags=re.IGNORECASE,
)

STACKED_VALUE_LINE = re.compile(
    r"^(?:\*)?\s*(?P<value>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:\*)?\s*$",
)

VITAL_PATTERN = re.compile(
    r"^(?P<name>Weight|Height|BMI|Pulse|SpO2|Temperature|Systolic|Diastolic)\s*:?\s*(?P<value>\d+\.?\d*)\s*(?P<unit>[A-Za-z%/°]+)?\s*$",
    flags=re.IGNORECASE,
)

INVALID_METRIC_NAME = re.compile(
    r"sample collected|age/gender|patient name|phone no|email|disclaimer|your name|purpose of visit",
    flags=re.IGNORECASE,
)

SKIP_LINE_PATTERN = re.compile(
    r"description:|^apollo\b|disclaimer|sample collected|phone\b|email:|^dear\b|thank you|"
    r"parameters$|report name|note:|info:|purpose of visit|risk score|acceptable score|"
    r"^[0-9\.]+$|^\*$|^%$|^mg/dL$|^ng/mL$|^pg/mL$|^U/L$|^g/dL$|^fL$|^mmol/L$",
    flags=re.IGNORECASE,
)

MIN_PARSE_TEXT_CHARS = 80

LAB_PREVIEW_MARKERS = (
    "lab panel results",
    "lab parameters needing attention",
    "complete blood count",
    "lipid profile",
    "total cholesterol",
    "renal profile",
    "liver function test",
)


class MedicalExtractionService:
    @staticmethod
    def detect_language(_text: str) -> str:
        return "en"

    @staticmethod
    def normalize_text(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = []
        for line in text.splitlines():
            cleaned = re.sub(r"\s+", " ", line.strip())
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines)

    @staticmethod
    def lab_text_preview(text: str, max_len: int = 800) -> str:
        lower = text.lower()
        for marker in LAB_PREVIEW_MARKERS:
            idx = lower.find(marker)
            if idx >= 0:
                return text[idx : idx + max_len]
        return text[:max_len]

    @staticmethod
    def _parse_value(raw: str) -> float:
        return float(raw.replace(",", ""))

    @staticmethod
    def _make_metric(
        name: str,
        value: float,
        unit: str = "",
        ref_min: float | None = None,
        ref_max: float | None = None,
    ) -> MetricPayload:
        is_abnormal = (ref_min is not None and value < ref_min) or (ref_max is not None and value > ref_max)
        return MetricPayload(
            metric_name=re.sub(r"\s+", " ", name.strip()).lower(),
            metric_value=value,
            unit=unit.strip(),
            reference_min=ref_min,
            reference_max=ref_max,
            is_abnormal=is_abnormal,
            observed_at=datetime.utcnow(),
        )

    @staticmethod
    def _metric_key(metric: MetricPayload) -> str:
        return f"{metric.metric_name}:{metric.metric_value}"

    @staticmethod
    def _add_metric(metrics: list[MetricPayload], seen: set[str], metric: MetricPayload) -> None:
        if INVALID_METRIC_NAME.search(metric.metric_name):
            return
        key = MedicalExtractionService._metric_key(metric)
        if key in seen:
            return
        seen.add(key)
        metrics.append(metric)

    @staticmethod
    def _build_metric_from_match(match: re.Match) -> MetricPayload:
        ref_min = float(match.group("ref_min")) if match.groupdict().get("ref_min") else None
        ref_max = float(match.group("ref_max")) if match.groupdict().get("ref_max") else None
        value = float(match.group("value"))
        name = re.sub(r"\s+", " ", match.group("name").strip()).lower()
        return MedicalExtractionService._make_metric(
            name,
            value,
            unit=(match.group("unit") or "").strip(),
            ref_min=ref_min,
            ref_max=ref_max,
        )

    @staticmethod
    def _is_skipped_line(line: str) -> bool:
        return bool(SKIP_LINE_PATTERN.search(line)) or line.lower().startswith("description")

    @staticmethod
    def _looks_like_metric_name(line: str) -> bool:
        if MedicalExtractionService._is_skipped_line(line):
            return False
        if len(line) < 2 or len(line) > 80:
            return False
        if line.endswith("."):
            return False
        if STACKED_REF_LINE.match(line) or STACKED_VALUE_LINE.match(line):
            return False
        letters = sum(c.isalpha() for c in line)
        if letters < 2:
            return False
        upper_ratio = sum(c.isupper() for c in line if c.isalpha()) / max(letters, 1)
        return upper_ratio > 0.6 or (line.upper() == line and re.search(r"[A-Z]", line))

    @staticmethod
    def _find_stacked_value_index(lines: list[str], ref_index: int) -> int | None:
        j = ref_index - 1
        while j >= 0 and j >= ref_index - 6:
            line = lines[j]
            if STACKED_VALUE_LINE.match(line):
                return j
            if MedicalExtractionService._is_skipped_line(line):
                j -= 1
                continue
            break
        return None

    @staticmethod
    def _extract_colon_metrics(text: str, seen: set[str]) -> list[MetricPayload]:
        metrics: list[MetricPayload] = []
        for line in text.splitlines():
            for pattern in (LINE_METRIC_PATTERN, UPPER_ONLY_PATTERN, LOOSE_LINE_PATTERN, VITAL_PATTERN):
                match = pattern.match(line)
                if match:
                    MedicalExtractionService._add_metric(metrics, seen, MedicalExtractionService._build_metric_from_match(match))
                    break

        if len(metrics) < 3:
            for pattern in (INLINE_METRIC_PATTERN, UPPER_ONLY_PATTERN):
                for match in pattern.finditer(text):
                    MedicalExtractionService._add_metric(metrics, seen, MedicalExtractionService._build_metric_from_match(match))
        return metrics

    @staticmethod
    def _extract_stacked_metrics(text: str, seen: set[str]) -> list[MetricPayload]:
        lines = text.splitlines()
        metrics: list[MetricPayload] = []

        for i, line in enumerate(lines):
            ref_match = STACKED_REF_LINE.match(line)
            if not ref_match:
                continue

            value_index = MedicalExtractionService._find_stacked_value_index(lines, i)
            if value_index is None:
                continue

            value_match = STACKED_VALUE_LINE.match(lines[value_index])
            if not value_match:
                continue

            name_parts: list[str] = []
            j = value_index - 1
            while j >= 0 and len(name_parts) < 4:
                prev = lines[j]
                if STACKED_VALUE_LINE.match(prev) or STACKED_REF_LINE.match(prev):
                    break
                if MedicalExtractionService._is_skipped_line(prev):
                    j -= 1
                    continue
                if MedicalExtractionService._looks_like_metric_name(prev):
                    name_parts.insert(0, prev)
                    j -= 1
                else:
                    break

            if not name_parts:
                continue

            metric = MedicalExtractionService._make_metric(
                " ".join(name_parts),
                MedicalExtractionService._parse_value(value_match.group("value")),
                unit=(ref_match.group("unit") or "").strip(),
                ref_min=float(ref_match.group("ref_min")),
                ref_max=float(ref_match.group("ref_max")),
            )
            MedicalExtractionService._add_metric(metrics, seen, metric)

        return metrics

    @staticmethod
    def extract_metrics(text: str) -> list[MetricPayload]:
        text = MedicalExtractionService.normalize_text(text)
        seen: set[str] = set()
        metrics = MedicalExtractionService._extract_colon_metrics(text, seen)
        stacked = MedicalExtractionService._extract_stacked_metrics(text, seen)
        metrics.extend(stacked)
        return metrics

    @staticmethod
    def build_parse_hint(metric_count: int, text_chars: int, extraction_method: str) -> str:
        if metric_count > 0:
            return f"Extracted {metric_count} lab values from report."

        if extraction_method in {"pdf_needs_tesseract", "image_needs_tesseract"}:
            return (
                "Could not read this file — Tesseract OCR is not installed on the server. "
                "Run: sudo apt install tesseract-ocr tesseract-ocr-eng"
            )

        if extraction_method == "pdf_unreadable":
            return "PDF could not be read. It may be password-protected or corrupted."

        if text_chars < MIN_PARSE_TEXT_CHARS:
            if extraction_method.startswith("pdf"):
                return (
                    "Almost no text found in this PDF — it is likely a scanned image. "
                    "Install Tesseract OCR or upload a .txt export of your report."
                )
            return "No readable text found in this file."

        return (
            f"Read {text_chars} characters but no lab values matched our parser. "
            "Try exporting the report as .txt or ensure lines look like: Hb : 11.2 g/dL (13.0-17.0)"
        )
