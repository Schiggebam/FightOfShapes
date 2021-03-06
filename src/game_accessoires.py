from __future__ import annotations
from typing import List, Tuple, Dict, Any

import arcade
from arcade import AnimationKeyframe

from src.hex_map import Hexagon
from src.misc.game_constants import ResourceType, error, GroundType, PlayerColour, UnitType, UnitCost


class Drawable:
    def __init__(self):
        self.sprite: arcade.Sprite = arcade.Sprite()
        self.tex_counter = -1  # this variable is supposed to count the number of textures
        self.__active_tex = -1
        self.tex_code = ""
        self.offset = (0, 0)
        self.update_interval = 0.2
        self.__time = .0

    def set_sprite_pos(self, pos_pixel: (int, int), camera_pos):
        self.sprite.center_x = pos_pixel[0] + self.offset[0] + camera_pos[0]
        self.sprite.center_y = pos_pixel[1] + self.offset[1] + camera_pos[1]

    def add_texture(self, tex: arcade.Texture):
        if self.__active_tex == -1:
            self.__active_tex = 0
        self.sprite.append_texture(tex)
        self.tex_counter = self.tex_counter + 1
        self.sprite.set_texture(self.__active_tex)  # preserve the idx

    def set_tex_offset(self, offset: (int, int)):
        self.offset = offset
        self.sprite.center_x = self.sprite.center_x + offset[0]
        self.sprite.center_y = self.sprite.center_y + offset[1]

    def set_tex_scale(self, scale: float):
        self.sprite.scale = scale

    def set_active_texture(self, idx: int):
        if self.tex_counter >= idx:
            self.sprite.set_texture(idx)
            self.__active_tex = idx
        else:
            error("Drawable: No texture at index: " + str(idx))

    def next_frame(self, d_t):
        self.__time = self.__time + d_t
        if self.__time >= self.update_interval:
            self.__active_tex = (self.__active_tex + 1) % (self.tex_counter + 1)
            self.sprite.set_texture(self.__active_tex)
            self.__time = .0


class Ground(Drawable):

    def __init__(self, str_code: str):
        super().__init__()
        self.walkable: bool = False
        self.buildable: bool = False
        self.ground_type: GroundType = GroundType.get_type_from_strcode(str_code)


class Resource(Drawable):

    resource_info: Dict[ResourceType, Dict[str, Any]] = {}  # a dict containing all information about the resources

    def __init__(self, tile: Hexagon, res_type: ResourceType):
        super().__init__()
        self.tile: Hexagon = tile
        self.remaining_amount: int = int(0)
        self.resource_type: ResourceType = res_type
        self.remaining_amount = Resource.resource_info[res_type]['amount']

    def demand_res(self, request):
        if request <= self.remaining_amount:
            self.remaining_amount = self.remaining_amount - request
            return request
        else:
            remaining = self.remaining_amount
            self.remaining_amount = 0
            return remaining


class Unit:
    unit_info: Dict[UnitType, Dict[str, Any]] = {}

    def __init__(self, u_type: UnitType):
        self.unit_type: UnitType = u_type
        self.name = Unit.unit_info[u_type]['name']
        self.attack_value = Unit.unit_info[u_type]['attack']
        self.defence_value = Unit.unit_info[u_type]['defence']
        self.population = Unit.unit_info[u_type]['population']
        self.cost_resource = Unit.unit_info[u_type]['cost_resource']
        self.cost_culture = Unit.unit_info[u_type]['cost_culture']

    @staticmethod
    def get_unit_cost(ut: UnitType) -> UnitCost:
        """returns a UnitCost of the cost in resources, culture and population"""
        return UnitCost(Unit.unit_info[ut]['cost_resource'],
                        Unit.unit_info[ut]['cost_culture'],
                        Unit.unit_info[ut]['population'])

    @staticmethod
    def get_unit_stats(ut: UnitType) -> (int, int, int):
        """returns a tuple of the attack and defence value and population of the unit"""
        return Unit.unit_info[ut]['attack'], Unit.unit_info[ut]['defence'], Unit.unit_info[ut]['population']


class Army(Drawable):
    def __init__(self, tile: Hexagon, owner_id):
        super().__init__()
        self.tile: Hexagon = tile
        self.owner_id: int = owner_id
        self.is_barbaric: bool = False
        self.__units: List[Unit] = []

    def add_unit(self, unit: Unit):
        self.__units.append(unit)

    def get_units(self) -> List[Unit]:
        # returns only a copy (not sure if that makes sense since this lacks consistancy to the rest of the code)
        return list(self.__units)

    def remove_units_of_type(self, amount: int, ut: UnitType):
        tbr = []
        count = 0
        for u in self.__units:
            if count >= amount:
                break
            if u.unit_type == ut:
                tbr.append(u)
                count = count + 1
        for r in tbr:
            self.__units.remove(r)
        if count != amount:
            error(
                "Army: unexpected amount of removed units. requested to remove: {}, removed: {}".format(amount, count))

    def remove_all_units(self):
        self.__units.clear()

    def get_attack_strength(self) -> int:
        value = 0
        for u in self.__units:
            value = value + u.attack_value
        return value

    def get_defence_strength(self) -> int:
        value = 0
        for u in self.__units:
            value = value + u.defence_value
        return value

    def get_population(self) -> int:
        value = 0
        for u in self.__units:
            value = value + u.population
        return value

    def get_amount_by_unit(self, ut: UnitType):
        value = 0
        for u in self.__units:
            if u.unit_type == ut:
                value = value + 1
        return value

    def get_population_by_unit(self, ut: UnitType):
        value = 0
        for u in self.__units:
            if u.unit_type == ut:
                value = value + u.population
        return value

    def get_units_as_tuple(self) -> Tuple[int, int, int]:
        return (self.get_amount_by_unit(UnitType.MERCENARY),
                self.get_amount_by_unit(UnitType.KNIGHT),
                self.get_amount_by_unit(UnitType.BABARIC_SOLDIER))


class Flag(arcade.AnimatedTimeBasedSprite):
    def __init__(self, pos: Tuple[int, int], animated_tex: List[arcade.Texture], scale=1):
        super().__init__(scale=scale, center_x=pos[0], center_y=pos[1])
        i = 0
        for tex in animated_tex:
            self.append_texture(tex)
            self.frames.append(AnimationKeyframe(i, 80, tex))
            i += 1
        self.set_texture(0)


class Scenario:
    def __init__(self):
        self.resource_list: [Resource] = []
        self.aux_sprites: [(Hexagon, Drawable)] = []
