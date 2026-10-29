"""Chat assistant brain: sends the operator's question + our computed facts to Google Gemini (free tier).

The AI only turns facts into sentences — every number comes from engine/period_summary.py (CLAUDE.md rule 9).
The Gemini key is a secret: it is read from .env (GEMINI_API_KEY) and never written in code or sent to the browser.
"""

import json
import urllib.error
import urllib.request

from engine import config

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """You are the SolarSense Assistant for solar plant operators and O&M engineers.

RULES:
1. Use ONLY the numbers in FACTS. Never calculate new totals, estimate, or invent numbers. Quote kWh and rupee
   values rounded to whole numbers (no decimals), with Indian digit grouping (e.g. 2,47,695 kWh, Rs 7,43,085);
   percentages with at most one decimal.
2. FACTS has summaries for 'day' (the selected date), 'week' (7 days ending at the selected date) and 'month'
   (the whole period of data, about one month). Pick the one the question asks for; default to 'day'.
3. If the answer is not in FACTS (forecasts, other plants, dates outside the data, prices), say you do not have
   that data and point to the dashboard page that may help (Overview, Plant, Weather & Energy, Inverters, Alerts).
4. Rupee values use an ASSUMED tariff; mention this once when you give rupee amounts.
5. Reports: a one-line headline, then 3 to 6 short bullet points (output vs expected, losses to faults, clouds and
   heat, alerts, worst inverters, recommended actions). Other questions: 1 to 3 sentences.
6. End with one short line naming the most useful dashboard page, written exactly as "Open the <Page> page"
   with <Page> one of: Overview, Plant, Weather & Energy, Inverters, Alerts. Use "Inverters" for one inverter's
   detail, "Alerts" for alert lists and actions, "Weather & Energy" for clouds/heat/losses split, "Plant" for
   multi-day trends, "Overview" for the selected day.
7. Under 120 words. Plain, professional English. No emojis. Inverter IDs exactly as given.
8. Fault types: INVERTER_TRIP = inverter trip, UNDERPERFORMANCE = underperformance, DATA_GAP = data gap,
   DEGRADATION = degradation/soiling, OVERHEATING = overheating, SENSOR_ISSUE = sensor/data issue."""


def build_request(question, facts, history):
    """The JSON body Gemini expects: rules, the last few turns of the conversation, then facts + question."""
    turns = [{"role": "user" if role == "user" else "model", "parts": [{"text": text}]} for role, text in history]
    latest = f"FACTS (computed by SolarSense, JSON):\n{json.dumps(facts, ensure_ascii=False, default=str)}\n\n" \
             f"Operator question: {question}"
    turns.append({"role": "user", "parts": [{"text": latest}]})
    return {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": turns,
        # Low temperature = sticks to the facts. thinkingBudget 0 = faster replies for a chat window.
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600, "thinkingConfig": {"thinkingBudget": 0}},
    }


def ask_gemini(question, facts, history=()):
    """Ask Gemini and return its reply text, or None if it fails (no key, no internet, quota used up)."""
    if not config.GEMINI_API_KEY:
        return None
    body = json.dumps(build_request(question, facts, history)).encode("utf-8")
    request = urllib.request.Request(GEMINI_URL.format(model=config.GEMINI_MODEL), data=body, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "x-goog-api-key": config.GEMINI_API_KEY})
    try:
        with urllib.request.urlopen(request, timeout=config.CHAT_TIMEOUT_SECONDS) as response:
            answer = json.loads(response.read().decode("utf-8"))
        parts = answer["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts).strip() or None
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError):
        return None
