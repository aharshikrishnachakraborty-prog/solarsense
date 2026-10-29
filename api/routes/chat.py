"""Chat assistant endpoints: computed facts + asking Google Gemini to phrase the answer.

Our code computes every number (engine/period_summary.py). Gemini only phrases the answer from those facts
(engine/assistant.py). The Gemini key stays on the server, in .env — the browser never sees it.
"""

import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.data_store import get_store
from engine import config
from engine.assistant import ask_gemini
from engine.period_summary import all_facts

router = APIRouter(prefix="/api", tags=["assistant"])

OFFLINE_REPLY = ("The assistant is offline right now. You can still find every number on the dashboard pages "
                 "(Overview, Plant, Weather & Energy, Alerts).")
HISTORY_TURNS = 6                                   # remember the last few messages so follow-ups make sense
recent_messages = defaultdict(deque)                # session -> times of recent messages (simple rate limit)
conversations = defaultdict(lambda: deque(maxlen=HISTORY_TURNS))   # session -> [(role, text), ...]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    plant: int
    date: Optional[str] = None
    session_id: str = Field(default="anonymous", max_length=64)


def facts_for(plant, date):
    """Check plant/date, then build the day / week / whole-period facts."""
    store = get_store()
    plant = store.check_plant(plant)
    date = date if date in store.dates else store.worst_loss_date(plant)
    return all_facts(store, plant, date)


def too_many(session_id):
    """True if this session sent too many messages in the last minute (protects the free Gemini quota)."""
    now, times = time.time(), recent_messages[session_id]
    while times and now - times[0] > 60:
        times.popleft()
    if len(times) >= config.CHAT_MAX_PER_MINUTE:
        return True
    times.append(now)
    return False


def mentioned_inverters(reply):
    """Real inverter IDs that appear in the reply, with their plant — the chat turns them into links."""
    return {inverter: int(plant) for inverter, plant in get_store().inverter_plant.items() if inverter in reply}


@router.get("/chat/facts")
def chat_facts(plant: int, date: Optional[str] = None):
    """The facts the assistant answers from (also handy to check its answers)."""
    return facts_for(plant, date)


@router.post("/chat")
def chat(body: ChatRequest):
    """Answer an operator's question with Gemini, using only our computed facts."""
    if not config.GEMINI_API_KEY:
        return {"reply": OFFLINE_REPLY, "online": False}
    if too_many(body.session_id):
        return {"reply": "Too many questions in a minute. Please wait a moment and try again.", "online": True}
    history = conversations[body.session_id]
    reply = ask_gemini(body.message, facts_for(body.plant, body.date), list(history))
    if not reply:
        return {"reply": OFFLINE_REPLY, "online": False}
    history.extend([("user", body.message), ("model", reply)])
    return {"reply": reply, "online": True, "inverters": mentioned_inverters(reply)}
