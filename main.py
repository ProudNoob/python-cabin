# main.py
from __future__ import annotations
import random
from entities import GameState, SIDES
import night

DIV = "\n" + "=" * 56 + "\n"
import json, os

SAVE_FILE = "save.json"

def save_game(gs: GameState):
    data = {
        "day_num": gs.day_num,
        "player": {
            "hp": gs.player.hp,
            "max_hp": gs.player.max_hp,
            "wood": gs.player.wood,
            "food": gs.player.food,
            "seeds": gs.player.seeds,
            "damage": gs.player.damage,
            "gather_bonus": getattr(gs.player, "gather_bonus", 0),
        },
        "fences": {s: {"hp": f.hp, "max_hp": f.max_hp} for s, f in gs.fences.items()},
        "upgrades": list(getattr(gs, "upgrades", [])),
        "reinforce_cost": getattr(gs, "reinforce_cost", 10),
        "has_field": getattr(gs, "has_field", False),
        "field_state": getattr(gs, "field_state", "empty"),
        "field_timer": getattr(gs, "field_timer", 0),
        "field_watered": getattr(gs, "field_watered", 0),
        "campfire_on": getattr(gs, "campfire_on", True),
        "traps": getattr(gs, "traps", 0),
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print("(Game saved.)")


def load_game() -> GameState:
    """Always return a valid GameState. Fall back to a fresh game on error."""
    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("(Save missing/corrupted. Starting a new game.)")
        return GameState()

    gs = GameState()
    gs.day_num = data["day_num"]
    p = data["player"]
    gs.player.hp = p["hp"]
    gs.player.max_hp = p["max_hp"]
    gs.player.wood = p["wood"]
    gs.player.food = p["food"]
    gs.player.seeds = p["seeds"]
    gs.player.damage = p["damage"]
    gs.player.gather_bonus = p.get("gather_bonus", 0)

    for s, fdata in data["fences"].items():
        f = gs.fences[s]
        f.hp = fdata["hp"]
        f.max_hp = fdata["max_hp"]

    gs.crafted = set(data.get("crafted", []))
    gs.reinforce_cost = data.get("reinforce_cost", 10)
    gs.has_field = data.get("has_field", False)
    gs.field_state = data.get("field_state", "empty")
    gs.field_timer = data.get("field_timer", 0)
    gs.field_watered = data.get("field_watered", 0)
    gs.campfire_on = data.get("campfire_on", True)
    gs.traps = data.get("traps", 0)
    print("(Game loaded.)")
    return gs

def intro(gs: GameState):
    print(DIV)
    print("You stumble out of the pines into a small clearing.")
    print("A wooden cabin crouches in the mist, its four fences scarred but standing.")
    input("\n[Enter] Step toward the cabin...")

def show_day_status(gs: GameState, actions_left: int):
    total = gs.player.day_actions_per_day
    hour = 6 + (total - actions_left)
    print(DIV)
    print(f"DAY {gs.day_num} — {hour:02d}:00 | Actions left: {actions_left}")
    print(f"HP {gs.player.hp}/{gs.player.max_hp} | Wood {gs.player.wood} | Food {gs.player.food} | Seeds {gs.player.seeds} | Arrows {gs.arrows} | Traps {gs.traps}")
    for s in SIDES:
        f = gs.fence(s)
        print(f"  {s:<5} Fence: {f.hp:02d}/{f.max_hp}")
    print(DIV)

def day_menu(gs):
    print("Choose your action:")
    print(" 1) Gather wood")
    print(" 2) Forage")
    print(" 3) Repair all fences")
    print(" 4) Rest")
    print(" 5) Craft items")
    if getattr(gs, "has_field", False):
        print(" 6) Tend the field")
    print(" 7) End day")
    return input("> ").strip()


def do_craft(gs: GameState):
    reinforce_cost = getattr(gs, "reinforce_cost", 10)

    # ---- Permanent Upgrades ----
    # (name, cost, desc, prereq)
    upgrades = [
        ("Spear", 5, "Increase night attack damage by +2.", None),
        ("Axe", 6, "Gather +2 extra wood each time.", None),
        ("Hoe", 4, "Unlock 'Tend Field' to grow food.", None),
        ("Bow", 8, "Allows ranged attacks using arrows.", "Spear"),  # must have spear
        ("Watchtower", 25, "Shoot from any side but cannot defend.", "Bow"),  # must have bow
    ]

    # ---- Consumables / Repeatables ----
    craftables = [
        (f"Reinforce Fences ({reinforce_cost} wood)", reinforce_cost, "Increase all fence max HP by +10, cost rises each time."),
        ("Trap", 5, "Place a trap that kills 2–4 monsters when a new wave spawns."),
        ("Arrow Batch", 2, "Craft 5 arrows for ranged attacks."),
    ]

    # ---- Display ----
    print("\n== Permanent Upgrades ==")
    for i, (name, cost, desc, prereq) in enumerate(upgrades, 1):
        mark = "✅" if name in gs.upgrades else " "
        prereq_text = f"(requires {prereq})" if prereq else ""
        print(f" U{i}) {name:<18} ({cost} wood) {mark} {prereq_text}\n     {desc}")

    print("\n== Craftable Items ==")
    for i, (name, cost, desc) in enumerate(craftables, 1):
        print(f" C{i}) {name:<18} ({cost} wood)\n     {desc}")

    choice = input("> Choose item (e.g. U1, C2) or Enter to cancel: ").strip().lower()
    if not choice:
        print("Cancelled.")
        return

    # ---- Handle Upgrades ----
    if choice.startswith("u"):
        idx = int(choice[1:]) - 1
        if not (0 <= idx < len(upgrades)):
            print("Invalid choice.")
            return
        name, cost, desc, prereq = upgrades[idx]

        # prerequisite check
        if prereq and prereq not in gs.upgrades:
            print(f"You need {prereq} before crafting {name}.")
            return

        if name in gs.upgrades:
            print("You already have this upgrade.")
            return
        if gs.player.wood < cost:
            print("Not enough wood.")
            return

        gs.player.wood -= cost
        gs.upgrades.add(name)

        # Apply upgrade effects
        if name == "Spear":
            gs.player.damage += 2
        elif name == "Axe":
            gs.player.gather_bonus = 2
        elif name == "Hoe":
            gs.has_field = True
            gs.field_state = "empty"
            gs.field_timer = 0
        elif name == "Bow":
            gs.has_bow = True
        elif name == "Watchtower":
            gs.has_watchtower = True

        print(f"You craft {name}. {desc}")
        return

    # ---- Handle Craftables ----
    if choice.startswith("c"):
        idx = int(choice[1:]) - 1
        if not (0 <= idx < len(craftables)):
            print("Invalid choice.")
            return
        name, cost, desc = craftables[idx]
        if gs.player.wood < cost:
            print("Not enough wood.")
            return

        gs.player.wood -= cost

        if "Reinforce" in name:
            for f in gs.fences.values():
                f.max_hp += 10
                f.hp += 10
            gs.reinforce_cost += 5  # escalate cost
            print("Your fences grow sturdier, with thicker planks and braces.")
        elif name == "Trap":
            gs.traps += 1
            print("You build a trap and hide it near the fence line.")
        elif name == "Arrow Batch":
            gs.arrows += 5
            print("You craft 5 new arrows and bundle them neatly.")

        return

    print("Invalid input.")

def do_gather(gs: GameState):
    base = random.randint(2, 4)
    bonus = getattr(gs.player, "gather_bonus", 0) + gs.daily_wood_bonus_combo
    gs.daily_wood_bonus_combo += 2
    gained = base + bonus
    gs.player.wood += gained
    print(f"You gather wood at the treeline. +{gained} wood. (+{gs.daily_wood_bonus_combo} combo)")

def do_forage(gs: GameState):
    r = random.random()
    if r < 0.35:
        amt = random.randint(1, 2)
        gs.player.food += amt
        print(f"You find edible shoots and berries. Food +{amt}.")
    elif r < 0.6:
        gs.player.seeds += 1
        print("You find hardy seeds in a wilted husk. Seeds +1.")
    elif r < 0.8:
        amt = random.randint(1, 2)
        gs.player.wood += amt
        print(f"You drag back a limb. Wood +{amt}.")
    else:
        print("You trudge and circle back with nothing to show.")

def do_repair(gs: GameState):
    if gs.player.wood <= 0:
        print("You have no wood to repair with.")
        return

    total_need = sum(f.max_hp - f.hp for f in gs.fences.values())
    if total_need <= 0:
        print("All fences look sturdy already.")
        return

    # 1 wood = 2 HP repair
    max_possible_repair = gs.player.wood * 2
    actual_repair = min(total_need, max_possible_repair)

    # Distribute repair evenly among all damaged fences
    remaining = actual_repair
    repaired_total = 0
    for f in gs.fences.values():
        if f.hp < f.max_hp and remaining > 0:
            needed = f.max_hp - f.hp
            amount = min(needed, remaining)
            f.hp += amount
            repaired_total += amount
            remaining -= amount

    # Deduct wood spent (1 wood = 2 HP)
    wood_used = (repaired_total + 1) // 2  # round up partial use
    gs.player.wood -= wood_used

    print(f"You spend {wood_used} wood to patch the fences.")
    print(f"Total repair: +{repaired_total} HP across all sides.")

def do_rest(gs: GameState):
    healed = gs.player.rest()
    print(f"You rest by the hearth. HP +{healed}.")

def do_tend_field(gs: GameState):
    state = getattr(gs, "field_state", "empty")
    if state == "empty":
        if gs.player.seeds > 0:
            gs.player.seeds -= 1
            gs.field_state = "planted"
            gs.field_timer = 3
            gs.field_watered = 0
            print("You plant a seed in the soil.")
        else:
            print("You have no seeds.")
    elif state == "planted":
        gs.field_watered += 1
        gs.field_timer -= 1
        print(f"You water the young crop (Day {3 - gs.field_timer}/3).")
        if gs.field_timer <= 0:
            gs.field_state = "ready"
            print("Your crops are ready to harvest tomorrow!")
    elif state == "ready":
        bonus = min(gs.field_watered, 3)
        gained = random.randint(2, 4 + bonus)
        gs.player.food += gained
        gs.field_state = "empty"
        print(f"You harvest {gained} food from your field. The soil rests.")

def run_day(gs: GameState):
    actions = gs.player.day_actions_per_day
    hour = 6 + (14 - actions)
    print(f"Current time: {hour:02d}:00")
    while actions > 0:
        show_day_status(gs, actions)
        choice = day_menu(gs)
        consumed = True

        if choice == "1":
            do_gather(gs)
        elif choice == "2":
            do_forage(gs)
        elif choice == "3":
            do_repair(gs)
        elif choice == "4":
            do_rest(gs)
        elif choice == "5":
            do_craft(gs)
        elif choice == "6" and getattr(gs, "has_field", False):
            do_tend_field(gs)
        elif choice == "7":
            print("You decide to stop early and wait for dusk.")
            break
        else:
            print("Pick a number from the list.")
            consumed = False

        if consumed:
            actions -= 1
            input("\n[Enter] Continue...")

    print("\nDusk bleeds into night. The treeline begins to whisper...")

def morning_upkeep(gs: GameState):
    # Small chance of weather decay
    if random.random() < 0.25:
        decay = random.randint(1, 2)
        for s in SIDES:
            f = gs.fence(s)
            if f.hp > 0:
                f.hp = max(0, f.hp - decay)
        print(f"\nFrost gnaws at the boards overnight. All standing fences -{decay} HP.")
    # Consume 1 wood daily for the fire
    if gs.player.wood > 0:
        gs.player.wood -= 1
        gs.campfire_on = True
        print("You feed the campfire with 1 wood. Its warmth keeps the night at bay.")
    else:
        gs.campfire_on = False
        print("You have no wood for the campfire. The clearing will be dark tonight...")
    # Feast
    if gs.player.food > 0:
        gs.player.food -= 1
        print("You eat your morning meal. (-1 food)")
    else:
        dmg = 2
        gs.player.hp = max(0, gs.player.hp - dmg)
        print("You have nothing to eat. You feel weaker. (-2 HP)")
    gs.daily_wood_bonus_combo = 0
    gs.player.update_stats(gs.day_num)

def main():
    random.seed()
    if os.path.exists(SAVE_FILE):
        ans = input("Save file found. Continue? (Y/n): ").strip().lower()
        if ans != "n":
            gs: GameState = load_game()
        else:
            gs: GameState = GameState()
            intro(gs)
    else:
        gs: GameState = GameState()
        intro(gs)

    while gs.alive:
        run_day(gs)
        if not gs.alive:
            break

        night.run_night(gs)
        if not gs.alive:
            break

        gs.day_num += 1
        morning_upkeep(gs)
        # autosave at dawn
        save_game(gs)
        input("\n[Enter] A new day breaks...")

    # delete save on death / game over
    if os.path.exists(SAVE_FILE):
        try:
            os.remove(SAVE_FILE)
            print("(Save deleted.)")
        except OSError:
            pass

    print(DIV)
    print("You collapse against the cold earth. The forest exhales.")
    print(f"You survived until Day {gs.day_num}.")
    print("Thanks for playing this prototype.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nYou bar the cabin door and rest, for now.")