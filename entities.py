# entities.py
from __future__ import annotations
from dataclasses import dataclass, field
import random
from typing import Dict

SIDES = ("North", "East", "South", "West")

@dataclass
class Player:
    base_hp: int = 20
    base_damage: int = 4
    wood: int = 5
    food: int = 3
    seeds: int = 0
    defending: bool = False
    side: str = "Center"  # set during night
    day_actions_per_day: int = 14
    gather_bonus: int = 0

    # Computed each morning:
    max_hp: int = 20
    hp: int = 20
    damage: int = 4

    def update_stats(self, day_num: int):
        self.max_hp = self.base_hp + day_num * 2
        self.damage = self.base_damage + (day_num // 2)
        # heal if new max_hp exceeds current hp
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def heal(self, amount: int) -> int:
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def rest(self) -> int:
        if self.food > 0:
            self.food -= 1
            return self.heal(5)
        return self.heal(3)

@dataclass
class Fence:
    name: str
    max_hp: int = 20
    hp: int = 20

    def is_up(self) -> bool:
        return self.hp > 0

    def repair(self, amt: int) -> int:
        amt = max(0, min(amt, self.max_hp - self.hp))
        self.hp += amt
        return amt

@dataclass
class Enemy:
    side: str
    hp: int
    dmg: int
    name: str = field(default_factory=lambda: random.choice(
        ["Wisp", "Crawler", "Gnashling", "Hollow", "Stalker", "Skitter"]))

    def alive(self) -> bool:
        return self.hp > 0

def scaled_enemy(day_num: int, side: str) -> Enemy:
    base_hp = 5 + int(day_num * 1.2)
    base_dmg = 2 + int(day_num * 0.5)
    hp = base_hp + random.randint(-1, 2)
    dmg = base_dmg + random.choice([0, 0, 1])
    return Enemy(side=side, hp=max(1, hp), dmg=dmg)

@dataclass
class GameState:
    day_num: int = 1
    player: Player = field(default_factory=Player)
    fences: Dict[str, Fence] = field(default_factory=lambda: {
        "North": Fence("North Fence"),
        "East":  Fence("East Fence"),
        "South": Fence("South Fence"),
        "West":  Fence("West Fence"),
    })
    alive: bool = True
    crafted: set = field(default_factory=set)
    reinforce_cost: int = 10
    traps: int = 0
    defense_bonus: float = 0.0
    campfire_on: bool = True
    has_field: bool = False
    field_state: str = "empty"
    field_timer: int = 0
    field_watered: int = 0
    daily_wood_bonus_combo: int = 0
    has_bow: bool = False
    arrows: int = 0
    has_watchtower: bool = False
    in_tower: bool = False

    def fence(self, side: str) -> Fence:
        return self.fences[side]