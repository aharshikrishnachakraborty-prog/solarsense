"""Chat assistant: the facts match the computed tables, and /api/chat behaves with Gemini on, off or failing."""

from fastapi.testclient import TestClient

from api.data_store import get_store
from api.main import app
from api.routes import chat as chat_route
from engine import config
from engine.assistant import build_request
from engine.period_summary import period_window, summarize
from tests.conftest import log_in


def test_week_window_is_seven_days_ending_at_date():
    """A week is the 7 days up to and including the selected date."""
    dates = get_store().dates
    days = period_window(dates, dates[10], "week")
    assert len(days) == 7 and days[-1] == dates[10]
    assert period_window(dates, dates[2], "week") == dates[:3]   # near the start: only the days we have
    assert period_window(dates, dates[5], "month") == dates


def test_day_summary_matches_daily_table():
    """Day facts are exactly the numbers in daily_plant (nothing recalculated differently)."""
    store = get_store()
    date = store.dates[12]
    row = store.daily_plant[(store.daily_plant["plant"] == 2) & (store.daily_plant["date"] == date)].iloc[0]
    facts = summarize(store, 2, date, "day")
    assert facts["energy"]["actual_kwh"] == round(float(row["actual_kwh"]), 1)
    assert facts["energy"]["fault_loss_kwh"] == round(float(row["fault_loss_kwh"]), 1)


def test_chat_offline_without_key(monkeypatch):
    """No Gemini key configured: a friendly offline reply, not an error."""
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with TestClient(app) as client:
        log_in(client)
        answer = client.post("/api/chat", json={"message": "weekly report", "plant": 1}).json()
    assert answer["online"] is False and "offline" in answer["reply"]


def test_chat_sends_question_and_facts(monkeypatch):
    """With a key set, the question and our facts go to Gemini and its reply comes back."""
    sent = {}

    def fake_gemini(question, facts, history):
        sent.update(message=question, facts=facts)
        return "Plant 1 made 95% of expected output. Check bvBOhCH3iADSZry. Open the Alerts page."

    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(chat_route, "ask_gemini", fake_gemini)
    with TestClient(app) as client:
        log_in(client)
        answer = client.post("/api/chat", json={"message": "summary", "plant": 1, "session_id": "t1"}).json()
    assert answer["online"] is True and answer["reply"].startswith("Plant 1 made 95%")
    assert answer["inverters"] == {"bvBOhCH3iADSZry": 1}   # real IDs in the reply, for links
    assert sent["message"] == "summary"
    assert set(sent["facts"]["summaries"]) == {"day", "week", "month"}


def test_chat_gemini_failure_falls_back(monkeypatch):
    """If Gemini fails (no internet, quota used up), the user gets the offline message instead of a crash."""
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(chat_route, "ask_gemini", lambda question, facts, history: None)
    with TestClient(app) as client:
        log_in(client)
        answer = client.post("/api/chat", json={"message": "hi", "plant": 2, "session_id": "t2"}).json()
    assert answer["online"] is False


def test_gemini_request_has_rules_history_and_facts():
    """The request carries the rules, earlier turns, and the facts next to the new question."""
    body = build_request("weekly report", {"plant": 1}, [("user", "hi"), ("model", "Hello.")])
    assert "Use ONLY the numbers in FACTS" in body["systemInstruction"]["parts"][0]["text"]
    assert [t["role"] for t in body["contents"]] == ["user", "model", "user"]
    assert '"plant": 1' in body["contents"][-1]["parts"][0]["text"]
