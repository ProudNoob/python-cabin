# night.py
from __future__ import annotations
import random
from typing import Dict, List, Tuple
from entities import GameState, Enemy, SIDES, scaled_enemy

DIV = "\n" + "=" * 56 + "\n"

def _spawn_pattern(day: int, current_enemies: int, max_alive: int) -> List[Tuple[str, int]]:
    if current_enemies >= max_alive:
        return []
    day_clamped = min(day, 10)
    spawn_chance = min(0.35 + day_clamped * 0.05, 0.85)
    per_spawn = 1 if day < 3 else 2 if day < 6 else 3
    if random.random() > spawn_chance:
        return []

    groups = 1 if day < 3 else 2 if day < 7 else 3
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

def _print_board(gs: GameState, enemy_queues: Dict[str, List[Enemy]], turn: int):
    hour = 20 + turn * 0.5
    if hour >= 24:
        hour -= 24
    clock = f"{int(hour):02d}:{'30' if hour % 1 else '00'}"

    print(DIV)
    mode = "🏰 In Tower" if gs.in_tower else "🛡️ On Ground"
    print(f" NIGHT — Day {gs.day_num} | Time {clock} | Mode: {mode}")
    print(f" You are defending: [{gs.player.side}]   HP {gs.player.hp}/{gs.player.max_hp}")
    print(" Fences:")
    for s in SIDES:
        f = gs.fence(s)
        fence_bar = f"{f.hp:02d}/{f.max_hp}"
        q = enemy_queues[s]
        q_str = ", ".join(f"{e.name}({e.hp})" if gs.campfire_on else "? (?)" for e in q) if q else "—"
        print(f"  {s:<5} | Fence {fence_bar} | Enemies: {q_str}")
    print(DIV)

def _player_menu(gs) -> str:
    print("Choose your action:")
    print(" 1) Move North")
    print(" 2) Move East")
    print(" 3) Move South")
    print(" 4) Move West")
    print(" 5) Attack")
    print(" 6) Defend")
    print(" 7) Wait")
    if gs.has_watchtower:
        if not gs.in_tower:
            print(" 8) Climb tower (costs 1 turn)")
        else:
            print(" 8) Climb down (costs 1 turn)")
    return input("> ").strip()

def _resolve_player_action(gs: GameState, enemy_queues: Dict[str, List[Enemy]]) -> bool:
    gs.player.defending = False
    choice = _player_menu(gs)
    if choice in ("1", "2", "3", "4"):
        target = {"1": "North", "2": "East", "3": "South", "4": "West"}[choice]
        if gs.player.side == target:
            print(f"You're already at the {target} side — no need to move.")
            return False
        gs.player.side = target
        print(f"You dash to the {target} side.")
        return True

    if choice == "5":
        # --- RANGED ATTACK OPTION ---
        if gs.has_bow and gs.arrows > 0:
            # Determine possible sides based on watchtower
            if gs.has_watchtower and gs.in_tower:
                target_side = input("Shoot which side? (N/E/S/W): ").strip().lower()
                side_map = {"n": "North", "e": "East", "s": "South", "w": "West"}
                side = side_map.get(target_side, gs.player.side)
            else:
                # Can shoot current or adjacent sides
                if gs.player.side in ["North", "South"]:
                    valid_sides = ["North", "South", "East", "West"]
                    valid_sides.remove("South" if gs.player.side == "North" else "North")
                else:
                    valid_sides = ["North", "South", "East", "West"]
                    valid_sides.remove("West" if gs.player.side == "East" else "East")
                print("Choose a side to shoot:")
                for i, s in enumerate(valid_sides, 1):
                    print(f" {i}) {s}")
                pick = input("> ").strip()
                try:
                    side = valid_sides[int(pick) - 1]
                except (ValueError, IndexError):
                    print("Invalid choice. Shooting current side.")
                    side = gs.player.side

            q = enemy_queues[side]
            if not q:
                print(f"No enemy present on {side}. Arrow wasted.")
                gs.arrows -= 1
                return True

            target = min(q, key=lambda e: e.hp)
            dmg = gs.player.damage + random.randint(0, 2)
            target.hp = max(0, target.hp - dmg)
            gs.arrows -= 1
            print(f"🏹 Arrow hits {target.name} on {side} for {dmg} damage! ({gs.arrows} left)")
            if target.hp <= 0:
                print(f"The {target.name} collapses.")
                q.remove(target)
            return True

        # --- MELEE FALLBACK ---
        side = gs.player.side
        q = enemy_queues[side]
        if not q:
            print(f"No enemy in reach on the {side} side.")
            return True
        target = min(q, key=lambda e: e.hp)
        dmg = gs.player.damage + random.randint(0, 2)
        target.hp = max(0, target.hp - dmg)
        print(f"You strike the {target.name} for {dmg} damage!")
        if target.hp <= 0:
            print(f"The {target.name} collapses.")
            q.remove(target)
        return True

    if choice == "6":
        if gs.has_watchtower and gs.in_tower:
            print("You cannot defend while in the watchtower — you’re too far from the fences!")
            return False
        gs.player.defending = True
        print(f"You brace against the {gs.player.side} fence.")
        return True

    if choice == "7":
        print("You steady your breath...")
        return True

    if choice == "8" and gs.has_watchtower:
        if not gs.in_tower:
            gs.in_tower = True
            print("You climb the tower, gaining full sight of the battlefield.")
        else:
            gs.in_tower = False
            print("You climb down to the ground, ready to defend the fences again.")
        return True  # consumes a turn

    print("Invalid choice.")
    return False

def _enemies_attack(gs: GameState, enemy_queues: Dict[str, List[Enemy]]):
    for side in SIDES:
        q = enemy_queues[side]
        if not q:
            continue
        attacker = random.choice(q)
        fence = gs.fence(side)
        if fence.is_up():
            dmg = attacker.dmg
            if gs.defense_bonus > 0:
                dmg = int(dmg * (1 - gs.defense_bonus))
            fence.hp = max(0, fence.hp - dmg)
            print(f"{attacker.name} batters the {side} fence (-{dmg}).")
        else:
            dmg = attacker.dmg
            if gs.player.side == side and gs.player.defending:
                dmg = max(0, dmg - 2)
            if gs.has_watchtower and gs.in_tower:
                dmg += 1  # extra damage if exposed in tower
            gs.player.hp = max(0, gs.player.hp - dmg)
            print(f"{attacker.name} breaches {side}! You take {dmg} damage.")

def run_night(gs: GameState):
    turns = 20  # 10 hours * 2 turns/hour
    enemy_queues: Dict[str, List[Enemy]] = {s: [] for s in SIDES}
    gs.player.side = "North"

    print("\nNight falls. The treeline rustles with unseen steps...")
    # Decide whether to climb the tower (if built)
    if gs.has_watchtower:
        ans = input("Do you want to start the night in the watchtower? (y/N): ").strip().lower()
        gs.in_tower = (ans == "y")
        if gs.in_tower:
            print("You climb the tower, bow ready. You’ll shoot from above but can’t defend.")
        else:
            print("You remain on the ground, near the fences.")
    else:
        gs.in_tower = False

    for t in range(1, turns + 1):
        current_alive = sum(len(q) for q in enemy_queues.values())
        max_alive = int(3 + gs.day_num * 1.2)

        new_batch = []
        for side, count in _spawn_pattern(gs.day_num, current_alive, max_alive):
            for _ in range(count):
                e = scaled_enemy(gs.day_num, side)
                enemy_queues[side].append(e)
                new_batch.append(e)

        # trap trigger per batch
        if new_batch and gs.traps > 0:
            kills = random.randint(2, 4)
            victims = random.sample(new_batch, min(kills, len(new_batch)))
            for e in victims:
                enemy_queues[e.side].remove(e)
            gs.traps -= 1
            print(f"Your traps snap! {len(victims)} creatures from the new wave are slain.")

        _print_board(gs, enemy_queues, t)

        acted = False
        while not acted:
            acted = _resolve_player_action(gs, enemy_queues)
        if gs.player.hp <= 0:
            gs.alive = False
            break

        _enemies_attack(gs, enemy_queues)
        if gs.player.hp <= 0:
            gs.alive = False
            break

        for s in SIDES:
            enemy_queues[s] = [e for e in enemy_queues[s] if e.alive()]

    if gs.alive:
        print("\nA gray thread of light touches the treetops. Dawn.")
        healed = 2
        gs.player.hp = min(gs.player.max_hp, gs.player.hp + healed)
        print(f"You patch wounds and breathe deep. HP +{healed}.")