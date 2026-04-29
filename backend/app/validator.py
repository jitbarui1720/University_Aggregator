BOOTCAMP_KEYWORDS = [
    "bootcamp", "boot camp", "workforce", "continuing education",
    "professional development", "corporate training", "non-credit",
    "noncredit", "workforce development"
]

DEGREE_KEYWORDS = [
    "bachelor", "master of science", "master of arts", "mba",
    "associate degree", "doctoral", "phd", "m.s.", "b.s."
]

VALID_TYPES = ["graduate certificate", "undergraduate certificate"]

HARD_REJECT_REASON_KEYWORDS = [
    "bootcamp", "boot camp", "bachelor", "master", "associate",
    "doctoral", "phd", "degree program", "specialization",
    "concentration", "track within", "minor"
]

SOFT_REJECT_REASON_KEYWORDS = [
    "official academic catalog", "not listed in the official",
    "stanford bulletin", "extension", "continuing education",
    "professional development"
]


def _norm(value: str) -> str:
    return str(value or "").strip().lower()


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def validate_discovery(discovery: dict) -> tuple[bool, str]:
    """
    Returns (is_valid, reason).
    Checks that Gemini found a real academic non-degree certificate.
    """
    program_name_raw = discovery.get("program_name", "")
    program_type_raw = discovery.get("program_type", "")
    rejection_reason_raw = discovery.get("rejection_reason", "")
    model_valid_raw = discovery.get("is_valid_certificate", "")
    program_url_raw = discovery.get("program_url", "")

    program_name = _norm(program_name_raw)
    program_type = _norm(program_type_raw)
    rejection_reason = _norm(rejection_reason_raw)
    model_valid = _norm(model_valid_raw)
    program_url = _norm(program_url_raw)

    if program_name in {"", "not found", "n/a", "no valid program found"}:
        return False, "No valid program name was found in discovery output"

    if program_url in {"", "not found", "n/a"}:
        return False, "Program URL is missing from discovery output"

    for kw in BOOTCAMP_KEYWORDS:
        if kw in program_name:
            return False, f"Program name contains excluded keyword: '{kw}'"

    for kw in DEGREE_KEYWORDS:
        if kw in program_name:
            return False, f"Program name contains degree keyword: '{kw}'"

    if not any(vt in program_type for vt in VALID_TYPES):
        if "graduate certificate" in program_name:
            program_type = "graduate certificate"
        elif "undergraduate certificate" in program_name:
            program_type = "undergraduate certificate"
        else:
            return False, f"Program type '{program_type_raw}' is not a valid certificate type"

    if _contains_any(rejection_reason, HARD_REJECT_REASON_KEYWORDS):
        return False, rejection_reason_raw or "Gemini rejection reason indicates invalid program"

    if model_valid in {"yes", "true"}:
        return True, "OK"

    # Some schools host valid non-degree certificates in official extension/professional units.
    if model_valid in {"no", "false"} and _contains_any(rejection_reason, SOFT_REJECT_REASON_KEYWORDS):
        return True, "Accepted by local validator despite model soft rejection"

    if model_valid in {"", "not found", "n/a"}:
        return True, "OK (model validity flag missing; accepted by local checks)"

    return False, rejection_reason_raw or "Gemini flagged as invalid"
