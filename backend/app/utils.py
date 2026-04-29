import json
import re
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
try:
    from .fields import FIELDS
except ImportError:
    from fields import FIELDS


_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
_MISSING_URL_VALUES = {"", "not found", "n/a", "na", "none", "null"}
_TARGET_DISCOVERY_URL_KEYS = (
    "program_url",
    "tuition_url",
    "faculty_url",
    "admissions_url",
)
_DISCOVERY_CONTEXT_URL_KEY = "context_urls"

_DEGREE_HINT_RE = re.compile(
    r"\b(bachelor|master|associate|doctoral|doctorate|phd|mba|b\.s\.|m\.s\.|aas)\b",
    re.IGNORECASE,
)

_URL_SCORING_HINTS = {
    "program_url": (
        ("cybersecurity", 10),
        ("cyber", 8),
        ("certificate", 7),
        ("program", 5),
        ("information-security", 4),
        ("catalog", 3),
    ),
    "tuition_url": (
        ("tuition", 10),
        ("cost", 8),
        ("fees", 7),
        ("billing", 5),
        ("financial", 4),
    ),
    "faculty_url": (
        ("faculty", 10),
        ("directory", 8),
        ("instructor", 6),
        ("staff", 5),
        ("people", 4),
    ),
    "admissions_url": (
        ("admissions", 10),
        ("apply", 8),
        ("enroll", 6),
        ("contact", 5),
        ("registration", 4),
    ),
}

_URL_BAD_HINTS = (
    "calendar",
    "events",
    "news",
    "login",
    "signin",
    "search",
    "youtube",
    "instagram",
    "facebook",
    "linkedin",
    "pdf",
)

_CONTEXT_URL_HINTS = (
    ("certificate", 9),
    ("cyber", 8),
    ("security", 7),
    ("curriculum", 7),
    ("course", 6),
    ("catalog", 6),
    ("admissions", 5),
    ("apply", 4),
    ("tuition", 5),
    ("fees", 4),
    ("financial", 4),
    ("funding", 4),
    ("scholarship", 5),
    ("fellowship", 4),
    ("requirement", 4),
    ("checklist", 3),
    ("handbook", 2),
)

_CONTEXT_URL_BAD_HINTS = (
    "news",
    "event",
    "calendar",
    "athletics",
    "instagram",
    "facebook",
    "linkedin",
    "youtube",
    "login",
    "signin",
    "policy",
    "resource",
    "partnership",
    "snap",
)


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href = ""
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return

        href = ""
        for key, value in attrs:
            if key.lower() == "href":
                href = str(value or "").strip()
                break

        self._current_href = href
        self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            text = str(data or "").strip()
            if text:
                self._current_text.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a":
            return
        if not self._current_href:
            return

        anchor_text = " ".join(self._current_text).strip()
        self.links.append((self._current_href, anchor_text))
        self._current_href = ""
        self._current_text = []


def build_field_schema() -> str:
    schema = []
    for key, _, _ in FIELDS:
        schema.append(
            f'    "{key}": {{"value": "...", "source_url": "...", "source_quote": "..."}}'
        )
    return ",\n".join(schema)


def load_prompt(path: str, **kwargs) -> str:
    with open(path, "r", encoding="utf-8") as f:
        template = f.read()

    # Replace only named placeholders like {college_name} and leave JSON braces intact.
    def replace_placeholder(match: re.Match) -> str:
        key = match.group(1)
        return str(kwargs.get(key, match.group(0)))

    rendered = _PLACEHOLDER_RE.sub(replace_placeholder, template)

    # Support legacy prompts that used escaped braces for str.format-style templates.
    rendered = rendered.replace("{{", "{").replace("}}", "}")

    return rendered


def clean_json(raw_text: str) -> dict:
    raw_text = raw_text.strip()

    # Strip markdown fences
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines).strip()

    start = raw_text.find("{")
    end   = raw_text.rfind("}")

    if start == -1 or end == -1:
        print("Failed JSON Text:", raw_text)
        raise ValueError("No valid JSON object found in model response")

    json_str = raw_text[start:end + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Direct parse failed ({e}), attempting recovery...")

    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(json_str)
        return obj
    except json.JSONDecodeError as e:
        print("Recovery failed. Raw snippet:")
        print(json_str[:500])
        raise ValueError(f"Could not parse JSON: {e}")


def _normalize_college_name(college_name: str) -> str:
    return " ".join(str(college_name or "").strip().lower().split())


def _is_missing_url(value: str) -> bool:
    normalized = " ".join(str(value or "").strip().lower().split())
    return normalized in _MISSING_URL_VALUES


def _is_http_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _strip_url_fragment(value: str) -> str:
    parsed = urlparse(value)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ""))


def _normalize_absolute_url(value: str, base_url: str = "") -> str:
    raw = str(value or "").strip()
    if _is_missing_url(raw):
        return ""

    lowered = raw.lower()
    if lowered.startswith(("mailto:", "tel:", "javascript:", "#")):
        return ""

    if lowered.startswith("//"):
        base_scheme = urlparse(base_url).scheme if base_url else "https"
        raw = f"{base_scheme}:{raw}"
    elif not _is_http_url(raw):
        if not base_url:
            return ""
        raw = urljoin(base_url, raw)

    if not _is_http_url(raw):
        return ""

    return _strip_url_fragment(raw)


def _domain_key(url: str) -> str:
    raw = str(url or "").strip().lower()
    if not raw:
        return ""

    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    netloc = parsed.netloc.lower()
    if not netloc and parsed.path and "." in parsed.path:
        netloc = parsed.path.lower()

    netloc = netloc.split("@")[-1].split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _site_key(value: str) -> str:
    host = _domain_key(value)
    if not host:
        return ""

    parts = [part for part in host.split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])

    return host


def _same_domain(url: str, root_domain_key: str) -> bool:
    if not root_domain_key:
        return True

    current = _domain_key(url)
    root = _domain_key(root_domain_key)

    if not current or not root:
        return False

    return (
        current == root
        or current.endswith(f".{root}")
        or root.endswith(f".{current}")
        or _site_key(current) == _site_key(root)
    )


def _root_url(url: str) -> str:
    if not _is_http_url(url):
        return ""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _request(url: str, method: str = "GET") -> Request:
    return Request(
        url=url,
        method=method,
        headers={"User-Agent": "Mozilla/5.0 (compatible; UniversityAggregator/1.0)"},
    )


def _is_reachable(url: str, timeout: int = 5) -> bool:
    if not _is_http_url(url):
        return False

    for method in ("HEAD", "GET"):
        try:
            req = _request(url, method=method)
            with urlopen(req, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if status < 400:
                    return True
        except HTTPError as exc:
            if method == "HEAD" and exc.code in {403, 405}:
                continue
            if exc.code < 400:
                return True
        except URLError:
            if method == "GET":
                return False
        except Exception:
            if method == "GET":
                return False

    return False


def _fetch_html(url: str, timeout: int = 5, max_bytes: int = 400_000) -> str:
    if not _is_http_url(url):
        return ""

    try:
        req = _request(url, method="GET")
        with urlopen(req, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                return ""

            content_type = str(response.headers.get("Content-Type", "")).lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                return ""

            body = response.read(max_bytes)
            encoding = response.headers.get_content_charset() or "utf-8"
            return body.decode(encoding, errors="ignore")
    except Exception:
        return ""


def _extract_links(html: str, page_url: str, root_domain_key: str) -> list[tuple[str, str]]:
    parser = _AnchorParser()
    try:
        parser.feed(html)
    except Exception:
        return []

    links: list[tuple[str, str]] = []
    blocked_ext = (
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".zip",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
    )

    for href, anchor_text in parser.links:
        absolute = _normalize_absolute_url(href, base_url=page_url)
        if not absolute:
            continue
        if not _same_domain(absolute, root_domain_key):
            continue

        if urlparse(absolute).path.lower().endswith(blocked_ext):
            continue

        links.append((absolute, anchor_text.strip()))

    return links


def _should_crawl(url: str) -> bool:
    path = urlparse(url).path.lower()
    blocked_ext = (
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".zip",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
    )
    if path.endswith(blocked_ext):
        return False

    crawl_hints = (
        "cyber",
        "security",
        "certificate",
        "program",
        "academ",
        "catalog",
        "tuition",
        "cost",
        "admissions",
        "faculty",
        "department",
        "school",
        "college",
    )

    return path in {"", "/"} or any(hint in path for hint in crawl_hints)


def _crawl_priority(url: str) -> int:
    text = url.lower()
    score = 0

    if any(hint in text for hint in ("cyber", "security", "certificate")):
        score += 10
    if any(hint in text for hint in ("programs/divisions", "programs", "catalog", "curriculum")):
        score += 5
    if any(hint in text for hint in ("faculty", "staff", "directory")):
        score += 4
    if any(hint in text for hint in ("tuition", "cost", "fees")):
        score += 3
    if any(hint in text for hint in ("admissions", "apply", "contact")):
        score += 2

    if any(hint in text for hint in ("high_school", "transfer", "student", "news", "event", "calendar")):
        score -= 6

    return score


def _collect_internal_links(seed_urls: list[str], max_pages: int = 8, max_links: int = 250) -> list[tuple[str, str]]:
    queue: list[str] = []
    seen_queue: set[str] = set()

    for seed in seed_urls:
        normalized = _normalize_absolute_url(seed)
        if normalized and normalized not in seen_queue:
            queue.append(normalized)
            seen_queue.add(normalized)

    if not queue:
        return []

    seed_set = set(queue)
    root_domain_key = _site_key(queue[0]) or _domain_key(queue[0])
    visited_pages: set[str] = set()
    collected: dict[str, str] = {}

    while queue and len(visited_pages) < max_pages and len(collected) < max_links:
        page_url = queue.pop(0)
        if page_url in visited_pages:
            continue

        visited_pages.add(page_url)
        html = _fetch_html(page_url)
        if not html:
            continue

        for link_url, anchor_text in _extract_links(html, page_url, root_domain_key):
            if link_url not in collected or (anchor_text and not collected[link_url]):
                collected[link_url] = anchor_text

            if len(collected) >= max_links:
                break

            if link_url not in visited_pages and link_url not in queue and _should_crawl(link_url):
                queue.append(link_url)

        # Always process original seed URLs first, then use priority ordering.
        queue.sort(key=lambda candidate_url: (candidate_url not in seed_set, -_crawl_priority(candidate_url)))

    return list(collected.items())


def _has_degree_hint(text: str) -> bool:
    normalized = str(text or "").replace("-", " ").replace("_", " ")
    return bool(_DEGREE_HINT_RE.search(normalized))


def _query_int(url: str, key: str) -> int:
    try:
        query = parse_qs(urlparse(url).query)
        values = query.get(key, [])
        if not values:
            return -1
        return int(values[0])
    except (TypeError, ValueError):
        return -1


def _score_link(target_key: str, url: str, anchor_text: str) -> int:
    text = f"{url} {anchor_text}".lower()
    score = 0

    for keyword, weight in _URL_SCORING_HINTS.get(target_key, ()):
        if keyword in text:
            score += weight

    for bad_hint in _URL_BAD_HINTS:
        if bad_hint in text:
            score -= 3

    parsed = urlparse(url)
    if parsed.query:
        score -= 1

    depth_penalty = max(0, parsed.path.count("/") - 3)
    score -= depth_penalty

    if target_key == "program_url":
        if not any(hint in text for hint in ("cyber", "security", "information security", "information-security")):
            score -= 12
        if "certificate" in text:
            score += 8
        if any(hint in text for hint in ("advanced-certificate", "advanced certificate", "cas.", "certificate in")):
            score += 4
        if _has_degree_hint(text) and "certificate" not in text:
            score -= 12
        if any(hint in text for hint in ("high_school", "futureready", "future ready", "transfer")):
            score -= 12
        if "preview_program.php" in url.lower():
            catoid = _query_int(url, "catoid")
            if catoid >= 0:
                score += min(catoid, 20)

    if target_key == "tuition_url":
        if not any(hint in text for hint in ("tuition", "fees", "cost")):
            score -= 10
        if any(hint in text for hint in ("financial-aid", "lottery", "scholarship", "waiver", "work_study", "grant")):
            score -= 8

    if target_key == "faculty_url":
        if not any(hint in text for hint in ("faculty", "staff", "directory", "instructor")):
            score -= 10
        if "about/directory" in text:
            score -= 4
        if "cyber" in text and ("faculty" in text or "staff" in text):
            score += 6

    if target_key == "admissions_url":
        if not any(hint in text for hint in ("admissions", "apply", "enroll", "contact")):
            score -= 10
        if any(hint in text for hint in ("international", "military", "senior", "transient", "residency", "readmit", "transfer")):
            score -= 5
        if any(hint in text for hint in ("/admissions/index", "/admissions/apply/index", "/graduate/admissions", "/admissions.html")):
            score += 5

    return score


def _pick_best_link(target_key: str, candidates: list[tuple[str, str]]) -> str:
    best_url = ""
    best_score = 0

    for url, anchor_text in candidates:
        score = _score_link(target_key, url, anchor_text)
        if score > best_score:
            best_score = score
            best_url = url

    if best_score <= 0:
        return ""

    return best_url


def _pick_best_scored_link(target_key: str, candidates: list[tuple[str, str]]) -> tuple[str, int]:
    best_url = ""
    best_score = 0

    for url, anchor_text in candidates:
        score = _score_link(target_key, url, anchor_text)
        if score > best_score:
            best_score = score
            best_url = url

    return best_url, best_score


def _append_unique_url(target: list[str], candidate: str) -> None:
    normalized = _normalize_absolute_url(candidate)
    if normalized and normalized not in target:
        target.append(normalized)


def _score_context_url(url: str, anchor_text: str) -> int:
    text = f"{url} {anchor_text}".lower()
    score = 0

    for keyword, weight in _CONTEXT_URL_HINTS:
        if keyword in text:
            score += weight

    for keyword in _CONTEXT_URL_BAD_HINTS:
        if keyword in text:
            score -= 4

    if _has_degree_hint(text) and "certificate" not in text and "cyber" not in text:
        score -= 5

    parsed = urlparse(url)
    depth_penalty = max(0, parsed.path.count("/") - 4)
    score -= depth_penalty

    return score


def build_additional_context_urls(discovery: dict, max_urls: int = 8) -> list[str]:
    core_urls: list[str] = []
    merged = dict(discovery or {})

    for key in _TARGET_DISCOVERY_URL_KEYS:
        _append_unique_url(core_urls, str(merged.get(key, "")))

    if not core_urls:
        return []

    primary_program_url = _normalize_absolute_url(str(merged.get("program_url", "")))
    primary_catoid = _query_int(primary_program_url, "catoid")

    seed_urls: list[str] = []
    for url in core_urls:
        _append_unique_url(seed_urls, url)
        root = _root_url(url)
        _append_unique_url(seed_urls, root)

    link_pairs = _collect_internal_links(seed_urls, max_pages=16, max_links=500)

    # Pull high-signal links directly from each core page in case crawl limits skip them.
    for core_url in core_urls:
        html = _fetch_html(core_url)
        if not html:
            continue

        domain_scope = _site_key(core_url) or _domain_key(core_url)
        direct_links = _extract_links(html, core_url, domain_scope)
        link_pairs.extend(direct_links)

    dedup: dict[str, str] = {}
    for url, anchor_text in link_pairs:
        normalized = _normalize_absolute_url(url)
        if not normalized or normalized in core_urls:
            continue

        if normalized not in dedup or (anchor_text and not dedup[normalized]):
            dedup[normalized] = anchor_text

    ranked: list[tuple[int, str]] = []
    for url, anchor_text in dedup.items():
        # Keep context pages within the same catalog edition when possible.
        if "preview_program.php" in url.lower() and primary_catoid >= 0:
            candidate_catoid = _query_int(url, "catoid")
            if candidate_catoid >= 0 and candidate_catoid != primary_catoid:
                continue

        score = _score_context_url(url, anchor_text)

        if score > 5:
            ranked.append((score, url))

    ranked.sort(reverse=True)

    selected: list[str] = []
    for _, url in ranked:
        if url not in selected:
            selected.append(url)
        if len(selected) >= max_urls:
            break

    return selected


def normalize_context_urls(raw_value: object) -> list[str]:
    if isinstance(raw_value, list):
        values = raw_value
    else:
        text = str(raw_value or "").strip()
        if not text:
            return []

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                values = parsed
            else:
                values = re.findall(r"https?://[^\s'\"\],]+", text)
        except json.JSONDecodeError:
            values = re.findall(r"https?://[^\s'\"\],]+", text)

    normalized: list[str] = []
    for value in values:
        cleaned = _normalize_absolute_url(str(value or ""))
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)

    return normalized


def _guess_domain_seeds(college_name: str) -> list[str]:
    compact = re.sub(r"[^a-z0-9]", "", _normalize_college_name(college_name))
    if not compact:
        return []

    return [
        f"https://www.{compact}.edu",
        f"https://{compact}.edu",
    ]


def apply_discovery_url_overrides(college_name: str, discovery: dict) -> dict:
    """
    Normalize discovery URLs and auto-fill missing/broken URL fields.
    This keeps Stage 2 URL Context robust without hardcoded school mappings.
    """
    merged = dict(discovery or {})

    seed_url = ""
    for key in _TARGET_DISCOVERY_URL_KEYS:
        normalized = _normalize_absolute_url(str(merged.get(key, "")))
        if normalized:
            merged[key] = normalized
            if not seed_url:
                seed_url = normalized

    if not seed_url:
        for guess in _guess_domain_seeds(college_name):
            if _is_reachable(guess):
                seed_url = guess
                break

    if not seed_url:
        merged[_DISCOVERY_CONTEXT_URL_KEY] = []
        return merged

    root = _root_url(seed_url)
    if not root:
        merged[_DISCOVERY_CONTEXT_URL_KEY] = []
        return merged

    # Convert relative URL outputs from discovery into absolute URLs using the root domain.
    for key in _TARGET_DISCOVERY_URL_KEYS:
        normalized = _normalize_absolute_url(str(merged.get(key, "")), base_url=root)
        if normalized:
            merged[key] = normalized

    seed_urls = [root]
    for key in _TARGET_DISCOVERY_URL_KEYS:
        candidate = _normalize_absolute_url(str(merged.get(key, "")), base_url=root)
        if candidate and candidate not in seed_urls:
            seed_urls.append(candidate)

    discovered_links = _collect_internal_links(seed_urls, max_pages=14, max_links=400)
    if root not in [url for url, _ in discovered_links]:
        discovered_links.append((root, "home"))

    for key in _TARGET_DISCOVERY_URL_KEYS:
        current = _normalize_absolute_url(str(merged.get(key, "")), base_url=root)
        current_reachable = bool(current) and _is_reachable(current)
        current_score = _score_link(key, current, "") if current else -999

        best, best_score = _pick_best_scored_link(key, discovered_links)

        # Prefer stronger internal links even when the current URL is reachable.
        if best and (not current_reachable or best_score >= current_score + 3):
            merged[key] = best
            continue

        if current_reachable:
            merged[key] = current
            continue

        if best:
            merged[key] = best
        elif current:
            merged[key] = current
        else:
            merged[key] = "Not Found"

    try:
        merged[_DISCOVERY_CONTEXT_URL_KEY] = build_additional_context_urls(merged)
    except Exception:
        merged[_DISCOVERY_CONTEXT_URL_KEY] = []

    return merged
