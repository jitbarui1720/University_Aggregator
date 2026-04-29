import os
import pandas as pd
from IPython.display import display
from google import genai
from google.genai import types
from dotenv import load_dotenv

try:
    from .fields import FIELDS
    from .utils import (
        build_field_schema,
        load_prompt,
        clean_json,
        apply_discovery_url_overrides,
        normalize_context_urls,
    )
    from .validator import validate_discovery
except ImportError:
    from fields import FIELDS
    from utils import (
        build_field_schema,
        load_prompt,
        clean_json,
        apply_discovery_url_overrides,
        normalize_context_urls,
    )
    from validator import validate_discovery

# ── Config ────────────────────────────────────────────────────────────────────
APP_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.dirname(APP_DIR)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the .env file")
    
MODEL = "gemini-2.5-pro"
client = genai.Client(api_key=GEMINI_API_KEY)

DISCOVERY_PROMPT = os.path.join(APP_DIR, "prompts", "discovery.txt")
EXTRACTION_PROMPT = os.path.join(APP_DIR, "prompts", "extraction.txt")


# ── Stage 1: Discover the correct program + URLs ──────────────────────────────
def discover_program(college_name: str) -> dict:
    print(f"\n[Stage 1] Discovering program for: {college_name}")

    domain_guess = college_name.lower().replace(" ", "") + ".edu"

    prompt = load_prompt(
        DISCOVERY_PROMPT,
        college_name=college_name,
        college_domain=domain_guess
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            temperature=0.1,
        ),
    )

    discovery = clean_json(response.text)
    discovery = apply_discovery_url_overrides(college_name, discovery)
    context_urls = normalize_context_urls(discovery.get("context_urls", []))
    discovery["context_urls"] = context_urls

    print(f"  Program found : {discovery.get('program_name')}")
    print(f"  Program URL   : {discovery.get('program_url')}")
    if context_urls:
        print(f"  Extra context : {len(context_urls)} pages discovered")

    return discovery


# ── Stage 2: Gemini reads URLs natively via URL Context ───────────────────────
def extract_program_data(college_name: str, discovery: dict) -> dict:
    print(f"\n[Stage 2] Extracting data using URL context")

    program_url = discovery.get("program_url", "Not Found")
    tuition_url = discovery.get("tuition_url", "Not Found")
    faculty_url = discovery.get("faculty_url", "Not Found")
    admissions_url = discovery.get("admissions_url", "Not Found")
    context_urls = normalize_context_urls(discovery.get("context_urls", []))
    extra_urls_block = "\n".join(f"- {url}" for url in context_urls) if context_urls else "- None"

    print(f"  Program page  : {program_url}")
    print(f"  Tuition page  : {tuition_url}")
    print(f"  Faculty page  : {faculty_url}")
    print(f"  Admissions    : {admissions_url}")
    if context_urls:
        print("  Extra context :")
        for url in context_urls:
            print(f"    - {url}")

    prompt = load_prompt(
        EXTRACTION_PROMPT,
        college_name=college_name,
        program_name=discovery.get("program_name", "Unknown"),
        program_url=program_url,
        tuition_url=tuition_url,
        faculty_url=faculty_url,
        admissions_url=admissions_url,
        extra_urls_block=extra_urls_block,
        schema=build_field_schema()
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"url_context": {}}],
            temperature=0.1,
        ),
    )

    return clean_json(response.text)


def normalize_extracted_data(data: dict) -> dict:
    normalized: dict[str, dict[str, str]] = {}

    for key, _, _ in FIELDS:
        field = data.get(key, {})
        if isinstance(field, dict):
            value = str(field.get("value", "Not Found") or "Not Found").strip()
            source_url = str(field.get("source_url", "Not Found") or "Not Found").strip()
            source_quote = str(field.get("source_quote", "Not Found") or "Not Found").strip()
        else:
            value = str(field or "Not Found").strip()
            source_url = "Not Found"
            source_quote = "Not Found"

        if not value:
            value = "Not Found"
        if not source_url:
            source_url = "Not Found"
        if not source_quote:
            source_quote = "Not Found"

        if value == "Not Found":
            source_url = "Not Found"
            source_quote = "Not Found"

        normalized[key] = {
            "value": value,
            "source_url": source_url,
            "source_quote": source_quote,
        }

    return normalized


# ── Build DataFrame ───────────────────────────────────────────────────────────
def build_dataframe(data: dict) -> pd.DataFrame:
    row = {}

    for key, label, _ in FIELDS:
        field = data.get(key, {})
        if isinstance(field, dict):
            value = field.get("value", "Not Found")
        else:
            value = str(field)

        row[label] = value

    return pd.DataFrame([row])


# If fewer than this many fields are found (after JSON normalization), run the full pipeline once more.
MIN_FOUND_FIELDS_BEFORE_RETRY = 10


def count_found_fields(normalized_fields: dict) -> int:
    """Count fields whose value is not 'Not Found' (post-normalization)."""
    return sum(
        1
        for entry in normalized_fields.values()
        if isinstance(entry, dict) and entry.get("value") != "Not Found"
    )


def run_pipeline(college_name: str, save_csv: bool = True) -> dict:
    college_target = (college_name or "").strip()
    if not college_target:
        raise ValueError("College name is required")

    slug = college_target.replace(" ", "_").lower()
    output_dir = os.path.join(APP_DIR, "outputs", slug)
    os.makedirs(output_dir, exist_ok=True)
    discovery_path = os.path.join(output_dir, f"{slug}_discovery.csv")
    data_path = os.path.join(output_dir, f"{slug}_cybersecurity_full.csv")

    def run_once() -> dict:
        discovery = discover_program(college_target)

        is_valid, reason = validate_discovery(discovery)
        discovery_record = dict(discovery)
        discovery_record["validation_status"] = "Valid" if is_valid else "Invalid"
        discovery_record["validation_reason"] = reason

        if save_csv:
            pd.DataFrame([discovery_record]).to_csv(discovery_path, index=False)

        if not is_valid:
            return {
                "status": "invalid_program",
                "college_name": college_target,
                "slug": slug,
                "validation": {"is_valid": False, "reason": reason},
                "discovery": discovery_record,
                "fields": {},
                "csv_paths": {
                    "discovery_csv": discovery_path if save_csv else None,
                    "full_csv": None,
                },
            }

        extracted_json = extract_program_data(college_target, discovery)
        normalized_fields = normalize_extracted_data(extracted_json)
        df = build_dataframe(normalized_fields)

        if save_csv:
            df.to_csv(data_path, index=False)

        return {
            "status": "completed",
            "college_name": college_target,
            "slug": slug,
            "validation": {"is_valid": True, "reason": reason},
            "discovery": discovery_record,
            "fields": normalized_fields,
            "row": df.iloc[0].to_dict(),
            "csv_paths": {
                "discovery_csv": discovery_path if save_csv else None,
                "full_csv": data_path if save_csv else None,
            },
        }

    result = run_once()
    retry_applied = False

    if result.get("status") == "completed":
        found_n = count_found_fields(result["fields"])
        if found_n < MIN_FOUND_FIELDS_BEFORE_RETRY:
            print(
                f"\n[Retry] Only {found_n} fields found "
                f"(threshold {MIN_FOUND_FIELDS_BEFORE_RETRY}); running full pipeline once more..."
            )
            result = run_once()
            retry_applied = True

        if result.get("status") == "completed":
            result["found_field_count"] = count_found_fields(result["fields"])
            result["retry_applied"] = retry_applied

    return result


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    college_name = input(
        "Enter the college name (e.g., 'Stanford University'): "
    ).strip()
    result = run_pipeline(college_name, save_csv=True)

    if result["status"] == "invalid_program":
        print(f"\nInvalid program detected: {result['validation']['reason']}")
        print(f"Discovery saved to: {result['csv_paths']['discovery_csv']}")
        print("\nNo CSV generated because no valid non-degree certificate was found.")
        raise SystemExit(0)

    print(f"\nValidated program: {result['discovery']['program_name']}")

    df = build_dataframe(result["fields"])
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_colwidth", 80)
    display(df.T)

    print(f"\nData saved to: {result['csv_paths']['full_csv']}")
    print(f"Discovery saved to: {result['csv_paths']['discovery_csv']}")