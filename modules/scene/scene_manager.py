"""
scene_manager.py
Scene definitions and transitions.
A scene is the physical and social container for dialogue.
It affects: available props, tone register, who can plausibly be there,
social pressure (public vs private), and what kinds of events are natural.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Scene:
    id:           str
    name:         str
    location:     str          # short label
    description:  str          # one sentence, for prompt injection
    time_options: list[str]    # which times of day feel natural here
    props:        list[str]    # physical objects available
    social_mode:  str          # private | semi_public | public
    tone_modifier: str         # how this place shapes emotional register
    event_weights: dict        # adjusts event type probabilities
    transition_to: list[str]   # which scenes this naturally leads to


SCENES: dict[str, Scene] = {

    "central_perk": Scene(
        id          = "central_perk",
        name        = "Central Perk",
        location    = "the coffee shop",
        description = "Central Perk. The orange couch. The smell of coffee that nobody is really tasting.",
        time_options = ["morning", "afternoon", "evening"],
        props        = ["coffee cup", "couch", "counter", "the couch arm", "a mug going cold"],
        social_mode  = "semi_public",
        tone_modifier = "slightly performative — they're in public but it's their public",
        event_weights = {"interaction": 0.40, "discovery": 0.20, "quiet_moment": 0.25,
                         "conflict": 0.10, "internal_shift": 0.05},
        transition_to = ["monica_apartment", "chandler_joey_apartment", "street"],
    ),

    "monica_apartment": Scene(
        id          = "monica_apartment",
        name        = "Monica's apartment",
        location    = "the apartment",
        description = "Monica's apartment. The kitchen that is always clean enough. The living area where things actually happen.",
        time_options = ["morning", "afternoon", "evening", "late_night"],
        props        = ["the couch", "kitchen counter", "the window", "a dish towel", "leftovers"],
        social_mode  = "private",
        tone_modifier = "where things actually get said — private enough to be honest",
        event_weights = {"interaction": 0.30, "quiet_moment": 0.25, "conflict": 0.20,
                         "internal_shift": 0.15, "discovery": 0.10},
        transition_to = ["chandler_joey_apartment", "central_perk", "hallway", "street"],
    ),

    "chandler_joey_apartment": Scene(
        id          = "chandler_joey_apartment",
        name        = "Chandler and Joey's apartment",
        location    = "across the hall",
        description = "Chandler and Joey's apartment. The foosball table. The canoe. The specific entropy of two men who've lived together for years.",
        time_options = ["afternoon", "evening", "late_night"],
        props        = ["the foosball table", "the couch", "the canoe", "the TV", "a game controller", "a sandwich"],
        social_mode  = "private",
        tone_modifier = "relaxed, honest in a low-key way — nobody is performing here",
        event_weights = {"quiet_moment": 0.35, "interaction": 0.30, "internal_shift": 0.20,
                         "discovery": 0.10, "conflict": 0.05},
        transition_to = ["monica_apartment", "hallway", "central_perk"],
    ),

    "hallway": Scene(
        id          = "hallway",
        name        = "The hallway",
        location    = "the hallway",
        description = "The hallway between the apartments. Neither of them planned to be here at the same time.",
        time_options = ["morning", "afternoon", "evening", "late_night"],
        props        = ["the door", "the stairs", "the space between them"],
        social_mode  = "semi_public",
        tone_modifier = "transitional — things said here are between places, less committed",
        event_weights = {"interaction": 0.45, "quiet_moment": 0.25, "discovery": 0.15,
                         "internal_shift": 0.10, "conflict": 0.05},
        transition_to = ["monica_apartment", "chandler_joey_apartment", "street"],
    ),

    "street": Scene(
        id          = "street",
        name        = "New York street",
        location    = "outside",
        description = "New York. The street outside the building. The city doing what it does around them.",
        time_options = ["morning", "afternoon", "evening"],
        props        = ["a cab", "the sidewalk", "a bodega", "traffic noise", "a bench"],
        social_mode  = "public",
        tone_modifier = "movement and noise — conversations here are interrupted, briefer, less resolved",
        event_weights = {"interaction": 0.35, "quiet_moment": 0.20, "discovery": 0.20,
                         "conflict": 0.15, "internal_shift": 0.10},
        transition_to = ["central_perk", "monica_apartment", "joey_work", "ross_museum"],
    ),

    "ross_museum": Scene(
        id          = "ross_museum",
        name        = "The natural history museum",
        location    = "the museum",
        description = "The museum. Ross's domain. The dinosaurs. The specific quiet of very old things.",
        time_options = ["morning", "afternoon"],
        props        = ["a fossil", "the exhibit", "a display case", "his office", "a grant proposal"],
        social_mode  = "semi_public",
        tone_modifier = "Ross is more himself here — slightly more confident, slightly more oblivious",
        event_weights = {"discovery": 0.35, "quiet_moment": 0.25, "interaction": 0.20,
                         "internal_shift": 0.15, "conflict": 0.05},
        transition_to = ["central_perk", "street", "monica_apartment"],
    ),

    "joey_work": Scene(
        id          = "joey_work",
        name        = "The audition / set",
        location    = "an audition room",
        description = "A casting office or a set. The waiting room where everything is possible and nothing is certain.",
        time_options = ["morning", "afternoon"],
        props        = ["sides", "a headshot", "a waiting room chair", "a casting director's desk"],
        social_mode  = "public",
        tone_modifier = "Joey is most himself and most anxious here simultaneously",
        event_weights = {"conflict": 0.25, "discovery": 0.30, "interaction": 0.25,
                         "internal_shift": 0.15, "quiet_moment": 0.05},
        transition_to = ["central_perk", "chandler_joey_apartment", "street"],
    ),

    "phoebe_massage": Scene(
        id          = "phoebe_massage",
        name        = "Phoebe's massage studio",
        location    = "the massage studio",
        description = "Phoebe's massage space. Crystals. The specific quiet she creates on purpose.",
        time_options = ["morning", "afternoon"],
        props        = ["crystals", "the massage table", "incense", "a dreamcatcher", "her guitar in the corner"],
        social_mode  = "private",
        tone_modifier = "Phoebe is most authoritative here — this is her room",
        event_weights = {"quiet_moment": 0.35, "interaction": 0.30, "internal_shift": 0.25,
                         "discovery": 0.08, "conflict": 0.02},
        transition_to = ["central_perk", "street", "monica_apartment"],
    ),

    "late_night_couch": Scene(
        id          = "late_night_couch",
        name        = "The couch, late",
        location    = "the couch",
        description = "The couch. Late. The TV on or not. The city outside not visible but audible.",
        time_options = ["late_night"],
        props        = ["the remote", "a blanket", "cold leftovers", "a half-empty glass", "phone face-down"],
        social_mode  = "private",
        tone_modifier = "defenses are lower — what gets said here is more true than what gets said at 2pm",
        event_weights = {"quiet_moment": 0.40, "internal_shift": 0.30, "interaction": 0.20,
                         "discovery": 0.08, "conflict": 0.02},
        transition_to = ["monica_apartment", "chandler_joey_apartment"],
    ),
}


class SceneManager:

    def __init__(self, initial_scene_id: str = "central_perk"):
        self.current: Scene = SCENES.get(initial_scene_id, SCENES["central_perk"])
        self.history: list[str] = [self.current.id]

    def transition(self, scene_id: Optional[str] = None) -> Scene:
        """Move to a new scene. If no id given, pick a natural one."""
        if scene_id and scene_id in SCENES:
            self.current = SCENES[scene_id]
        else:
            # Pick from natural transitions weighted by current scene
            candidates = [s for s in self.current.transition_to if s in SCENES]
            if candidates:
                self.current = SCENES[random.choice(candidates)]
        self.history.append(self.current.id)
        return self.current

    def random_prop(self) -> str:
        return random.choice(self.current.props)

    def to_prompt_fragment(self, time_of_day: str = "evening") -> str:
        s = self.current
        return (
            f"{s.description}\n"
            f"Time: {time_of_day}. Social register: {s.tone_modifier}."
        )

    def get_event_weights(self) -> dict:
        return self.current.event_weights

    @classmethod
    def from_id(cls, scene_id: str) -> "SceneManager":
        return cls(scene_id)
