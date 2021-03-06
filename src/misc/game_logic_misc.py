import queue
# from dataclasses import dataclass
from math import ceil
from typing import Tuple

from src.game_accessoires import Army, Unit
from src.hex_map import Hexagon

from src.misc.building import Building
from src.misc.game_constants import BuildingType, BuildingState, LogType, DiploEventType, UnitType, error, \
    BattleAfterMath, PlayerType
from src.player import Player


class IncomeCalculator:
    def __init__(self, hex_map, scenario):
        self.scenario = scenario  # reference to scenario
        self.hex_map = hex_map  # reference to hex_map

    def calculate_income(self, player: Player) -> int:
        if player.is_barbaric:
            return 1  # linear growth for barbaric players
        income = int(0)
        for building in player.buildings:
            if building.building_state == BuildingState.UNDER_CONSTRUCTION:
                continue
            if building.building_state == BuildingState.DESTROYED:
                continue
            income = income + building.resource_per_turn
            for tile in self.hex_map.get_neighbours(building.tile):
                for res in self.scenario.resource_list:
                    if res.tile.offset_coordinates == tile.offset_coordinates:
                        income = income + res.demand_res(building.resource_per_field)

        return income

    def calculate_food(self, player: Player) -> int:
        food_inc = 0
        if player.player_type is PlayerType.BARBARIC or player.player_type is PlayerType.VILLAGER:
            return 0  # no food mechanics for npc players
        for building in player.buildings:
            if building.construction_time > 0 or building.building_state == BuildingState.UNDER_CONSTRUCTION or \
                 building.building_state == BuildingState.DESTROYED:
                continue
            if building.building_type == BuildingType.FARM:
                food_inc = food_inc + len(building.associated_tiles)
            else:
                food_inc = food_inc - building.food_consumption
        for a in player.armies:
            for u in a.get_units():
                food_inc = food_inc - u.population
        return food_inc

    def calculate_culture(self, player: Player) -> int:
        c = int(0)
        for building in player.buildings:
            if building.building_state == BuildingState.ACTIVE:
                c = c + building.culture_per_turn
        return c

    @staticmethod
    def building_food_influence(building: Building):
        if building.building_type == BuildingType.FARM:
            return len(building.associated_tiles)
        return building.food_consumption

    @staticmethod
    def building_population_influence(building: Building):
        return building.grant_pop

    @staticmethod
    def building_culture_influce(building: Building):
        return building.culture_per_turn


class InitialCondition:
    """
    this class will setup a player. In a future version, most of this should depend on XML input
    """
    @staticmethod
    def set_init_values(player: Player, base_hex: Hexagon, gl):
        if player.player_type is PlayerType.HUMAN or player.player_type is PlayerType.AI:
            player.food = 35
            player.amount_of_resources = 20
            unit = Unit(player.get_initial_unit_type())
            army = Army(gl.hex_map.get_hex_by_offset(player.init_army_loc), player.id)
            army.add_unit(unit)
            gl.add_army(army, player)
        elif player.player_type is PlayerType.VILLAGER:
            player.food = 30
            player.amount_of_resources = 5
        elif player.player_type is PlayerType.BARBARIC:
            player.amount_of_resources = 5
            player.food = 10
        player.discovered_tiles.add(base_hex)
        b_type = player.get_initial_building_type()
        b: Building = Building(base_hex, b_type, player.id)
        gl.add_building(b, player)
        b.construction_time = 0
        b.set_state_active()
        tmp = gl.hex_map.get_neighbours_dist(base_hex, b.sight_range)
        player.discovered_tiles.update(tmp)


class FightCalculator:

    @staticmethod
    def army_vs_army(attacker: Army, defender: Army) -> BattleAfterMath:
        attack_value = attacker.get_attack_strength()
        defencive_value = defender.get_defence_strength()
        if attack_value == 0:
            error("Attack value is 0 -> will adjust it to 0.5")
            attack_value = 0.5
        if defencive_value == 0:
            error("Defence value is 0 -> will adjust it to 0.5")
            defencive_value = 0.5

        attacker_won = attack_value >= defencive_value
        defender_won = defencive_value >= attack_value
        attacker_losses = defencive_value if attacker_won else attack_value
        defender_losses = attack_value if defender_won else defencive_value
        attacker_alive_pop_ratio = (attack_value - attacker_losses) / attack_value
        defender_alive_pop_ratio = (defencive_value - defender_losses) / defencive_value
        if attacker_won:
            attacker_alive_pop_ratio = attacker_alive_pop_ratio + (attacker_losses/3.0) / attack_value
        if defender_won:
            defender_alive_pop_ratio = defender_alive_pop_ratio + (defender_losses/3.0) / defencive_value
        attacker_pop = attacker.get_population()
        defender_pop = defender.get_population()
        attacker_surviving_pop_ratio = attacker_pop * attacker_alive_pop_ratio
        defender_surviving_pop_ratio = defender_pop * defender_alive_pop_ratio
        for unit in UnitType:
            attacker_unit_x = attacker.get_population_by_unit(unit)
            attacker_kill_count_unit_x = attacker_unit_x - ((attacker_unit_x / attacker_pop) *
                                                            attacker_surviving_pop_ratio)
            attacker.remove_units_of_type(ceil(attacker_kill_count_unit_x), unit)
            defender_unit_x = defender.get_population_by_unit(unit)
            defender_kill_count_unit_x = defender_unit_x - ((defender_unit_x / defender_pop) *
                                                            defender_surviving_pop_ratio)
            defender.remove_units_of_type(ceil(defender_kill_count_unit_x), unit)
        if attacker_won and defender_won:
            return BattleAfterMath.DRAW
        elif attacker_won:
            return BattleAfterMath.ATTACKER_WON
        else:
            return BattleAfterMath.DEFENDER_WON

    @staticmethod
    def army_vs_building(attacker: Army, defender: Building) -> BattleAfterMath:
        attack_value = attacker.get_attack_strength()
        defencive_value = defender.defensive_value
        attacker_won = attack_value >= defencive_value  # they can both win if their values are equal
        defender_won = defencive_value >= attack_value
        if attacker_won:
            attacker_losses = defencive_value if attacker_won else attack_value
            attacker_alive_ratio = (attack_value - attacker_losses) / attack_value
            attacker_alive_ratio = attacker_alive_ratio + (attacker_losses / 3.0) / attack_value
            attacker_pop = attacker.get_population()
            attacker_surviving_pop_ratio = attacker_pop * attacker_alive_ratio
            for unit in UnitType:
                attacker_unit_x = attacker.get_population_by_unit(unit)
                attacker_kill_count_unit_x = attacker_unit_x - ((attacker_unit_x / attacker_pop) *
                                                                attacker_surviving_pop_ratio)
                attacker.remove_units_of_type(ceil(attacker_kill_count_unit_x), unit)
            defender.defensive_value = -1       # building is destroyed

        if defender_won:
            attacker.remove_all_units()         # army is destroyed

        if attacker.get_population() == 0:
            defender_won = True

        if attacker_won and defender_won:
            return BattleAfterMath.DRAW
        elif attacker_won:
            return BattleAfterMath.ATTACKER_WON
        else:
            return BattleAfterMath.DEFENDER_WON




class Logger:
    class Log:
        def __init__(self, log_tpye):
            self.log_type = log_tpye

    class BattleLog(Log):
        def __init__(self, log_type: LogType, pre_att_u: Tuple[int, int, int], pre_def_u: Tuple[int, int, int],
                     post_att_u: Tuple[int, int, int], post_def_u: Tuple[int, int, int], outcome: BattleAfterMath,
                     att_name: str, def_name: str):
            super().__init__(log_type)
            self.pre_att_units: Tuple[int, int, int] = pre_att_u
            self.pre_def_units: Tuple[int, int, int] = pre_def_u
            self.post_att_units: Tuple[int, int, int] = post_att_u
            self.post_def_units: Tuple[int, int, int] = post_def_u
            self.outcome: BattleAfterMath = outcome
            self.att_name = att_name
            self.def_name = def_name

    class EventLog(Log):
        def __init__(self, log_type: LogType, event: DiploEventType, relative_change: float, loc: (int, int), lifetime: int, player_name: str):
            super().__init__(log_type)
            self.event_type = event
            self.relative_change = relative_change
            self.loc = loc
            self.lifetime = lifetime
            self.player_name = player_name

    class NotificationLog(Log):
        def __init__(self, log_type: LogType, text: str):
            super().__init__(log_type)
            self.text = text

    logs: queue.Queue = queue.Queue()

    @staticmethod
    def log_battle_army_vs_army_log(pre_att_u: Tuple[int, int, int], pre_def_u: Tuple[int, int, int],
                                    post_att_u: Tuple[int, int, int], post_def_u: Tuple[int, int, int],
                                    outcome: BattleAfterMath, att_name: str, def_name: str):

        log = Logger.BattleLog(LogType.BATTLE_ARMY_VS_ARMY, pre_att_u, pre_def_u,
                               post_att_u, post_def_u, outcome, att_name, def_name)
        Logger.logs.put(log)

    @staticmethod
    def log_battle_army_vs_building(pre_att_u: Tuple[int, int, int],  post_att_u: Tuple[int, int, int],
                                    pre_building_value, post_building_value,
                                    outcome: BattleAfterMath, att_name: str, def_name: str):
        log = Logger.BattleLog(LogType.BATTLE_ARMY_VS_BUILDING, pre_att_u, (pre_building_value, 0, 0),
                               post_att_u, (post_building_value, 0, 0), outcome, att_name, def_name)
        Logger.logs.put(log)

    @staticmethod
    def log_diplomatic_event(event: DiploEventType, relative_change: float, loc: (int, int), lifetime: int, player_name:str):
        if event == DiploEventType.TYPE_ENEMY_BUILDING_SCOUTED or \
                event == DiploEventType.TYPE_ENEMY_ARMY_INVADING:
            log = Logger.EventLog(LogType.DIPLO_ENEMY_BUILDING_SCOUTED,
                                  event, relative_change, loc, lifetime, player_name)
            Logger.logs.put(log)

    @staticmethod
    def log_notification(text: str):
        Logger.logs.put(Logger.NotificationLog(LogType.NOTIFICATION, text))
