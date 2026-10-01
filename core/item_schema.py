"""
core/item_schema.py
아이템별로 조절 가능한 EasyRPG/네이티브 필드 정의(ITEM_FIELD_DEFS)와,
예전 버전 프로젝트 설정을 새 스키마로 옮겨주는 마이그레이션 함수.
core/skill_schema.py와 동일한 패턴입니다 - 새 아이템 옵션이 추가되면
이 목록에 dict 하나만 추가하면 Item 탭(속성 편집기)과 최종 패치(core/lcf.py)
양쪽에 자동으로 반영됩니다.
"""

# 장비 능력치(ATK/DEF/MIND/AGI/HIT/CRI)를 수정할 수 있는 아이템 타입:
# 무기(1)/방패(2)/방어구(3)/투구(4)/장신구(5). 그 외 타입(소모품 등)은 편집을 막고
# edb에도 쓰지 않습니다 (core/lcf.py의 아이템 패치 부분 참고).
EQUIPMENT_ITEM_TYPES = (1, 2, 3, 4, 5)

# from_edb: edb에 이미 있는 실제 값을 화면에 보여주고, 목록에 처음 추가할 때 기본값으로
#           채워 넣습니다. 값이 비어있거나(None/"") 아직 손대지 않았다면 edb 원래 값이
#           그대로 유지되도록 저장 시 쓰지 않습니다(default None인 필드는 None이면 건너뜀).
# equipment_only: 장비류 아이템에서만 편집/저장됩니다.
ITEM_FIELD_DEFS = [
    {"name": "name", "label": "이름", "type": "string", "group": "일반",
     "default": "", "skip_if_empty": True,
     "description": "아이템 이름입니다. 알만툴 편집기의 글자 수 제한과 무관하게 자유롭게 입력할 수 있습니다."},
    {"name": "description", "label": "설명", "type": "string", "group": "일반",
     "default": "", "skip_if_empty": True,
     "from_edb": True,
     "description": "아이템 메뉴 등에 표시되는 설명 문구입니다."},
    {"name": "easyrpg_max_count", "label": "최대 소지 수량", "type": "int", "group": "일반",
     "default": -1, "max": 255,
     "description": "이 아이템의 최대 소지 수량입니다. -1은 엔진 기본값을 사용합니다."},
    {"name": "easyrpg_using_message", "label": "사용 메시지", "type": "string", "group": "일반",
     "default": "default_message",
     "description": "아이템 사용 시 표시할 메시지입니다. 'default_message'는 기본 메시지를 그대로 사용합니다."},
    {"name": "atk_points1", "label": "ATK", "type": "int", "group": "장비 능력치",
     "default": None, "max": 2147483646, "from_edb": True, "equipment_only": True,
     "description": "장비 시 공격력(ATK) 증가량입니다. 무기/방패/방어구/투구/장신구 타입에서만 수정할 수 있습니다."},
    {"name": "def_points1", "label": "DEF", "type": "int", "group": "장비 능력치",
     "default": None, "max": 2147483646, "from_edb": True, "equipment_only": True,
     "description": "장비 시 방어력(DEF) 증가량입니다. 장비류 아이템에서만 수정할 수 있습니다."},
    {"name": "spi_points1", "label": "MIND", "type": "int", "group": "장비 능력치",
     "default": None, "max": 2147483646, "from_edb": True, "equipment_only": True,
     "description": "장비 시 정신력(MIND) 증가량입니다. 장비류 아이템에서만 수정할 수 있습니다."},
    {"name": "agi_points1", "label": "AGI", "type": "int", "group": "장비 능력치",
     "default": None, "max": 2147483646, "from_edb": True, "equipment_only": True,
     "description": "장비 시 민첩성(AGI) 증가량입니다. 장비류 아이템에서만 수정할 수 있습니다."},
    {"name": "hit", "label": "HIT", "type": "int", "group": "장비 능력치",
     "default": None, "min": 0, "max": 100, "from_edb": True, "equipment_only": True,
     "description": "장비의 명중률(0~100)입니다. 장비류 아이템에서만 수정할 수 있습니다."},
    {"name": "critical_hit", "label": "CRI", "type": "int", "group": "장비 능력치",
     "default": None, "min": 0, "max": 100, "from_edb": True, "equipment_only": True,
     "description": "장비의 치명타율(0~100)입니다. 장비류 아이템에서만 수정할 수 있습니다."},
]


def default_item_fields():
    return {fd["name"]: fd["default"] for fd in ITEM_FIELD_DEFS}


def migrate_item_entry(entry):
    """예전 버전({"id":.., "easyrpg_max_count": 값})의 아이템 항목을
    새 스키마({"id":.., "fields": {...}})로 변환합니다. 이미 새 형식이면
    새로 추가된 필드만 기본값으로 채워서 반환합니다."""
    if isinstance(entry.get("fields"), dict):
        fields = dict(entry["fields"])
        for fd in ITEM_FIELD_DEFS:
            if fd["name"] not in fields:
                fields[fd["name"]] = fd["default"]
        return {"id": entry["id"], "fields": fields}

    fields = default_item_fields()
    if "easyrpg_max_count" in entry:
        fields["easyrpg_max_count"] = entry["easyrpg_max_count"]
    return {"id": entry["id"], "fields": fields}
