"""Request a troubleshooting guide using only counts of known issue types."""
import json
import os
from urllib.request import Request, urlopen

from feed import ISSUE_TYPES


def explain_issues(counts: dict[str, int]) -> str:
    """Return read-only troubleshooting text from the OpenAI Responses API."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError("Set OPENAI_API_KEY to enable AI troubleshooting.")
    summary = {issue: int(counts[issue]) for issue in ISSUE_TYPES if issue in counts}
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        "store": False,
        "max_output_tokens": 500,
        "instructions": (
            "Write a short plain-text troubleshooting checklist for a beginner "
            "reviewing a product CSV. Explain what source records to consult for "
            "each listed issue type. Never supply or guess replacement values, "
            "and never claim to have edited the file."
        ),
        "input": json.dumps(summary),
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=20) as response:
        result = json.load(response)
    guide = "\n".join(
        part.get("text", "")
        for item in result.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    ).strip()
    if not guide:
        raise ValueError("The API returned no troubleshooting text.")
    return guide
