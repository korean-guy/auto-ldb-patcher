"""
core/terrain_schema.py
지형(Terrain)별로 조절 가능한 EasyRPG 확장 옵션 필드 정의(TERRAIN_FIELD_DEFS)와
기본값, 그리고 예전 버전 프로젝트 설정을 새 스키마로 옮겨주는 마이그레이션 함수.
core/item_schema.py와 동일한 패턴입니다 - 새 지형 옵션이 추가되면 이 목록에
dict 하나만 추가하면 Terrain 탭(속성 편집기)과 최종 패치(core/lcf.py) 양쪽에
자동으로 반영됩니다.

지형은 데미지량(damage) 등 알만툴 순정 필드도 많지만, 이번 요청은 EasyRPG
확장 옵션 2종(easyrpg_damage_in_percent/easyrpg_damage_can_kill)만 조절하는
것이므로 그 외 순정 필드는 다루지 않습니다.
"""

TERRAIN_FIELD_DEFS = [
    {"name": "easyrpg_damage_in_percent", "label": "데미지를 비율(%)로 적용", "type": "bool", "group": "EasyRPG 확장 옵션",
     "default": False, "bool_encoding": "TF",
     "description": "이 지형의 데미지(damage) 값을 고정 수치가 아니라 최대 HP 대비 비율(%)로 적용합니다."},
    {"name": "easyrpg_damage_can_kill", "label": "데미지로 사망 가능", "type": "bool", "group": "EasyRPG 확장 옵션",
     "default": False, "bool_encoding": "TF",
     "description": "이 지형의 데미지로 인해 HP가 0이 되면 사망 처리됩니다(기본값은 HP 1은 항상 남음)."},
]


def default_terrain_fields():
    return {fd["name"]: fd["default"] for fd in TERRAIN_FIELD_DEFS}


def migrate_terrain_entry(entry):
    """새로 추가된 필드가 있으면 기본값으로 채워서 반환합니다 (다른 탭과 동일한 패턴을
    유지해 향후 필드가 늘어나도 기존 프로젝트가 깨지지 않도록 합니다)."""
    fields = dict(entry.get("fields", {}))
    for fd in TERRAIN_FIELD_DEFS:
        if fd["name"] not in fields:
            fields[fd["name"]] = fd["default"]
    return {"id": entry["id"], "fields": fields}
