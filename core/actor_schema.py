"""
core/actor_schema.py
액터(Actor)별로 조절 가능한 필드 정의와 기본값, 그리고 능력치 성장 배열
(maxhp/maxsp/attack/defense/spirit/agility) 관련 상수를 담고 있습니다.

레벨 상한(final_level)과 능력치 성장 배열은 서로 개수가 반드시 일치해야 해서
(개수가 안 맞으면 lcf2xml/엔진 쪽에서 오버플로우가 날 수 있음) ACTOR_FIELD_DEFS에
넣지 않고 tabs/actor_tab.py에서 전용 로직(자동 리사이즈)으로 다룹니다.
이 목록에는 그 외 스칼라 값들(경험치 곡선, EasyRPG 옵션)만 둡니다 - 새 EasyRPG
액터 옵션이 추가되면 이 목록에 dict 하나만 추가하면 Actor 탭에 자동으로 나타납니다.
"""

# 능력치 성장 배열 6종 - 표시명과 함께 정의 (레벨 수만큼 원소를 가짐)
STAT_ARRAY_KEYS = ["maxhp", "maxsp", "attack", "defense", "spirit", "agility"]
STAT_ARRAY_LABELS = {
    "maxhp": "최대 HP", "maxsp": "최대 SP", "attack": "공격력",
    "defense": "방어력", "spirit": "정신력", "agility": "민첩성",
}

ABSOLUTE_MAX_LEVEL = 255

ACTOR_FIELD_DEFS = [
    {"name": "exp_base", "label": "경험치 기본값", "type": "int", "group": "경험치",
     "default": 0, "max": 2147483646,
     "description": "경험치 곡선의 기본값(exp_base)입니다."},
    {"name": "exp_inflation", "label": "경험치 증가도", "type": "int", "group": "경험치",
     "default": 0, "max": 2147483646,
     "description": "경험치 곡선의 증가도(exp_inflation)입니다."},
    {"name": "exp_correction", "label": "경험치 보정치", "type": "int", "group": "경험치",
     "default": 0, "max": 2147483646,
     "description": "경험치 곡선의 보정치(exp_correction)입니다."},

    {"name": "easyrpg_actorai", "label": "AI 유형", "type": "enum", "group": "AI",
     "default": -1,
     "options": {"-1": "기본값", "0": "RPG_RT", "1": "RPG_RT+", "2": "ATTACK"},
     "description": "이 캐릭터에 적용할 AI 유형입니다."},

    {"name": "easyrpg_prevent_critical", "label": "크리티컬 방지", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "적이 이 캐릭터에게 크리티컬을 가할 수 없게 됩니다."},
    {"name": "easyrpg_raise_evasion", "label": "회피율 상승", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "회피율이 상승합니다."},
    {"name": "easyrpg_immune_to_attribute_downshifts", "label": "속성 약점 완화 면역", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "속성 상성에 의한 데미지 등급 하락(약점 완화)의 영향을 받지 않습니다."},
    {"name": "easyrpg_ignore_evasion", "label": "회피 무시", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "대상의 회피를 무시하고 공격합니다."},
    {"name": "easyrpg_dual_attack", "label": "동시 공격(듀얼 어택)", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "한 번에 두 번 공격합니다."},
    {"name": "easyrpg_attack_all", "label": "전체 공격", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "일반 공격이 적 전체를 대상으로 합니다."},

    {"name": "easyrpg_unarmed_hit", "label": "맨손 공격 명중 보정", "type": "int", "group": "맨손 공격",
     "default": -1, "max": 2147483646,
     "description": "무기를 장착하지 않았을 때의 명중률 보정값입니다. -1은 기본값을 의미합니다."},
    {"name": "easyrpg_unarmed_state_set", "label": "맨손 공격 상태이상 부여", "type": "string", "group": "맨손 공격",
     "default": "",
     "description": "무기를 장착하지 않았을 때 부여할 상태이상 ID 목록입니다(쉼표로 구분)."},
    {"name": "easyrpg_unarmed_state_chance", "label": "맨손 공격 상태이상 확률", "type": "int", "group": "맨손 공격",
     "default": 0, "max": 100,
     "description": "맨손 공격 시 위 상태이상이 걸릴 확률(%)입니다."},
    {"name": "easyrpg_unarmed_attribute_set", "label": "맨손 공격 속성", "type": "string", "group": "맨손 공격",
     "default": "",
     "description": "무기를 장착하지 않았을 때 적용할 속성 ID 목록입니다(쉼표로 구분)."},
]


def default_actor_fields():
    return {fd["name"]: fd["default"] for fd in ACTOR_FIELD_DEFS}


def migrate_actor_entry(entry):
    """새로 추가된 필드가 있으면 기본값으로 채워서 반환합니다 (Actor 탭은 신규 기능이라
    지금은 예전 저장 형식이 없지만, 다른 탭과 동일한 패턴을 유지해 향후 필드가
    늘어나도 기존 프로젝트가 깨지지 않도록 합니다)."""
    fields = dict(entry.get("fields", {}))
    for fd in ACTOR_FIELD_DEFS:
        if fd["name"] not in fields:
            fields[fd["name"]] = fd["default"]

    if "final_level" not in entry:
        entry["final_level"] = ABSOLUTE_MAX_LEVEL
    if "parameters" not in entry or not isinstance(entry["parameters"], dict):
        entry["parameters"] = {k: [] for k in STAT_ARRAY_KEYS}
    if "original_fields" not in entry:
        entry["original_fields"] = dict(fields)
    if "original_final_level" not in entry:
        entry["original_final_level"] = entry["final_level"]
    if "original_parameters" not in entry:
        entry["original_parameters"] = {k: list(v) for k, v in entry["parameters"].items()}

    return {
        "id": entry["id"],
        "fields": fields,
        "final_level": entry["final_level"],
        "parameters": entry["parameters"],
        "original_fields": entry["original_fields"],
        "original_final_level": entry["original_final_level"],
        "original_parameters": entry["original_parameters"],
    }


def resize_stat_array(values, new_length):
    """능력치 성장 배열을 new_length개로 맞춥니다.
    늘어나면 마지막 값을 반복해서 채우고(값이 하나도 없으면 0), 줄어들면 뒤를 자릅니다."""
    values = list(values or [])
    if new_length <= 0:
        return []
    if len(values) == new_length:
        return values
    if len(values) > new_length:
        return values[:new_length]
    pad_value = values[-1] if values else 0
    return values + [pad_value] * (new_length - len(values))
