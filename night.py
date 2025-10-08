# night.py
from __future__ import annotations
import random
from typing import Dict, List, Tuple
from entities import GameState, Enemy, SIDES, scaled_enemy

DIV = "\n" + "=" * 56 + "\n"

def _spawn_pattern(day: int, current_enemies: int, max_alive: int) -> List[Tuple[str, int]]:
    """
    Smarter spawn pacing with cap. Returns list of (side, count).
    """
    if current_enemies >= max_alive:
        return []  # Too many alive already

    # difficulty parameters
    day_clamped = min(day, 5)
    spawn_chance = [0.4, 0.5, 0.6, 0.7, 0.8][day_clamped - 1]
    per_spawn = [1, 2, 2, 3, 3][day_clamped - 1]
    if random.random() > spawn_chance:
        return []  # no spawn this turn

    # how many groups to spawn (more later days)
    groups = 1 if day < 3 else 2 if day < 5 else 3
    result = []
    remaining_slots = max_alive - current_enemies
    for _ in range(groups):
        if remaining_slots <= 0:
            break
        side = random.choice(SIDES)
        count = min(per_spawn, remaining_slots)
        result.append((side, count))
        remaining_slots -= count
    return result

def _print_board(gs: GameState, enemy_queues: Dict[str, List[Enemy]]):
    # A compact HUD view listing each side
    print(DIV)
    print(f" NIGHT — Day {gs.day_num}")
    print(f" You are defending: [{gs.player.side}]   HP {gs.player.hp}/{gs.player.max_hp}")
    print(" Fences:")
    for s in SIDES:
        f = gs.fence(s)
        fence_bar = f"{f.hp:02d}/{f.max_hp}"
        q = enemy_queues[s]
        q_str = ", ".join(
            f"{e.name}({e.hp})" if gs.campfire_on else "? (?)"
            for e in q
        ) if q else "—"
        print(f"  {s:<5} | Fence {fence_bar} | Enemies: {q_str}")
    print(DIV)

def _player_menu() -> str:
    print("Choose your action:")
    print(" 1) Move to North (costs 1 turn)")
    print(" 2) Move to East  (costs 1 turn)")
    print(" 3) Move to South (costs 1 turn)")
    print(" 4) Move to West  (costs 1 turn)")
    print(" 5) Attack (adjacent side you're on)")
    print(" 6) Defend (reduce incoming at your side this turn)")
    print(" 7) Wait")
    choice = input("> ").strip()
    return choice

def _resolve_player_action(gs: GameState, enemy_queues: Dict[str, List[Enemy]]) -> bool:
    """
    Returns True if the action consumed the player's turn (most do).
    """
    gs.player.defending = False  # reset each turn; only lasts one turn

    choice = _player_menu()
    if choice in ("1", "2", "3", "4"):
        target = {"1": "North", "2": "East", "3": "South", "4": "West"}[choice]
        if gs.player.side == target:
            print(f"You're already at the {target} side — no need to move.")
            return False
        gs.player.side = target
        print(f"You dash to the {target} side.")
        return True

    if choice == "5":  # Attack
        side = gs.player.side
        q = enemy_queues[side]
        if not q:
            print(f"No enemy in reach on the {side} side.")
            return True
        # Focus lowest HP
        target = min(q, key=lambda e: e.hp)
        dmg = gs.player.damage + random.randint(0, 2)
        target.hp = max(0, target.hp - dmg)
        print(f"You strike the {target.name} on the {side} side for {dmg}!")
        if target.hp <= 0:
            print(f"The {target.name} collapses.")
            q.remove(target)
        return True

    if choice == "6":  # Defend
        gs.player.defending = True
        print(f"You brace against the {gs.player.side} fence, shield up.")
        return True

    if choice == "7":  # Wait
        print("You steady your breath...")
        return True

    print("Pick a number from the list.")
    return False

def _enemies_attack_and_move(gs: GameState, enemy_queues: Dict[str, List[Enemy]]):
    """
    Each side: one random enemy acts. If fence up -> damage fence.
    If fence down -> they breach and damage the player unless he is
    defending that side (mitigated).
    """
    for side in SIDES:
        q = enemy_queues[side]
        if not q:
            continue
        # One enemy acts per side (keeps turns readable)
        attacker = random.choice(q)
        fence = gs.fence(side)
        if fence.is_up():
            fence.hp = max(0, fence.hp - attacker.dmg)
            print(f"{attacker.name} batters the {side} fence! (-{attacker.dmg})")
        else:
            # Breach damage to player if not defended here
            dmg = attacker.dmg
            if gs.player.side == side:
                # He's at this side; defending reduces damage
                if gs.player.defending:
                    dmg = max(0, dmg - 2)
                gs.player.hp = max(0, gs.player.hp - dmg)
                print(f"{attacker.name} claws at you on the {side}! You take {dmg}.")
            else:
                # Not present: partial breach damage to you anyway (they slip in)
                spill = max(1, dmg - 1)
                gs.player.hp = max(0, gs.player.hp - spill)
                print(f"{attacker.name} slips through {side} and wounds you inside! (-{spill})")

def run_night(gs: GameState):
    """
    Night lasts a fixed number of turns with light scaling by day.
    """
    turns = int((10 * 2))  # 10 in-game hours * 2 turns/hour = 20 turns
    enemy_queues: Dict[str, List[Enemy]] = {s: [] for s in SIDES}
    gs.player.side = "North"  # start on one side
    turns_done = 0

    if gs.day_num == 1:
        print("A faint howl echoes once, then silence... the forest tests you.")
    elif gs.day_num >= 4:
        print("The air is thick with growls. They come in greater numbers tonight.")

    for t in range(1, turns + 1):
        # inside run_night()
        hour = 20 + (turns_done * 0.5)
        if hour >= 24: hour -= 24
        print(f"⏰ Time: {int(hour):02d}:{'30' if hour % 1 else '00'}")

        if hour == 22:
            print("You hear faint scratching beyond the fence...")
        elif hour == 1:
            print("The fire crackles softly, embers dancing against the dark.")
        elif hour == 4:
            print("A chill wind whispers through the gaps in the fence.")
        # Spawn
        # Determine cap and spawn pattern
        current_alive = sum(len(q) for q in enemy_queues.values())
        max_alive = [3, 4, 6, 8, 10][min(gs.day_num - 1, 4)]

        new_batch = []
        for side, count in _spawn_pattern(gs.day_num, current_alive, max_alive):
            for _ in range(count):
                e = scaled_enemy(gs.day_num, side)
                enemy_queues[side].append(e)
                new_batch.append(e)

        # ---- Trap trigger check ----
        if new_batch and gs.traps > 0:
            kills = random.randint(1, 3)
            victims = random.sample(new_batch, min(kills, len(new_batch)))
            for e in victims:
                enemy_queues[e.side].remove(e)
            gs.traps -= 1
            print(f"Your traps snap in the dark! {len(victims)} creatures from the new wave are slain.")

        _print_board(gs, enemy_queues)

        # Player action (must consume a turn)
        acted = False
        while not acted:
            acted = _resolve_player_action(gs, enemy_queues)

        if gs.player.hp <= 0:
            gs.alive = False
            break

        # Enemies act
        _enemies_attack_and_move(gs, enemy_queues)

        if gs.player.hp <= 0:
            gs.alive = False
            break

        # Clean up dead (if any somehow <0)
        for s in SIDES:
            enemy_queues[s] = [e for e in enemy_queues[s] if e.alive()]
        turns_done+=1

    if gs.alive:
        print("\nA gray thread of light at the treetops. Dawn.")
        # small morning heal
        if gs.player.hp < gs.player.max_hp:
            healed = 2
            gs.player.hp = min(gs.player.max_hp, gs.player.hp + healed)
            print(f"You bind cuts and drink hot water. HP +{healed}.")