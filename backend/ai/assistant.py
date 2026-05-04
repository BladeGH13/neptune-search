import re
from dataclasses import dataclass
from typing import Optional

# ── Intent definitions ──────────────────────────────────────────────────────

@dataclass
class Intent:
    name: str
    confidence: float
    slots: dict

# Each rule: (pattern, intent_name, slot_extractor_fn)
INTENT_RULES = [
    # Calculation
    (r"\b(\d[\d\s\+\-\*\/\.\(\)]+)\b", "calculate", lambda m: {"expr": m.group(0).strip()}),
    # Definition / what is
    (r"\bwhat\s+is\s+(.+)", "define", lambda m: {"term": m.group(1).strip("? ")}),
    (r"\bdefine\s+(.+)", "define", lambda m: {"term": m.group(1).strip("? ")}),
    # Conversion
    (r"(\d+\.?\d*)\s*(km|miles?|kg|lbs?|celsius|fahrenheit|c|f)\s+(?:to|in)\s+(\w+)",
        "convert", lambda m: {"value": m.group(1), "from_unit": m.group(2), "to_unit": m.group(3)}),
    # Weather
    (r"\bweather\s+(?:in\s+)?(.+)", "weather", lambda m: {"location": m.group(1).strip("? ")}),
    # Time / date
    (r"\b(?:what(?:\'s|\s+is)\s+)?(?:the\s+)?(?:time|date)\b", "datetime", lambda m: {}),
    # Who is
    (r"\bwho\s+is\s+(.+)", "who_is", lambda m: {"person": m.group(1).strip("? ")}),
    # How to
    (r"\bhow\s+(?:do\s+(?:i|you)\s+|to\s+)(.+)", "how_to", lambda m: {"task": m.group(1).strip("? ")}),
    # Site search
    (r"\bsite:(\S+)\s+(.*)", "site_search", lambda m: {"domain": m.group(1), "query": m.group(2)}),
]

FACT_DB = {
    # Quick facts — expandable as you crawl more pages
    "neptune": "Neptune is the eighth planet from the Sun, an ice giant with a deep blue color caused by methane in its atmosphere.",
    "bluom": "BLUOM is a technology company building Neptune Browser and Neptune Search.",
    "python": "Python is a high-level, interpreted programming language known for its readability and large ecosystem.",
    "html": "HTML (HyperText Markup Language) is the standard markup language for creating web pages.",
}

CONVERSION_FACTORS = {
    ("km", "miles"): 0.621371,
    ("miles", "km"): 1.60934,
    ("kg", "lbs"): 2.20462,
    ("lbs", "kg"): 0.453592,
    ("celsius", "fahrenheit"): None,   # handled specially
    ("fahrenheit", "celsius"): None,
    ("c", "f"): None,
    ("f", "c"): None,
}

# ── Main AI class ────────────────────────────────────────────────────────────

class NeptuneAI:
    """
    Rule-based AI assistant for Neptune Search.
    Detects user intent and generates instant answers above search results.

    To upgrade to an ONNX model later, subclass this and override `classify_intent`.
    The rest of the pipeline (slot filling, response generation) stays identical.
    """

    def __init__(self, onnx_model_path: Optional[str] = None):
        self.onnx_model = None
        if onnx_model_path:
            self._load_onnx(onnx_model_path)

    def _load_onnx(self, path: str):
        """Plug in a trained ONNX model for intent classification."""
        try:
            import onnxruntime as ort
            self.onnx_model = ort.InferenceSession(path)
        except ImportError:
            print("onnxruntime not installed — falling back to rule engine")

    def classify_intent(self, query: str) -> Intent:
        """Match query against rule patterns. Returns highest-confidence intent."""
        query_lower = query.lower().strip()

        for pattern, intent_name, slot_fn in INTENT_RULES:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    slots = slot_fn(match)
                except Exception:
                    slots = {}
                return Intent(name=intent_name, confidence=0.9, slots=slots)

        return Intent(name="search", confidence=1.0, slots={})

    def answer(self, query: str) -> Optional[dict]:
        """
        Returns an instant answer dict if we can answer directly,
        or None if we should just show search results.

        Returns: {
            "type": "answer" | "suggestion" | "conversion" | "fact",
            "title": str,
            "body": str,
            "source": str (optional)
        }
        """
        intent = self.classify_intent(query)

        if intent.name == "define":
            term = intent.slots.get("term", "").lower()
            if term in FACT_DB:
                return {
                    "type": "fact",
                    "title": f"About: {term.title()}",
                    "body": FACT_DB[term],
                    "source": "Neptune Knowledge Base",
                }

        elif intent.name == "convert":
            return self._handle_conversion(intent.slots)

        elif intent.name == "calculate":
            return self._handle_calculation(intent.slots)

        elif intent.name == "datetime":
            from datetime import datetime
            now = datetime.utcnow()
            return {
                "type": "answer",
                "title": "Current Date & Time (UTC)",
                "body": now.strftime("%A, %d %B %Y — %H:%M UTC"),
                "source": "System",
            }

        elif intent.name == "site_search":
            domain = intent.slots.get("domain", "")
            return {
                "type": "suggestion",
                "title": f"Searching within {domain}",
                "body": f"Filtering results to pages on {domain}.",
                "source": None,
            }

        return None   # No instant answer — fall through to normal search results

    def summarise_results(self, query: str, results: list[dict]) -> Optional[str]:
        """
        Generate a brief AI summary above search results.
        Uses top 3 snippets as context.
        """
        if not results:
            return f'No results found for "{query}". Try different keywords.'

        top_domains = list({r["domain"] for r in results[:5] if r["domain"]})
        count = len(results)
        domain_str = ", ".join(top_domains[:3])

        return (
            f"Found {count} result{'s' if count != 1 else ''} for \"{query}\". "
            f"Top sources include: {domain_str}."
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _handle_conversion(self, slots: dict) -> Optional[dict]:
        try:
            value = float(slots["value"])
            from_unit = slots["from_unit"].lower().rstrip("s")
            to_unit = slots["to_unit"].lower().rstrip("s")

            # Celsius ↔ Fahrenheit special cases
            if from_unit in ("c", "celsius") and to_unit in ("f", "fahrenheit"):
                result = value * 9 / 5 + 32
                return {"type": "conversion", "title": "Unit Conversion",
                        "body": f"{value}°C = {result:.2f}°F", "source": None}
            if from_unit in ("f", "fahrenheit") and to_unit in ("c", "celsius"):
                result = (value - 32) * 5 / 9
                return {"type": "conversion", "title": "Unit Conversion",
                        "body": f"{value}°F = {result:.2f}°C", "source": None}

            key = (from_unit, to_unit + "s") if (from_unit, to_unit + "s") in CONVERSION_FACTORS else (from_unit, to_unit)
            factor = CONVERSION_FACTORS.get(key)
            if factor:
                result = value * factor
                return {"type": "conversion", "title": "Unit Conversion",
                        "body": f"{value} {from_unit} = {result:.4f} {to_unit}", "source": None}
        except Exception:
            pass
        return None

    def _handle_calculation(self, slots: dict) -> Optional[dict]:
        expr = slots.get("expr", "")
        # Safe eval — only allows numbers and basic operators
        safe_expr = re.sub(r"[^\d\s\+\-\*\/\.\(\)]", "", expr)
        try:
            result = eval(safe_expr, {"__builtins__": {}})   # no builtins = safe
            return {"type": "answer", "title": "Calculator",
                    "body": f"{safe_expr.strip()} = {result}", "source": None}
        except Exception:
            return None

# Singleton instance
ai = NeptuneAI()