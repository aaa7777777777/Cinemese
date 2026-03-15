"""
dashboard.py — FastAPI backend, character-aware engines.
Run: uvicorn planning.dashboard:app --reload --port 7331
"""
from __future__ import annotations
import time, random, uuid, sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yaml

from modules.emotion.emotion_engine import EmotionEngine
from modules.events.event_engine import EventEngine, Event

app = FastAPI(title="CharacterOS Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CONFIG   = yaml.safe_load((ROOT / "planning" / "planning_config.yaml").read_text())
CHAR_IDS = ["chandler_bing","joey_tribbiani","ross_geller",
            "monica_geller","rachel_green","phoebe_buffay"]

COMPATIBLE_PAIRS = {
    frozenset({"quiet_moment"}),
    frozenset({"quiet_moment","internal_shift"}),
    frozenset({"interaction"}),
    frozenset({"interaction","discovery"}),
    frozenset({"discovery","internal_shift"}),
}
COLLISION_THRESHOLD = CONFIG.get("collision_threshold", 80)
POST_BUDGET = 1.20


class AgentRuntime:
    def __init__(self, cid: str):
        soul_path = ROOT / "core" / "soul_doc" / f"{cid}.yaml"
        if not soul_path.exists():
            soul_path.write_text(yaml.dump({"character_id":cid,"trait_weights":{},"life_nodes":[]}))

        self.cid = cid
        self.emotion_engine = EmotionEngine(soul_path, CONFIG, self._writeback, character_id=cid)
        self.event_engine   = EventEngine(CONFIG, self._on_event, character_id=cid)
        self.log: list[dict] = []

    def tick(self):
        self.emotion_engine.tick()
        event = self.event_engine.tick(self.emotion_engine.current)
        if event:
            self.emotion_engine.receive_event(event.to_dict())

    def _writeback(self, node: dict):
        self._log("soul_doc","writeback",node["event"],0)

    def _on_event(self, event: Event):
        self._log("event",event.type,event.description,event.event_score)

    def _log(self, cat:str, label:str, body:str, score:float):
        self.log.insert(0,{"ts":time.strftime("%H:%M:%S"),"category":cat,
                            "label":label,"body":body,"score":round(score,1)})
        self.log = self.log[:60]

    @property
    def tension_score(self):
        return self.event_engine.current_score + self.emotion_engine.current.compute_micro_score()

    def profile(self):
        e = self.emotion_engine.current
        return {
            "id": self.cid,
            "emotion_color":  e.dominant_color,
            "valence":        round(e.valence,3),
            "arousal":        round(e.arousal,3),
            "drift_pressure": round(e.drift_pressure,3),
            "rhythm_phase":   e.rhythm_phase,
            "micro_score":    round(e.compute_micro_score(),1),
            "event_score":    round(self.event_engine.current_score,1),
            "tension_score":  round(self.tension_score,1),
            "last_event_type": (self.event_engine._current_event.type
                                if self.event_engine._current_event else "quiet_moment"),
        }


RUNTIMES: dict[str, AgentRuntime] = {}
def rt(cid:str) -> AgentRuntime:
    if cid not in RUNTIMES: RUNTIMES[cid] = AgentRuntime(cid)
    return RUNTIMES[cid]


class EmotionOverride(BaseModel):
    valence:float; arousal:float; pressure:float

class EventInject(BaseModel):
    type:str; description:str; intensity:float
    valence_push:float=0.0; arousal_push:float=0.0; source:str="user_inject"

class PhaseSet(BaseModel):
    phase:str


@app.get("/characters")
def list_chars():
    return [{"id":c,"name":c.replace("_"," ").title()} for c in CHAR_IDS]

@app.get("/character/{cid}/state")
def get_state(cid:str):
    r=rt(cid); r.tick(); return r.profile()

@app.get("/character/{cid}/log")
def get_log(cid:str):
    return rt(cid).log[:30]

@app.post("/character/{cid}/emotion/override")
def override_emotion(cid:str, body:EmotionOverride):
    r=rt(cid)
    r.emotion_engine.receive_planning_override({"valence":body.valence,"arousal":body.arousal,"pressure":body.pressure})
    r._log("emotion","override",f"v={body.valence:+.2f} a={body.arousal:.2f}",0)
    return r.emotion_engine.current.__dict__

@app.post("/character/{cid}/emotion/phase")
def set_phase(cid:str, body:PhaseSet):
    r=rt(cid); r.emotion_engine.state.rhythm_phase=body.phase
    r._log("emotion","phase",f"→ {body.phase}",0)
    return {"phase":body.phase}

@app.post("/character/{cid}/event/inject")
def inject_event(cid:str, body:EventInject):
    r=rt(cid)
    event=r.event_engine.inject({"type":body.type,"description":body.description,
        "intensity":body.intensity,"valence_push":body.valence_push,
        "arousal_push":body.arousal_push,"source":body.source,
        "scene_injection":body.description})
    r.emotion_engine.receive_event(event.to_dict())
    return event.to_dict()

@app.get("/character/{cid}/event/random")
def random_event(cid:str, event_type:Optional[str]=None):
    r=rt(cid)
    event=r.event_engine._generate(r.emotion_engine.current)
    if event_type: event.type=event_type
    return event.to_dict()

# ── Matching ──────────────────────────────────────────────────────────────────

def match_score(a:dict, b:dict) -> dict:
    ts_a,ts_b = a["tension_score"],b["tension_score"]
    combined  = ts_a+ts_b
    delta     = abs(ts_a-ts_b)
    within    = delta<=COLLISION_THRESHOLD
    under     = combined<=COLLISION_THRESHOLD*2
    pair      = frozenset({a.get("last_event_type","quiet_moment"),
                           b.get("last_event_type","quiet_moment")})
    ev_ok     = any(pair<=p or pair==p for p in COMPATIBLE_PAIRS) or CONFIG.get("allow_high_intensity",False)
    sess_i    = min(ts_a,ts_b)*0.30
    post_ok   = combined+sess_i*2 <= combined*POST_BUDGET
    can       = within and under and ev_ok and post_ok
    return {
        "can_match":         can,
        "quality_score":     round(max(0.0,100-abs(delta-30)*2),1),
        "tension_delta":     round(delta,1),
        "combined_score":    round(combined,1),
        "within_range":      within,
        "under_ceiling":     under,
        "event_compatible":  ev_ok,
        "post_budget_ok":    post_ok,
        "session_intensity": round(sess_i,2),
        "reject_reason": (None if can else
            "delta_too_large" if not within else
            "combined_too_high" if not under else
            "events_incompatible" if not ev_ok else "post_collision_spike"),
    }

@app.get("/character/{cid}/match/find")
def find_match(cid:str):
    r=rt(cid); r.tick(); agent=r.profile()
    results=[]
    for other_cid in CHAR_IDS:
        if other_cid==cid: continue
        o=rt(other_cid); o.tick(); p=o.profile()
        s=match_score(agent,p)
        results.append({"character_id":other_cid,**p,**s})
    results.sort(key=lambda x:(not x["can_match"],-x["quality_score"]))
    return {"agent":cid,"agent_score":round(r.tension_score,1),
            "best_match":next((x for x in results if x["can_match"]),None),
            "all_candidates":results}

@app.post("/character/{cid}/match/execute")
def execute_match(cid:str, partner_id:str):
    ra,rb=rt(cid),rt(partner_id)
    pa,pb=ra.profile(),rb.profile()
    gate=match_score(pa,pb)
    if not gate["can_match"]: return {"error":gate["reject_reason"],"gate":gate}
    sid=str(uuid.uuid4())[:8]; intensity=gate["session_intensity"]
    da=intensity*(0.8+random.uniform(-0.2,0.2))
    db=intensity*(0.8+random.uniform(-0.2,0.2))
    pre=pa["tension_score"]+pb["tension_score"]
    post=pre+da*50+db*50
    if post>pre*POST_BUDGET:
        scale=max(0.0,(pre*POST_BUDGET-pre)/(da*50+db*50+1e-9))
        da*=scale; db*=scale
    for r_,d in [(ra,da),(rb,db)]:
        ev=r_.event_engine.inject({"id":f"sess_{sid}","type":"interaction",
            "source":"agent_collision",
            "description":"an encounter with another agent. something was left unsaid.",
            "intensity":round(d,3),"valence_push":round(random.uniform(-0.1,0.15),3),
            "arousal_push":round(random.uniform(0.05,0.20),3),
            "scene_injection":"an encounter just happened."})
        r_.emotion_engine.receive_event(ev.to_dict())
    return {"session_id":sid,"gate":gate,"post_a":ra.profile(),"post_b":rb.profile()}

@app.websocket("/ws/{cid}")
async def ws(websocket:WebSocket, cid:str):
    await websocket.accept()
    r=rt(cid)
    try:
        import asyncio
        while True:
            r.tick(); await websocket.send_json(r.profile()); await asyncio.sleep(30)
    except WebSocketDisconnect: pass

# ── Dialogue & Scene endpoints ────────────────────────────────────────────────

import sys as _sys
_sys.path.insert(0, str(ROOT))
from network.dialogue_engine import DialogueEngine as _DE, GRAPH as _GRAPH
from modules.scene.scene_manager import SCENES as _SCENES

_sessions: dict[str, _DE] = {}

class DialogueStart(BaseModel):
    participants: list[str]
    scene_id: str = "central_perk"
    user_in_room: bool = False

class DialogueTurnReq(BaseModel):
    speaker_id: Optional[str] = None
    user_message: Optional[str] = None

class SceneTransition(BaseModel):
    scene_id: Optional[str] = None  # None = pick natural next

@app.get("/scenes")
def list_scenes():
    return [{"id": k, "name": v.name, "location": v.location,
             "social_mode": v.social_mode,
             "transition_to": v.transition_to} for k, v in _SCENES.items()]

@app.post("/dialogue/start")
def start_dialogue(body: DialogueStart):
    import uuid
    sid = str(uuid.uuid4())[:8]
    engine = _DE(body.participants, body.scene_id, body.user_in_room)
    _sessions[sid] = engine
    return {"session_id": sid, "scene": engine.session.scene.id,
            "participants": body.participants}

@app.post("/dialogue/{session_id}/turn")
def dialogue_turn(session_id: str, body: DialogueTurnReq):
    engine = _sessions.get(session_id)
    if not engine:
        return {"error": "session not found"}
    api_key = __import__("os").environ.get("ANTHROPIC_API_KEY")
    turn = engine.run_turn(
        speaker_id   = body.speaker_id,
        api_key      = api_key,
        user_message = body.user_message,
        dry_run      = not bool(api_key),
    )
    # Sync emotion states back to AgentRuntime
    for cid, em_engine in engine.engines.items():
        if cid in RUNTIMES:
            RUNTIMES[cid].emotion_engine.state = em_engine.state
    return {
        "speaker_id":   turn.speaker_id,
        "speaker_name": turn.speaker_name,
        "addressed_to": turn.addressed_to,
        "moment":       turn.moment_text,
        "mode":         turn.mode,
        "scene":        turn.scene_id,
    }

@app.post("/dialogue/{session_id}/scene")
def change_scene(session_id: str, body: SceneTransition):
    engine = _sessions.get(session_id)
    if not engine:
        return {"error": "session not found"}
    engine.transition_scene(body.scene_id)
    return {"new_scene": engine.session.scene.id,
            "name": engine.session.scene.name,
            "description": engine.session.scene.description}

@app.get("/dialogue/{session_id}/relationship/{char_a}/{char_b}")
def get_relationship(session_id: str, char_a: str, char_b: str):
    return _GRAPH.get(char_a, char_b)

# ── Thread endpoints ──────────────────────────────────────────────────────────

from network.thread_registry import REGISTRY as _REGISTRY, make_thread_id

class ThreadStart(BaseModel):
    agent_a_id:  str
    agent_b_id:  str
    scene_id:    str = "central_perk"
    owner_a:     Optional[str] = None
    owner_b:     Optional[str] = None

@app.post("/thread/find_or_create")
def find_or_create_thread(body: ThreadStart):
    """
    Matchmaker calls this instead of /dialogue/start.
    Returns the thread_id — new or existing.
    UI uses thread_id as the stable window key.
    """
    thread, is_new = _REGISTRY.find_or_create(
        body.agent_a_id, body.agent_b_id, body.owner_a, body.owner_b
    )
    return {
        "thread_id":     thread.thread_id,
        "is_new":        is_new,
        "episode_count": thread.episode_count,
        "last_met_at":   thread.last_met_at,
        "participants":  [thread.agent_a_id, thread.agent_b_id],
    }

@app.post("/thread/{thread_id}/start_session")
def start_thread_session(thread_id: str, scene_id: str = "central_perk"):
    """
    Open a live dialogue session on an existing thread.
    Loads memory automatically.
    """
    thread = _REGISTRY.get(thread_id)
    if not thread:
        return {"error": "thread not found"}

    participants = [thread.agent_a_id, thread.agent_b_id]
    engine = _DE(participants, scene_id=scene_id, thread=thread)
    _sessions[thread_id] = engine   # use thread_id as session key for stable routing
    return {
        "thread_id":     thread_id,
        "scene":         engine.session.scene.id,
        "participants":  participants,
        "episode_count": thread.episode_count,
        "has_memory":    thread.episode_count > 0,
    }

@app.get("/thread/{thread_id}")
def get_thread(thread_id: str):
    thread = _REGISTRY.get(thread_id)
    if not thread:
        return {"error": "not found"}
    return thread.to_dict()

@app.get("/agent/{agent_id}/threads")
def get_agent_threads(agent_id: str):
    """All threads this agent has — for inbox view."""
    threads = _REGISTRY.threads_for_agent(agent_id)
    return [
        {
            "thread_id":     t.thread_id,
            "other_agent":   t.agent_b_id if t.agent_a_id == agent_id else t.agent_a_id,
            "episode_count": t.episode_count,
            "last_met_at":   t.last_met_at,
            "relationship":  t.relationship_a_to_b if t.agent_a_id == agent_id
                             else t.relationship_b_to_a,
        }
        for t in threads
    ]

@app.post("/thread/{thread_id}/close_episode")
def close_episode(thread_id: str, outcome_valence: float = 0.0):
    """
    Called when a dialogue session ends.
    Records the episode into the thread and updates relationship.
    """
    thread = _REGISTRY.get(thread_id)
    engine = _sessions.get(thread_id)
    if not thread or not engine:
        return {"error": "thread or session not found"}

    session  = engine.session
    turns    = len(session.turns)
    scene_id = session.scene.id
    intensity = min(0.9, 0.2 + turns * 0.06)

    # Build summaries from last turn
    def _summary(agent_id):
        own = [t.moment_text for t in session.turns if t.speaker_id == agent_id]
        other = [t.moment_text for t in session.turns if t.speaker_id != agent_id]
        if own:
            return own[-1][:80] + ("…" if len(own[-1]) > 80 else "")
        return "was present."

    sa = _summary(thread.agent_a_id)
    sb = _summary(thread.agent_b_id)

    # Update relationship cache
    from network.relationship_graph import CACHE as _REL_CACHE
    _REL_CACHE.update_after_episode(
        thread.agent_a_id, thread.agent_b_id,
        intensity, outcome_valence, turns
    )
    rel_ab = _REL_CACHE.get(thread.agent_a_id, thread.agent_b_id)
    rel_ba = _REL_CACHE.get(thread.agent_b_id, thread.agent_a_id)

    _REGISTRY.record_episode(
        thread, scene_id, turns, intensity, outcome_valence,
        sa, sb, rel_ab, rel_ba
    )

    return {
        "thread_id":     thread_id,
        "episode_number": thread.episode_count,
        "intensity":     intensity,
        "outcome_valence": outcome_valence,
        "relationship_updated": True,
    }
