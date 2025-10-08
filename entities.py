# entities.py
from __future__ import annotations
from dataclasses import dataclass, field
import random
from typing import Dict

SIDES = ("North", "East", "South", "West")

@dataclass
class Player:
    max_hp: int = 20
    hp: int = 20
    wood: int = 5
    food: int = 3
    seeds: int = 0
    damage: int = 4
    defending: bool = False
    side: str = "Center"  # Center by day; at night set to one of SIDES
    # day config
    day_actions_per_day: int = 14

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
    # gentle scaling
    base_hp = 5 + day_num // 1
    base_dmg = 2 + max(0, (day_num - 1) // 2)
    # randomize a bit
    hp = base_hp + random.randint(0, 2)
    dmg = base_dmg + random.randint(0, 1)
    return Enemy(side=side, hp=hp, dmg=dmg)

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
    campfire_on: bool = True
    traps: int = 0

    def fence(self, side: str) -> Fence:
        return self.fences[side]