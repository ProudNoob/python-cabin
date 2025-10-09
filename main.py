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
        "crafted": list(getattr(gs, "crafted", [])),
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
    recipes = [
        ("Spear", 5, "Increase night attack damage by +2."),
        ("Axe", 6, "Gather +2 extra wood each time."),
        ("Hoe", 4, "Unlock 'Tend Field' action to grow food."),
        ("Bow", 8, "Craft a bow to shoot adjacent sides with arrows."),
        ("Arrow Batch", 2, "Craft 5 arrows for ranged attacks."),
        ("Watchtower", 25, "Build a tower to shoot from any side, but you cannot defend directly."),
        (f"Reinforced Fences ({reinforce_cost} wood)", reinforce_cost, "Boost all fence max HP by +10, cost rises each time."),
        ("Trap", 5, "Consumes 5 wood. Kills 1–3 monsters from each new wave."),
    ]
    owned = getattr(gs, "crafted", set())
    if not hasattr(gs, "crafted"):
        gs.crafted = set()

    print("\nAvailable Crafting Recipes:")
    for i, (name, cost, desc) in enumerate(recipes, 1):
        mark = "✅" if name in gs.crafted else " "
        print(f" {i}) {name:<18} ({cost} wood) {mark}\n     {desc}")

    choice = input("> Choose item number or Enter to cancel: ").strip()
    if not choice.isdigit():
        print("Cancelled.")
        return
    idx = int(choice) - 1
    if not (0 <= idx < len(recipes)):
        print("Invalid choice.")
        return
    name, cost, desc = recipes[idx]

    if name in gs.crafted:
        print("You already crafted this.")
        return
    if gs.player.wood < cost:
        print("Not enough wood.")
        return

    gs.player.wood -= cost
    gs.crafted.add(name)

    # Apply effects
    if name == "Spear":
        gs.player.damage = int(gs.player.damage * 1.3)

    elif name == "Axe":
        gs.player.gather_bonus = 5

    elif name == "Hoe":
        gs.has_field = True
        gs.field_state = "empty"
        gs.field_timer = 0

    elif name.startswith("Reinforced Fences"):
        bonus = 10
        for f in gs.fences.values():
            f.max_hp += bonus
            f.hp += bonus
        print(f"All fences reinforced. Max HP +{bonus} each.")
        gs.defense_bonus = getattr(gs, "defense_bonus", 0) + 0.05
        gs.reinforce_cost = getattr(gs, "reinforce_cost", 10) + 5 # Increase future cost

    elif name == "Trap":
        max_possible = gs.player.wood // 5
        if max_possible <= 0:
            print("Not enough wood to make even one trap.")
            return
        try:
            n = int(input(f"Craft how many traps? (1–{max_possible}): ").strip())
        except ValueError:
            print("Cancelled.")
            return
        if not (1 <= n <= max_possible):
            print("Cancelled.")
            return
        gs.player.wood -= n * 5
        gs.traps += n
        print(f"You craft {n} trap{'s' if n > 1 else ''}. They will trigger against new waves at night.")
        gs.crafted.remove(name)

    elif name == "Bow":
        if gs.has_bow:
            print("You already have a bow.")
            return
        gs.has_bow = True
        print("You craft a sturdy bow. Now you can shoot enemies from afar.")

    elif name == "Arrow Batch":
        max_possible = gs.player.wood // 2
        if max_possible <= 0:
            print("Not enough wood to make even one batch.")
            return
        try:
            n = int(input(f"Craft how many batches? (1–{max_possible}): ").strip())
        except ValueError:
            print("Cancelled.")
            return
        if not (1 <= n <= max_possible):
            print("Cancelled.")
            return
        gs.player.wood -= n * 2
        gs.arrows += n
        print(f"You craft {n} arrow{'s' if n > 1 else ''}. They feel deadly and sharp.")
        gs.crafted.add(name)

    elif name == "Watchtower":
        if gs.has_watchtower:
            print("You already have a watchtower.")
            return
        gs.has_watchtower = True
        print("You build a watchtower above the cabin. You can now shoot from any side.")
    # print(f"You craft a {name}. {desc}")

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
    # Passive experience scaling per survived day
    scale_factor = 1.05  # +5% overall growth per day survived
    old_dmg = gs.player.damage
    old_hp = gs.player.max_hp
    gs.player.max_hp = int(gs.player.max_hp * scale_factor)
    gs.player.damage = int(gs.player.damage * scale_factor)
    # heal to full each morning if wounded (optional, comment out if too easy)
    gs.player.hp = gs.player.max_hp
    print(f"You feel hardier and more seasoned. Damage {old_dmg}→{gs.player.damage}, Max HP {old_hp}→{gs.player.max_hp}.")
    gs.daily_wood_bonus_combo = 0

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