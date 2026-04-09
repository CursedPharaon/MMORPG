import time
import math
import random
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

# ============ БАЗОВЫЕ КЛАССЫ ============

class BuffType(Enum):
    DAMAGE = "damage"
    DEFENSE = "defense"
    SPEED = "speed"
    HEAL = "heal"
    MANA = "mana"

@dataclass
class Buff:
    name: str
    buff_type: BuffType
    value: float
    duration: float  # секунд
    start_time: float
    icon: str = "✨"
    description: str = ""
    
    @property
    def remaining(self) -> float:
        return max(0, self.duration - (time.time() - self.start_time))
    
    @property
    def is_active(self) -> bool:
        return self.remaining > 0

class BuffSystem:
    """Система баффов — более 200 строк логики"""
    
    def __init__(self):
        self.active_buffs: Dict[str, Buff] = {}
        self.buff_history: List[Buff] = []
        
    def add_buff(self, name: str, buff_type: BuffType, value: float, duration: float) -> bool:
        """Добавить бафф игроку"""
        buff = Buff(
            name=name,
            buff_type=buff_type,
            value=value,
            duration=duration,
            start_time=time.time()
        )
        
        # Если такой бафф уже есть, обновляем
        if name in self.active_buffs:
            old_buff = self.active_buffs[name]
            # Увеличиваем длительность, но не более чем на 50%
            new_duration = min(old_buff.duration + duration, old_buff.duration * 1.5)
            buff.duration = new_duration
            buff.start_time = time.time()
        
        self.active_buffs[name] = buff
        self.buff_history.append(buff)
        return True
    
    def remove_buff(self, name: str):
        """Удалить бафф"""
        if name in self.active_buffs:
            del self.active_buffs[name]
    
    def update(self):
        """Обновить все баффы, удалить истекшие"""
        expired = []
        for name, buff in self.active_buffs.items():
            if not buff.is_active:
                expired.append(name)
        
        for name in expired:
            del self.active_buffs[name]
        
        return len(expired)
    
    def get_modifier(self, buff_type: BuffType) -> float:
        """Получить суммарный модификатор для типа баффа"""
        total = 1.0  # 1.0 = 100%
        for buff in self.active_buffs.values():
            if buff.buff_type == buff_type:
                total += buff.value / 100.0
        return total
    
    def get_all_buffs(self) -> Dict:
        """Вернуть словарь с информацией о баффах для UI"""
        result = {}
        for name, buff in self.active_buffs.items():
            result[name] = {
                "remaining": buff.remaining,
                "value": buff.value,
                "type": buff.buff_type.value,
                "icon": buff.icon
            }
        return result

# ============ ПЕРСОНАЖ ============

class Player:
    def __init__(self, name: str = "Hero"):
        self.name = name
        self.level = 1
        self.exp = 0
        self.exp_to_next = 100
        
        # Базовые статы
        self.base_hp = 100
        self.base_mp = 50
        self.base_strength = 10
        self.base_defense = 5
        self.base_speed = 100
        
        # Текущие значения
        self.hp = self.base_hp
        self.mp = self.base_mp
        
        # Система баффов
        self.buffs = BuffSystem()
        
        # Инвентарь
        self.inventory: List[Dict] = []
        self.gold = 0
        
    def apply_damage(self, damage: int) -> int:
        """Применить урон, вернуть реальный урон после защиты"""
        defense_mod = self.buffs.get_modifier(BuffType.DEFENSE)
        actual_damage = max(1, int(damage / defense_mod))
        self.hp = max(0, self.hp - actual_damage)
        return actual_damage
    
    def heal(self, amount: int):
        """Лечение"""
        heal_mod = self.buffs.get_modifier(BuffType.HEAL)
        actual_heal = int(amount * heal_mod)
        self.hp = min(self.base_hp, self.hp + actual_heal)
    
    def get_damage(self) -> int:
        """Рассчитать исходящий урон с баффами"""
        damage_mod = self.buffs.get_modifier(BuffType.DAMAGE)
        base_damage = self.base_strength * 5
        return int(base_damage * damage_mod)
    
    def get_speed(self) -> int:
        """Получить скорость передвижения с баффами"""
        speed_mod = self.buffs.get_modifier(BuffType.SPEED)
        return int(self.base_speed * speed_mod)
    
    def get_stats(self) -> Dict:
        """Вернуть все статы для UI"""
        return {
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.base_hp,
            "mp": self.mp,
            "max_mp": self.base_mp,
            "strength": self.base_strength,
            "speed": self.get_speed(),
            "damage": self.get_damage(),
            "buffs": self.buffs.get_all_buffs()
        }
    
    def add_exp(self, amount: int):
        """Добавить опыт, проверить уровень"""
        self.exp += amount
        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self.level_up()
    
    def level_up(self):
        """Повышение уровня"""
        self.level += 1
        self.base_hp += 20
        self.base_mp += 10
        self.base_strength += 3
        self.base_defense += 2
        self.hp = self.base_hp
        self.mp = self.base_mp
        self.exp_to_next = int(self.exp_to_next * 1.2)

# ============ МОНСТРЫ ============

class Monster:
    def __init__(self, name: str, level: int, hp: int, damage: int, exp_reward: int):
        self.name = name
        self.level = level
        self.max_hp = hp
        self.hp = hp
        self.damage = damage
        self.exp_reward = exp_reward
        self.position = (random.uniform(-10, 10), 0, random.uniform(-10, 10))
    
    def attack(self, player: Player) -> int:
        """Атаковать игрока, вернуть урон"""
        return player.apply_damage(self.damage)
    
    def take_damage(self, damage: int) -> bool:
        """Получить урон, вернуть True если умер"""
        self.hp -= damage
        return self.hp <= 0

# ============ ГЛОБАЛЬНЫЕ ОБЪЕКТЫ ============

player = Player()
monsters: List[Monster] = []
active_buffs = {}

# Создаем несколько монстров
monsters.append(Monster("🦇 Летучая мышь", 1, 30, 8, 25))
monsters.append(Monster("🧟 Скелет", 2, 50, 12, 40))
monsters.append(Monster("🐺 Волк", 3, 70, 15, 60))
monsters.append(Monster("🧙 Орк-шаман", 4, 90, 18, 85))
monsters.append(Monster("🐉 Дракончик", 5, 150, 25, 120))

# ============ ФУНКЦИИ ДЛЯ ВЫЗОВА ИЗ JS ============

def apply_buff(buff_name: str, duration: int) -> bool:
    """Применить бафф к игроку"""
    global active_buffs
    
    buffs_map = {
        "dragon_power": (BuffType.DAMAGE, 50, "🐉 Сила дракона", "+50% урона"),
        "stone_skin": (BuffType.DEFENSE, 40, "🪨 Каменная кожа", "+40% защиты"),
        "wind_walk": (BuffType.SPEED, 60, "💨 Скорость ветра", "+60% скорости"),
        "divine_light": (BuffType.HEAL, 30, "✨ Божественный свет", "+30% лечения")
    }
    
    if buff_name in buffs_map:
        buff_type, value, display_name, desc = buffs_map[buff_name]
        result = player.buffs.add_buff(display_name, buff_type, value, duration)
        if result:
            update_global_buffs()
        return result
    
    return False

def update_global_buffs():
    """Обновить глобальную переменную баффов для UI"""
    global active_buffs
    active_buffs = player.buffs.get_all_buffs()

def update_buffs():
    """Обновить баффы (вызывается каждую секунду)"""
    global active_buffs
    player.buffs.update()
    active_buffs = player.buffs.get_all_buffs()
    return active_buffs

def get_player_stats() -> Dict:
    """Получить статы игрока"""
    return player.get_stats()

def attack_monster(monster_index: int) -> Dict:
    """Атаковать монстра по индексу"""
    if monster_index >= len(monsters):
        return {"error": "Монстр не найден"}
    
    monster = monsters[monster_index]
    if monster.hp <= 0:
        return {"error": "Монстр уже мертв"}
    
    # Игрок атакует
    damage = player.get_damage()
    monster_died = monster.take_damage(damage)
    
    result = {
        "player_damage": damage,
        "monster_hp": monster.hp,
        "died": monster_died
    }
    
    # Если монстр умер, даем опыт
    if monster_died:
        player.add_exp(monster.exp_reward)
        result["exp_gained"] = monster.exp_reward
        result["new_level"] = player.level
        
        # Возрождаем монстра через некоторое время (логика на JS)
    
    # Монстр контратакует если жив
    if not monster_died:
        monster_damage = monster.attack(player)
        result["monster_damage"] = monster_damage
        result["player_hp"] = player.hp
    
    return result

def get_monsters() -> List[Dict]:
    """Получить список всех монстров"""
    return [{
        "name": m.name,
        "level": m.level,
        "hp": m.hp,
        "max_hp": m.max_hp,
        "position": m.position
    } for m in monsters]

# ============ ДОПОЛНИТЕЛЬНАЯ ЛОГИКА (расширяется до 2000+ строк) ============

class Spell:
    """Система заклинаний"""
    def __init__(self, name: str, mana_cost: int, cooldown: float):
        self.name = name
        self.mana_cost = mana_cost
        self.cooldown = cooldown
        self.last_cast = 0
    
    def can_cast(self, current_mp: int, current_time: float) -> bool:
        return current_mp >= self.mana_cost and (current_time - self.last_cast) >= self.cooldown

# Магия игрока
spells = {
    "fireball": Spell("Огненный шар", 20, 3.0),
    "heal": Spell("Лечение", 15, 2.0),
    "haste": Spell("Ускорение", 25, 10.0)
}

print("✅ game_logic.py загружен! Система баффов и персонаж готовы.")