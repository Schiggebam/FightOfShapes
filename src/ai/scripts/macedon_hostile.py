from typing import Any, Dict, Callable, Tuple, List

from src.ai import AI_Toolkit
from src.ai.AI_GameStatus import AI_GameStatus
from src.ai.AI_Macedon import AI_Mazedonian
from src.ai.AI_MapRepresentation import AI_Army
from src.misc.game_constants import hint, BuildingType


def on_setup(prop: Dict[str, Any]):
    """Idea: Move all adjustable variables in the script"""


    """At this distance or smaller from any own building a tile is considered claimed"""
    prop['claiming_distance'] = 2

    """Currently no meaning to it"""
    prop['safety_dist_to_enemy_army'] = 3


def setup_weights(self) -> List[Tuple[Callable, float]]:
    w: List[Tuple[Callable, float]] = []

    def w1(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: If AI looses food -> Make building a farm more important!"""
        if type(elem) is AI_Mazedonian.BuildOption:
            if elem.type == BuildingType.FARM:
                return self.is_loosing_food
        return False

    w.append((w1, 3))

    # def w2(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
    #     """Idea: If AI is in aggressive state -> build offensive units"""
    #     if type(elem) is AI_Mazedonian.RecruitmentOption:
    #         if self.state == AI_Mazedonian.AI_State.AGGRESSIVE:
    #             if elem.type == UnitType.MERCENARY:
    #                 return True
    #     return False
    #
    # w.append((w2, 3))

    def w3(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: If AI has no army -> Recruiting an army is important"""
        if type(elem) is AI_Mazedonian.RaiseArmyOption:
            if len(ai_stat.map.army_list) == 0:
                return True
        return False

    w.append((w3, 3))

    def w4(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea, once we have enough resources (and is in passive/def state),
         make scouting slightly more important"""
        if type(elem) is AI_Mazedonian.ScoutingOption:
            if ai_stat.player_resources > 10:
                if self.state == AI_Mazedonian.AI_State.PASSIVE or self.state == AI_Mazedonian.AI_State.DEFENSIVE:
                    return True
        return False

    w.append((w4, 1))

    def w5(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: reduce significance of scouting in a low eco game"""
        if type(elem) is AI_Mazedonian.ScoutingOption:
            if ai_stat.player_resources < 10:
                return True
        return False

    w.append((w5, -1))

    def w6(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: If AI has more than 70 food, cut down on additional farms"""
        if type(elem) is AI_Mazedonian.BuildOption:
            if elem.type == BuildingType.FARM:
                if ai_stat.player_food > 70:
                    return True
        return False

    w.append((w6, -1))

    def w7(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: slightly decrease scouting and waiting if a lot of resources are available"""
        if type(elem) is AI_Mazedonian.ScoutingOption or type(elem) is AI_Mazedonian.WaitOption:
            if ai_stat.player_resources > 70:
                return True
        return False

    w.append((w7, -1))

    def w8(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: slightly decrease scouting in early game"""
        if type(elem) is AI_Mazedonian.ScoutingOption:
            if self.protocol == AI_Mazedonian.Protocol.EARLY_GAME:
                return True
        return False

    w.append((w8, -1))

    def w9(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: slightly increase building in early game"""
        if type(elem) is AI_Mazedonian.BuildOption:
            if self.protocol == AI_Mazedonian.Protocol.EARLY_GAME:
                return True
        return False

    w.append((w9, 1))

    def w10(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: if AI lacks population by twice the desired value -> double down"""
        if type(elem) is AI_Mazedonian.RecruitmentOption:
            if self.build_order.population / 2 > ai_stat.population:
                return True
        return False

    w.append((w10, 0.9))

    def w11(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: if AI doesn't have a farm -> highest prio (if it cannot build one -> wait)"""
        if type(elem) is AI_Mazedonian.BuildOption:
            if elem.type == BuildingType.FARM:
                for b in ai_stat.map.building_list:
                    if b.type == BuildingType.FARM:
                        return False
                return True  # returns true if AI does not have a farm and building one is an option
        return False

    w.append((w11, 10))

    def w12(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: extension to w11 (if it cannot build one -> wait)"""
        if type(elem) is AI_Mazedonian.WaitOption:
            for b in ai_stat.map.building_list:
                if b.type == BuildingType.FARM:
                    return False
            return True  # returns true if AI does not have a farm
        return False

    w.append((w12, 5))

    def w13(elem: AI_Mazedonian.Option, ai_stat: AI_GameStatus) -> bool:
        """Idea: if pop >= pop_limit, make building barracks slightly more popular"""
        if ai_stat.population_limit <= ai_stat.population:
            if type(elem) is AI_Mazedonian.BuildOption:
                if elem.type == BuildingType.BARRACKS:
                    if not AI_Toolkit.has_building_under_construction(BuildingType.BARRACKS, ai_stat):
                        return True
            if type(elem) is AI_Mazedonian.WaitOption:
                if not AI_Toolkit.has_building_under_construction(BuildingType.BARRACKS, ai_stat):
                    return True
            return False

    w.append((w13, 2.7))

    hint(f"AI has found {len(w)} weight functions.")
    return w


def setup_movement_weights(self: AI_Mazedonian) -> List[Tuple[Callable, float]]:
    aw: List[Tuple[Callable, float]] = []

    def aw1(elem: AI_Mazedonian.AttackTarget, ai_stat: AI_GameStatus) -> bool:
        if type(elem.target) == AI_Army:
            if AI_Toolkit.is_obj_in_list(elem.target, self.claimed_tiles):
                return True
        return False

    aw.append((aw1, 2))

    def aw2(elem: AI_Mazedonian.AttackTarget, ai_stat: AI_GameStatus) -> bool:
        if type(elem.target) == AI_Army:
            if self.previous_amount_of_buildings > len(ai_stat.map.building_list):
                return True
        return False

    aw.append((aw2, 1))

    def aw3(elem: AI_Mazedonian.AttackTarget, ai_stat: AI_GameStatus) -> bool:
        """Idea: reduce aggressifness in opponant is equal or stronger"""
        if type(elem.target) == AI_Army:
            if elem.target.owner in self.hostile_player:
                if self.opponent_strength[elem.target.owner] == AI_Mazedonian.Strength.STRONGER or \
                        self.opponent_strength[elem.target.owner] == AI_Mazedonian.Strength.EQUAL:
                    return True
        return False

    aw.append((aw3, -1))

    def aw4(elem: AI_Mazedonian.AttackTarget, ai_stat: AI_GameStatus) -> bool:
        """Idea: Reduce will to attack in early game"""
        if type(elem.target) == AI_Army:
            if self.protocol == AI_Mazedonian.Protocol.EARLY_GAME:
                return True
        return False

    aw.append((aw4, -2))

    hint(f"AI has found {len(aw)} movement weight functions.")
    return aw