"""
core/class_schema.py
클래스(Class)별로 조절 가능한 필드 정의입니다. core/actor_schema.py와 같은 패턴입니다.

주의: RPG Maker 2003의 <Class> 노드에 실제로 어떤 필드가 더 있는지(요청에서는
exp_base/exp_inflation/exp_correction 세 개와 "기타 클래스 설정치"라고만 언급됨) 확인할
수 있는 실제 EDB 예시를 아직 받지 못해서, 우선 명시적으로 주어진 경험치 3개 필드만
반영했습니다. Actor와 마찬가지로 <parameters><Parameters> 능력치 성장 배열을 갖는다고
가정했고(맨손 공격이나 easyrpg_* 전용 필드는 이번 요청에 없어 추가하지 않았습니다),
Class 노드에는 Actor의 final_level 같은 자체 레벨 상한 필드가 없다고 보고 System 탭의
'최대 레벨' 설정을 그대로 따르도록 했습니다. 실제 EDB에서 태그명이 다르거나 필드가
더 있으면 이 파일과 core/lcf.py의 클래스 처리 부분만 고치면 됩니다.
"""

CLASS_FIELD_DEFS = [
    {"name": "exp_base", "label": "경험치 기본값", "type": "int", "group": "경험치",
     "default": 0, "max": 2147483646,
     "description": "이 클래스의 경험치 곡선 기본값(exp_base)입니다."},
    {"name": "exp_inflation", "label": "경험치 증가도", "type": "int", "group": "경험치",
     "default": 0, "max": 2147483646,
     "description": "이 클래스의 경험치 곡선 증가도(exp_inflation)입니다."},
    {"name": "exp_correction", "label": "경험치 보정치", "type": "int", "group": "경험치",
     "default": 0, "max": 2147483646,
     "description": "이 클래스의 경험치 곡선 보정치(exp_correction)입니다."},
]


def default_class_fields():
    return {fd["name"]: fd["default"] for fd in CLASS_FIELD_DEFS}


def migrate_class_entry(entry):
    """새로 추가된 필드가 있으면 기본값으로 채워서 반환합니다 (다른 탭과 동일한 패턴)."""
    fields = dict(entry.get("fields", {}))
    for fd in CLASS_FIELD_DEFS:
        if fd["name"] not in fields:
            fields[fd["name"]] = fd["default"]

    if "parameters" not in entry or not isinstance(entry["parameters"], dict):
        entry["parameters"] = {}

    return {
        "id": entry["id"],
        "fields": fields,
        "parameters": entry["parameters"],
    }
