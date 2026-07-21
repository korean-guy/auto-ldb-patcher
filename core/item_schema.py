"""
core/item_schema.py
아이템별로 조절 가능한 EasyRPG/네이티브 필드 정의(ITEM_FIELD_DEFS)와,
예전 버전 프로젝트 설정을 새 스키마로 옮겨주는 마이그레이션 함수.
core/skill_schema.py와 동일한 패턴입니다 - 새 아이템 옵션이 추가되면
이 목록에 dict 하나만 추가하면 Item 탭(속성 편집기)과 최종 패치(core/lcf.py)
양쪽에 자동으로 반영됩니다.
"""

ITEM_FIELD_DEFS = [
    {"name": "easyrpg_max_count", "label": "최대 소지 수량", "type": "int", "group": "일반",
     "default": -1, "max": 255,
     "description": "이 아이템의 최대 소지 수량입니다. -1은 엔진 기본값을 사용합니다."},
    {"name": "easyrpg_using_message", "label": "사용 메시지", "type": "string", "group": "일반",
     "default": "default_message",
     "description": "아이템 사용 시 표시할 메시지입니다. 'default_message'는 기본 메시지를 그대로 사용합니다."},
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
