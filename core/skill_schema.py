"""
core/skill_schema.py
스킬별로 조절 가능한 EasyRPG/네이티브 필드 정의(SKILL_FIELD_DEFS)와,
예전 버전 프로젝트 설정을 새 스키마로 옮겨주는 마이그레이션 함수.

새 EasyRPG 스킬 옵션이 추가되면 이 목록에 dict 하나만 추가하면
Skill 탭(속성 편집기)과 최종 패치(core/lcf.py) 양쪽에 자동으로 반영됩니다.

bool 필드는 EDB에 "T"/"F" 문자열로 기록됩니다 (System 탭의 "1"/"0"과는 다른 관례이며,
EasyRPG가 실제로 Skill 노드에서 사용하는 표기법입니다).
"""

SKILL_FIELD_DEFS = [
    {"name": "name", "label": "이름", "type": "string", "group": "전투",
     "default": "", "skip_if_empty": True,
     "description": "스킬 이름입니다. 알만툴 편집기의 글자 수 제한과 무관하게 자유롭게 입력할 수 있습니다."},
    {"name": "power", "label": "기본 위력", "type": "int", "group": "전투",
     "default": 0, "max": 9999,
     "description": "스킬의 기본 위력(데미지 계산에 사용)입니다."},
    {"name": "physical_rate", "label": "공격력 비율", "type": "int", "group": "전투",
     "default": 0, "max": 100,
     "description": "1 = 5% 비율로 공격력이 데미지 계산에 반영됩니다."},
    {"name": "magical_rate", "label": "정신력 비율", "type": "int", "group": "전투",
     "default": 0, "max": 100,
     "description": "1 = 2.5% 비율로 정신력이 데미지 계산에 반영됩니다."},
    {"name": "easyrpg_critical_hit_chance", "label": "크리티컬 확률 (%)", "type": "int", "group": "전투",
     "default": 0, "max": 100,
     "description": "이 스킬의 크리티컬 발생 확률입니다."},
    {"name": "easyrpg_affected_by_row_modifiers", "label": "전열/후열 보정 적용", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "전열/후열 위치에 따른 데미지 보정을 받습니다."},
    {"name": "easyrpg_enable_stat_absorbing", "label": "능력치 흡수 활성화", "type": "bool", "group": "전투",
     "default": False, "bool_encoding": "TF",
     "description": "대상의 능력치를 흡수하는 효과를 활성화합니다."},
    {"name": "easyrpg_affected_by_evade_all_physical_attacks", "label": "완전 회피(물리) 영향받음",
     "type": "bool", "group": "반사/회피", "default": False, "bool_encoding": "TF",
     "description": "'모든 물리 공격 회피' 상태의 영향을 받습니다."},
    {"name": "easyrpg_ignore_reflect", "label": "리플렉트 무시", "type": "bool", "group": "반사/회피",
     "default": False, "bool_encoding": "TF",
     "description": "'마법 반사' 상태를 무시하고 대상에게 직접 적용됩니다."},
    {"name": "easyrpg_state_hit", "label": "상태이상 적중 보정", "type": "int", "group": "상태이상",
     "default": -1, "max": 2147483646,
     "description": "상태이상 적중률 보정값입니다. -1은 기본값을 의미합니다."},
    {"name": "easyrpg_attribute_hit", "label": "속성 적중 보정", "type": "int", "group": "상태이상",
     "default": -1, "max": 2147483646,
     "description": "속성 적중률 보정값입니다. -1은 기본값을 의미합니다."},
    {"name": "easyrpg_ignore_restrict_skill", "label": "스킬 사용 제한 무시", "type": "bool", "group": "제한",
     "default": False, "bool_encoding": "TF",
     "description": "행동 제한 상태여도 이 스킬 사용을 허용합니다."},
    {"name": "easyrpg_ignore_restrict_magic", "label": "마법 사용 제한 무시", "type": "bool", "group": "제한",
     "default": False, "bool_encoding": "TF",
     "description": "마법 봉인 상태여도 이 스킬 사용을 허용합니다."},
    {"name": "easyrpg_battle2k3_message", "label": "RPG2003 전투 메시지", "type": "string", "group": "메시지",
     "default": "default_message",
     "description": "전투 중 표시할 메시지입니다. 'default_message'는 기본 메시지를 그대로 사용합니다."},
    {"name": "easyrpg_hp_type", "label": "HP 소모 방식", "type": "enum", "group": "HP 소모",
     "default": 0, "options": {"0": "고정값 소모 (HP Cost)", "1": "비율 소모 (HP Percent)"},
     "description": "이 스킬이 HP를 고정값으로 소모할지, 비율로 소모할지 선택합니다."},
    {"name": "easyrpg_hp_cost", "label": "HP 소모량", "type": "int", "group": "HP 소모",
     "default": 0, "max": 2147483646,
     "description": "HP 소모 방식이 '고정값 소모'일 때만 사용됩니다.",
     "enabled_when": {"field": "easyrpg_hp_type", "equals": 0}},
    {"name": "easyrpg_hp_percent", "label": "HP 소모 비율 (%)", "type": "int", "group": "HP 소모",
     "default": 0, "max": 100,
     "description": "HP 소모 방식이 '비율 소모'일 때만 사용됩니다.",
     "enabled_when": {"field": "easyrpg_hp_type", "equals": 1}},
]

SKILL_FIELD_GROUPS = ["전투", "HP 소모", "상태이상", "제한", "반사/회피", "메시지"]


def default_skill_fields():
    return {fd["name"]: fd["default"] for fd in SKILL_FIELD_DEFS}


def migrate_skill_entry(entry):
    """예전 버전(최상위에 rating/physical_rate/... 및 "keep" sentinel을 두던 방식,
    혹은 실제 EDB 태그명과 다른 "rating"이라는 잘못된 필드명으로 저장되던 방식)의
    스킬 항목을 새 스키마({"id":.., "fields": {...}})로 변환합니다.
    이미 새 형식이면 새로 추가된 필드만 기본값으로 채워서 반환합니다."""
    if isinstance(entry.get("fields"), dict):
        fields = dict(entry["fields"])
        # 예전 버전에서 실제 EDB 태그명(<power>)이 아닌 "rating"으로 잘못 저장된 값을 이전합니다.
        if "rating" in fields:
            if "power" not in fields:
                fields["power"] = fields.pop("rating")
            else:
                fields.pop("rating")
        for fd in SKILL_FIELD_DEFS:
            if fd["name"] not in fields:
                fields[fd["name"]] = fd["default"]
        return {"id": entry["id"], "fields": fields}

    fields = {}
    for fd in SKILL_FIELD_DEFS:
        name = fd["name"]
        old_val = entry.get(name, "keep")
        if name == "power" and old_val == "keep" and "rating" in entry:
            old_val = entry.get("rating", "keep")
        fields[name] = fd["default"] if old_val == "keep" else old_val
    return {"id": entry["id"], "fields": fields}
