"""
matchmaker.py — single source of truth for all agent matching logic.

Three concerns, one file:
  A. Stranger relationship init  — derive initial RelationshipVector from soul_docs
  B. World collision             — compute worldview_gap and displacement outcome
  C. Match finding               — score candidates, return MatchResult

Replaces: network/random_match.py + worlds/world_matchmaker.py
"""
from __future__ import annotations
import random, yaml, json, time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

ROOT = Path(__file__).parent.parent

# ─────────────────────────────────────────────
# World helpers
# ─────────────────────────────────────────────

def load_nation(nation: str) -> dict:
    p = ROOT / "worlds" / "nations" / f"{nation}.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else {}

def get_world_coords(soul_doc: dict) -> dict:
    wid = soul_doc.get("world_id", "")
    if wid:
        parts   = wid.split("_")
        nation  = parts[0] if parts else "usa"
        era     = parts[1] if len(parts) > 1 else "2000s"
        env     = parts[2] if len(parts) > 2 else "urban"
    else:
        tags   = soul_doc.get("world_tags", [])
        nations = {"china","usa","japan","uk","korea","france"}
        eras    = {f"{y}s" for y in range(1900,2030,10)}
        envs    = {"urban","rural","school","suburban"}
        nation  = next((t for t in tags if t in nations), "usa")
        era     = next((t for t in tags if t in eras), "2000s")
        env     = next((t for t in tags if t in envs), "urban")
        wid     = f"{nation}_{era}_{env}"
    nation_data = load_nation(nation)
    decade      = nation_data.get("decades", {}).get(era, {})
    return {
        "world_id":    wid,
        "nation":      nation,
        "era":         era,
        "env":         env,
        "label":       nation_data.get("label", nation),
        "era_label":   decade.get("era_label", era),
        "economic_trend":   (decade.get("economic_trend") or "").strip(),
        "cultural_trend":   (decade.get("cultural_trend") or "").strip(),
        "background_noise": (decade.get("background_noise") or "").strip(),
    }

def world_prompt_fragment(wc: dict, displaced_count: int = 0) -> str:
    parts = [f"你来自：{wc.get('label','')} {wc.get('era_label', wc.get('era',''))}。"]
    for key in ("economic_trend","cultural_trend","background_noise"):
        v = wc.get(key,"")
        if v: parts.append(v)
    if displaced_count > 0:
        parts.append(f"\n你的原有事件轨道已断开过 {displaced_count} 次。你记得以前，但那个位置不在了。")
    return "\n".join(parts)


# ─────────────────────────────────────────────
# A. Stranger relationship init
# ─────────────────────────────────────────────

_COMP = [
    ("deflection_via_humor","genuine_vulnerability"),
    ("control_need","impulsivity"),
    ("intellectual_drive","emotional_directness"),
    ("competitiveness","warmth"),
    ("cynicism","spiritual_openness"),
    ("observational_acuity","social_fluency"),
]
_MIRROR  = ["loyalty","warmth_when_safe","genuine_vulnerability","nurturing","empathy","resilience"]
_FRIC    = [("competitiveness","competitiveness"),("control_need","impulsivity"),("cynicism","spiritual_openness")]
_TRANS   = ["genuine_vulnerability","loyalty","empathy","warmth_when_safe"]

def _baseline_emotion(t: dict) -> dict:
    return {
        "valence": t.get("self_worth",0.5)*0.4 + t.get("warmth_when_safe",0.5)*0.3
                   - t.get("cynicism",0.3)*0.2 - t.get("fear_of_permanence",0.4)*0.1,
        "arousal": t.get("deflection_via_humor",0.5)*0.3 + t.get("genuine_vulnerability",0.3)*0.2,
    }

def _trait_axes(ta: dict, tb: dict) -> tuple:
    res=fric=trans=0.0; n=0
    for a,b in _COMP:
        res += (ta.get(a,.5)*tb.get(b,.5))**.5*.8 + (ta.get(b,.5)*tb.get(a,.5))**.5*.6; n+=2
    for t in _MIRROR:
        va,vb=ta.get(t,.3),tb.get(t,.3); sim=1-abs(va-vb); avg=(va+vb)/2
        res+=sim*avg*1.2; trans+=avg*sim*.8; n+=1
    for a,b in _FRIC:
        va,vb=ta.get(a,.3),tb.get(b,.3)
        fric += (va*vb)**.5*1.5 if a==b else abs(va-.5)*2*abs(vb-.5)*2*.8; n+=1
    for t in _TRANS: trans+=(ta.get(t,.3)*tb.get(t,.3))**.5
    n=max(n,1)
    return min(1.0,res/n), min(1.0,fric/(len(_FRIC)+.5)), min(1.0,trans/(len(_TRANS)+1))

def _register(resonance,friction,fit,va,vb):
    if resonance>.65 and friction<.20: return "something immediately recognisable. easy to be near.","positive"
    if resonance>.50 and friction>.35: return "interesting and slightly difficult.","complicated"
    if friction>.55:                   return "a pull and a resistance.","complicated"
    if fit>.60 and resonance<.40:      return "emotionally in the same register, even as strangers.","neutral"
    if vb-va>.3:                       return "steadier than expected. slightly disarming.","neutral"
    if vb-va<-.3:                      return "carrying something. not sure if that's an opening.","wary"
    return "unclear yet. first exchanges will settle this.","neutral"

@dataclass
class RelationshipVector:
    from_id:str; to_id:str
    weight:float; friction:float; emotion_transfer:float; address_weight:float
    register:str; valence:str
    resonance:float=0.0; fit:float=0.0; overlap:float=0.0; authored:bool=False
    def to_dict(self):
        return {k:v for k,v in self.__dict__.items() if k not in ("from_id","to_id")}

def init_stranger(doc_a:dict, doc_b:dict) -> tuple:
    ta,tb=doc_a.get("trait_weights",{}),doc_b.get("trait_weights",{})
    res,fric_t,trans = _trait_axes(ta,tb)
    ea,eb = _baseline_emotion(ta), _baseline_emotion(tb)
    vgap  = abs(ea["valence"]-eb["valence"])
    agap  = abs(ea["arousal"]-eb["arousal"])
    fit   = min(1.0, max(.1,1-max(0,vgap-.3)*2)*.6 + max(.1,1-agap*1.2)*.4)
    overlap = min(1.0, len(set(doc_a.get("world_tags",[]))&set(doc_b.get("world_tags",[])))
                       /max(len(set(doc_a.get("world_tags",[]))|set(doc_b.get("world_tags",[]))),1))
    fric  = min(.95, fric_t*.65 + agap*.4*.35)
    w     = res*.50 + fit*.30 + overlap*.20
    aw    = max(.05, res*.20+overlap*.10)
    em    = min(.90, trans*.60+fit*.25+overlap*.15)
    id_a,id_b = doc_a.get("character_id","a"), doc_b.get("character_id","b")
    reg_ab,val_ab = _register(res,fric,fit,ea["valence"],eb["valence"])
    reg_ba,val_ba = _register(res,fric,fit,eb["valence"],ea["valence"])
    return (RelationshipVector(id_a,id_b,w,fric,em,aw,reg_ab,val_ab,res,fit,overlap),
            RelationshipVector(id_b,id_a,w,fric,em,aw,reg_ba,val_ba,res,fit,overlap))


# ─────────────────────────────────────────────
# B. World collision
# ─────────────────────────────────────────────

_NDIST = {
    ("china","china"):0,("japan","japan"):0,("usa","usa"):0,("uk","uk"):0,
    ("korea","korea"):0,("france","france"):0,
    ("china","japan"):.28,("japan","china"):.28,
    ("usa","uk"):.15,("uk","usa"):.15,
    ("korea","japan"):.22,("japan","korea"):.22,
    ("china","korea"):.30,("korea","china"):.30,
    ("china","usa"):.75,("usa","china"):.75,
    ("china","uk"):.70,("uk","china"):.70,
    ("japan","usa"):.60,("usa","japan"):.60,
    ("usa","france"):.30,("france","usa"):.30,
    ("uk","france"):.25,("france","uk"):.25,
}
_ERA = {f"{y}s":y for y in range(1900,2030,10)}
_ENV = {("urban","urban"):0,("suburban","suburban"):0,("rural","rural"):0,("school","school"):0,
        ("urban","suburban"):.20,("suburban","urban"):.20,("urban","rural"):.70,("rural","urban"):.70,
        ("school","urban"):.25,("urban","school"):.25,("school","rural"):.60,("rural","school"):.60,
        ("suburban","rural"):.55,("rural","suburban"):.55,("school","suburban"):.30,("suburban","school"):.30}

def world_gap(wc_a:dict, wc_b:dict) -> float:
    nd = _NDIST.get((wc_a["nation"],wc_b["nation"]), .80)
    ed = min(1.0, abs(_ERA.get(wc_a["era"],2000)-_ERA.get(wc_b["era"],2000))/80.0)
    vd = _ENV.get((wc_a["env"],wc_b["env"]), .50)
    return round(min(1.0, nd*.40+ed*.35+vd*.25), 4)

def resilience(soul:dict) -> float:
    t=soul.get("trait_weights",{})
    return round(min(1.0, t.get("quiet_resilience",.5)*.35+t.get("self_sufficiency",.5)*.30
                        +t.get("adaptability",.4)*.20+t.get("identity_stability",.5)*.15),3)

@dataclass
class CollisionResult:
    gap:float; outcome:str
    displaced_id:Optional[str]; both_displaced:bool; unstable_id:Optional[str]
    description:str; world_context:dict

def compute_collision(id_a,wc_a,soul_a,disp_a, id_b,wc_b,soul_b,disp_b) -> CollisionResult:
    gap   = world_gap(wc_a, wc_b)
    ra,rb = resilience(soul_a), resilience(soul_b)
    second= disp_a>0 or disp_b>0
    eg    = min(1.0, gap*(1.25 if second else 1.0))
    wctx  = {"a": world_prompt_fragment(wc_a,disp_a),
             "b": world_prompt_fragment(wc_b,disp_b), "gap": gap}
    if eg<.30:
        return CollisionResult(gap,"smooth",None,False,None,f"世界差距{gap:.2f}，顺畅相遇。",wctx)
    if eg<.55:
        w=id_a if ra<rb else id_b
        return CollisionResult(gap,"friction",None,False,w,f"世界差距{gap:.2f}。{w}情绪受冲击。",wctx)
    if eg<.75:
        d,o,dr,sr=(id_a,id_b,ra,rb) if ra<=rb else (id_b,id_a,rb,ra)
        u=o if second else None
        return CollisionResult(gap,"displace_one",d,False,u,
            f"世界差距{gap:.2f}。{d}（韧性{dr:.2f}）失去轨道，情绪归零。"
            +(f" {o}轨道标记不稳定。" if u else ""),wctx)
    w=id_a if ra<=rb else id_b
    return CollisionResult(gap,"displace_both",w,True,None,
        f"世界差距{gap:.2f}。两人都将失去轨道。{w}先断开。再也回不去原本事件。",wctx)

def execute_displacement(agent_id:str, by_world_id:str, engines:dict):
    if agent_id in engines:
        e=engines[agent_id].emotion_engine; ev=engines[agent_id].event_engine
        e.state.valence=e.state.arousal=e.state.drift_pressure=0.0
        e.state.dominant_color="归零。原来的世界已经不在了。"
        e.state.rhythm_phase="trough"; e._rhythm_timer=time.time()
        e._writeback_timers={}; ev._current_event=None; ev._last_event_time=time.time()
    sp=ROOT/"core"/"soul_doc"/f"{agent_id}.yaml"
    if sp.exists():
        doc=yaml.safe_load(sp.read_text()) or {}
        doc.setdefault("life_nodes",[]).append({
            "id":f"displacement_{int(time.time())}","ts":time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event":f"遇到来自{by_world_id}的人。原有事件轨道断开。归零。",
            "delta":{"self_worth":-.05,"adaptability":+.08,"identity_stability":-.10},
            "locked":False,"note":"displacement — permanent"})
        sp.write_text(yaml.dump(doc,allow_unicode=True,default_flow_style=False))


# ─────────────────────────────────────────────
# C. Match finding
# ─────────────────────────────────────────────

_AUTHORED_PATH = ROOT/"network"/"relationship_graph"/"relationships.yaml"
_CACHE_PATH    = ROOT/"network"/"relationship_graph"/"stranger_cache.json"
_RCACHE: dict[tuple,RelationshipVector] = {}

def _load_authored_rels():
    if not _AUTHORED_PATH.exists(): return
    data=yaml.safe_load(_AUTHORED_PATH.read_text()) or {}
    for fid,targets in data.get("relationships",{}).items():
        for tid,p in targets.items():
            _RCACHE[(fid,tid)]=RelationshipVector(
                fid,tid,p.get("weight",.5),p.get("friction",.2),
                p.get("emotion_transfer",.3),p.get("address_weight",.15),
                p.get("register",""),p.get("valence","neutral"),authored=True)
_load_authored_rels()

def get_relationship(id_a,id_b,doc_a=None,doc_b=None) -> dict:
    for k in [(id_a,id_b),(id_b,id_a)]:
        if k in _RCACHE: return _RCACHE[k].to_dict()
    if doc_a and doc_b:
        va,vb=init_stranger(doc_a,doc_b)
        _RCACHE[(id_a,id_b)]=va; _RCACHE[(id_b,id_a)]=vb
        _flush_rcache(); return va.to_dict()
    return {"weight":.3,"friction":.2,"emotion_transfer":.25,"address_weight":.10,
            "register":"stranger","valence":"neutral"}

def update_relationship(id_a,id_b,intensity,outcome_valence):
    for k in [(id_a,id_b),(id_b,id_a)]:
        if k not in _RCACHE: continue
        v=_RCACHE[k]
        v.weight=min(.95,v.weight+intensity*.04)
        v.emotion_transfer=min(.85,v.emotion_transfer+intensity*.03)
        v.address_weight=min(.45,v.address_weight+intensity*.04)
        if outcome_valence>.3: v.friction=max(.02,v.friction-intensity*.03)
        elif outcome_valence<-.3: v.friction=min(.90,v.friction+intensity*.04)
    _flush_rcache()

def _flush_rcache():
    try:
        _CACHE_PATH.write_text(json.dumps(
            {f"{fid}||{tid}":v.to_dict() for (fid,tid),v in _RCACHE.items() if not v.authored},
            indent=2,ensure_ascii=False))
    except: pass

COLLISION_THRESHOLD=80; POST_BUDGET=1.20
_COMPAT={frozenset({"quiet_moment"}),frozenset({"quiet_moment","internal_shift"}),
         frozenset({"interaction"}),frozenset({"interaction","discovery"}),
         frozenset({"discovery","internal_shift"})}

@dataclass
class MatchResult:
    agent_a_id:str; agent_b_id:str
    quality_score:float
    tension_gate:dict; world_collision:CollisionResult
    relationship:dict; session_config:dict

def find_match(agent_id,agent_profile,pool,mode="normal") -> Optional[MatchResult]:
    sp=ROOT/"core"/"soul_doc"/f"{agent_id}.yaml"
    doc_a=yaml.safe_load(sp.read_text()) if sp.exists() else {}
    wc_a =get_world_coords(doc_a)
    da   =agent_profile.get("displaced_count",0)
    ts_a =agent_profile.get("tension_score",30.0)
    ev_a =agent_profile.get("last_event_type","quiet_moment")

    scored=[]
    for c in pool:
        if c["id"]==agent_id: continue
        doc_b=c.get("soul_doc",{}); wc_b=c.get("world_coords") or get_world_coords(doc_b)
        ts_b=c.get("tension_score",30.0); ev_b=c.get("last_event_type","quiet_moment")
        db=c.get("displaced_count",0)
        col=compute_collision(agent_id,wc_a,doc_a,da, c["id"],wc_b,doc_b,db)
        if col.outcome=="displace_both" and mode!="wild" and da==0 and db==0: continue
        combined=ts_a+ts_b; delta=abs(ts_a-ts_b)
        pair=frozenset({ev_a,ev_b})
        t_ok=(delta<=COLLISION_THRESHOLD and combined<=COLLISION_THRESHOLD*2
              and any(pair<=p or pair==p for p in _COMPAT)
              and combined+min(ts_a,ts_b)*.30*2<=combined*POST_BUDGET)
        rel=get_relationship(agent_id,c["id"],doc_a,doc_b)
        rq=rel.get("weight",.3)*.6-rel.get("friction",.2)*.3
        tq=max(0.0,1.0-abs(delta-30)/50)
        g=col.gap
        wq=(1.0-abs(g-.325)/.175) if .15<=g<=.50 else max(0.0,1.0-abs(g-.325))
        score=rq*.35+tq*.35+wq*.20+(0.10 if da>0 or db>0 else 0)+(0.10 if t_ok else -0.20)
        scored.append((score,c,col,rel))

    if not scored: return None
    scored.sort(key=lambda x:-x[0])
    top=scored[:min(3,len(scored))]
    score,winner,col,rel=random.choices(top,weights=[s+.1 for s,*_ in top],k=1)[0]
    scene=("central_perk" if col.gap<.30 else "hallway" if col.gap<.55 else "street")
    return MatchResult(
        agent_a_id=agent_id, agent_b_id=winner["id"],
        quality_score=round(score,3),
        tension_gate={"ts_a":ts_a,"ts_b":winner.get("tension_score",30),"delta":abs(ts_a-winner.get("tension_score",30))},
        world_collision=col, relationship=rel,
        session_config={"participants":[agent_id,winner["id"]],"scene_id":scene,
                        "world_a":col.world_context.get("a",""),
                        "world_b":col.world_context.get("b","")})
