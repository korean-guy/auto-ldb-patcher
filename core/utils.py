"""
core/utils.py
프로그램 전역에서 재사용하는 순수 유틸 함수 모음 (경로/문자열/파싱/스키마 변환).
tkinter나 파일 저장에 관여하지 않는, 부작용 없는 함수들만 여기 둡니다.
"""
import os
import sys
import re
import copy


def get_program_dir():
    """프로그램(스크립트 또는 exe)이 위치한 최상위 폴더를 반환합니다.
    - PyInstaller onefile로 빌드된 경우: exe가 있는 폴더
    - 개발 중 여러 .py 파일로 실행하는 경우: 이 파일(core/utils.py)의 상위(core)의
      또 상위 폴더, 즉 auto ldb patcher.py가 있는 최상위 폴더
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    core_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(core_dir)


def sanitize_folder_name(name):
    invalid = '<>:"/\\|?*'
    cleaned = "".join(c for c in name if c not in invalid).strip()
    return cleaned if cleaned else "untitled_project"


def get_project_title(game_dir):
    """게임 폴더의 RPG_RT.ini에서 게임 제목을 읽어옵니다.
    GameTitle 키를 우선 확인하고, 없으면 Title 키를 확인합니다.
    실패하면 (폴더이름, 경고문구) 형태로 안전하게 대체값을 반환합니다."""
    ini_path = os.path.join(game_dir, "RPG_RT.ini")
    fallback = os.path.basename(os.path.normpath(game_dir))

    if not os.path.exists(ini_path):
        return fallback, "RPG_RT.ini 파일을 찾을 수 없어 폴더 이름을 프로젝트명으로 사용합니다."

    try:
        with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        return fallback, f"RPG_RT.ini 파일을 읽을 수 없어 폴더 이름을 프로젝트명으로 사용합니다.\n(사유: {e})"

    for key_name in ("GameTitle", "Title"):
        m = re.search(rf'^\s*{key_name}\s*=\s*(.+?)\s*$', text, re.MULTILINE | re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip(), None

    return fallback, "RPG_RT.ini에서 GameTitle(Title) 값을 찾을 수 없어 폴더 이름을 프로젝트명으로 사용합니다."


def normalize_options(raw_options):
    """options를 {"값문자열": "라벨"} dict 형태로 정규화합니다."""
    if isinstance(raw_options, dict):
        return {str(k): v for k, v in raw_options.items()}
    if isinstance(raw_options, list):
        out = {}
        for o in raw_options:
            if isinstance(o, dict):
                out[str(o.get("value"))] = o.get("label", str(o.get("value")))
        return out
    return {}


def migrate_system_limits(raw):
    """예전 버전들의 system_limits(구버전 dict / 중간버전 list)를 최신 dict 스키마로 변환합니다."""
    migrated = {}

    def build_entry(key, info):
        if not isinstance(info, dict):
            info = {"value": info}
        entry = dict(info)  # group 등 알려지지 않은 추가 키도 그대로 보존
        entry["type"] = info.get("type", "int")
        entry["name"] = info.get("name", info.get("label", key))
        entry["description"] = info.get("description", "")
        entry["group"] = info.get("group", "일반")
        entry["value"] = info.get("value", info.get("default", -1))
        entry["default"] = info.get("default", info.get("value", -1))
        entry.pop("label", None)
        if entry["type"] == "int":
            entry["max"] = info.get("max", 999999999)
        else:
            entry.pop("max", None)
        if entry["type"] in ("enum", "list"):
            entry["options"] = normalize_options(info.get("options", {}))
        else:
            entry.pop("options", None)
        return entry

    if isinstance(raw, dict):
        for key, info in raw.items():
            migrated[key] = build_entry(key, info)
    elif isinstance(raw, list):
        for info in raw:
            key = info.get("name") if isinstance(info, dict) else None
            if not key:
                continue
            migrated[key] = build_entry(key, info)

    return migrated


def merge_system_defs(existing, template):
    """existing에 없는 항목을 template에서 채워 넣습니다 (새 EasyRPG 옵션 자동 반영)."""
    merged = copy.deepcopy(existing)
    for key, tmpl in template.items():
        if key not in merged:
            merged[key] = copy.deepcopy(tmpl)
    return merged
