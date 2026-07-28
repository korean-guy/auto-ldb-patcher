"""
core/enemy_schema.py
적(Enemy)별로 조절 가능한 기본 스테이터스 필드와 EasyRPG 확장 옵션 필드 정의
(ENEMY_FIELD_DEFS), 기본값, 그리고 예전 버전 프로젝트 설정을 새 스키마로 옮겨주는
마이그레이션 함수. core/item_schema.py, core/skill_schema.py와 동일한 패턴입니다 -
새 적 옵션이 추가되면 이 목록에 dict 하나만 추가하면 Enemy 탭(속성 편집기)과
최종 패치(core/lcf.py) 양쪽에 자동으로 반영됩니다.

기본 스테이터스 6종(max_hp/max_sp/attack/defense/spirit/agility)은 액터/클래스의
레벨별 능력치 배열과 달리 적은 레벨 개념이 없어 스칼라 값 하나이므로, 다른 EasyRPG
옵션들과 마찬가지로 이 목록에 포함시켜 속성 편집기로 함께 편집합니다.
"""

ENEMY_FIELD_DEFS = [
    {"name": "max_hp", "label": "최대 HP", "type": "int", "group": "기본 스테이터스",
     "default": 1, "max": 2147483646,
     "description": "이 적의 최대 HP입니다."},
    {"name": "max_sp", "label": "최대 SP", "type": "int", "group": "기본 스테이터스",
     "default": 0, "max": 2147483646,
     "description": "이 적의 최대 SP입니다."},
    {"name": "attack", "label": "공격력", "type": "int", "group": "기본 스테이터스",
     "default": 0, "max": 2147483646,
     "description": "이 적의 공격력입니다."},
    {"name": "defense", "label": "방어력", "type": "int", "group": "기본 스테이터스",
     "default": 0, "max": 2147483646,
     "description": "이 적의 방어력입니다."},
    {"name": "spirit", "label": "정신력", "type": "int", "group": "기본 스테이터스",
     "default": 0, "max": 2147483646,
     "description": "이 적의 정신력입니다."},
    {"name": "agility", "label": "민첩성", "type": "int", "group": "기본 스테이터스",
     "default": 0, "max": 2147483646,
     "description": "이 적의 민첩성입니다."},

    {"name": "easyrpg_enemyai", "label": "AI 유형", "type": "enum", "group": "AI",
     "default": -1,
     "options": {"-1": "기본값", "0": "RPG_RT", "1": "RPG_RT+", "2": "ATTACK"},
     "description": "이 적에게 적용할 AI 유형입니다."},

    {"name": "easyrpg_prevent_critical", "label": "크리티컬 방지", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "플레이어 측이 이 적에게 크리티컬을 가할 수 없게 됩니다."},
    {"name": "easyrpg_raise_evasion", "label": "회피율 상승", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "이 적의 회피율이 상승합니다."},
    {"name": "easyrpg_immune_to_attribute_downshifts", "label": "속성 약점 완화 면역", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "속성 상성에 의한 데미지 등급 하락(약점 완화)의 영향을 받지 않습니다."},
    {"name": "easyrpg_ignore_evasion", "label": "회피 무시", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "대상의 회피를 무시하고 공격합니다."},
    {"name": "easyrpg_super_guard", "label": "슈퍼 가드", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "이 적이 방어(가드) 상태일 때 받는 데미지 감소 효과가 강화됩니다."},
    {"name": "easyrpg_attack_all", "label": "전체 공격", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "일반 공격이 파티 전체를 대상으로 합니다."},

    {"name": "easyrpg_hit", "label": "명중률 보정", "type": "int", "group": "특수 공격",
     "default": -1, "max": 2147483646,
     "description": "이 적의 명중률 보정값입니다. -1은 기본값을 의미합니다."},
    {"name": "easyrpg_state_set", "label": "공격 시 상태이상 부여", "type": "string", "group": "특수 공격",
     "default": "",
     "description": "공격 시 부여할 상태이상 ID 목록입니다(쉼표로 구분)."},
    {"name": "easyrpg_state_chance", "label": "상태이상 확률", "type": "int", "group": "특수 공격",
     "default": 0, "max": 100,
     "description": "위 상태이상이 걸릴 확률(%)입니다."},
    {"name": "easyrpg_attribute_set", "label": "공격 속성", "type": "string", "group": "특수 공격",
     "default": "",
     "description": "공격 시 적용할 속성 ID 목록입니다(쉼표로 구분)."},
]

# 기본 스테이터스 6종은 edb에 이미 존재하는 실제 수치를 기본값으로 사용합니다
# (core/skill_schema.py의 STAT_FIELDS_FROM_EDB와 동일한 패턴).
STAT_FIELDS_FROM_EDB = ("max_hp", "max_sp", "attack", "defense", "spirit", "agility")


def default_enemy_fields():
    return {fd["name"]: fd["default"] for fd in ENEMY_FIELD_DEFS}


def migrate_enemy_entry(entry):
    """새로 추가된 필드가 있으면 기본값으로 채워서 반환합니다 (다른 탭과 동일한 패턴을
    유지해 향후 필드가 늘어나도 기존 프로젝트가 깨지지 않도록 합니다)."""
    fields = dict(entry.get("fields", {}))
    for fd in ENEMY_FIELD_DEFS:
        if fd["name"] not in fields:
            fields[fd["name"]] = fd["default"]
    return {"id": entry["id"], "fields": fields}
