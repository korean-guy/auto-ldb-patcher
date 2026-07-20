"""
core/config.py
JSON 읽기/쓰기, 공통/프로젝트 config 관리, 게임 폴더(프로젝트) 선택을
모두 담당하는 ConfigManager. UI(탭)들은 이 클래스의 인스턴스(cfg)를
공유해서 설정을 읽고 씁니다.
"""
import os
import json
import copy
from tkinter import messagebox, filedialog

from core.utils import get_project_title, sanitize_folder_name, migrate_system_limits, merge_system_defs


# ---- 시스템 옵션 기본 정의 (최초 설치 시 config.json 시드 데이터로 사용) ----
DEFAULT_SYSTEM_DEFS = {
    "easyrpg_max_savefiles": {
        "type": "int", "name": "최대 세이브 파일 수",
        "description": "저장 가능한 세이브 파일 개수의 상한입니다.",
        "value": 15, "default": 15, "max": 99,
    },
    "easyrpg_max_item_count": {
        "type": "int", "name": "기본 아이템 소지 한도",
        "description": "개별 설정이 없는 아이템에 적용되는 기본 소지 한도입니다.",
        "value": 99, "default": 99, "max": 250,
    },
    "easyrpg_max_level": {
        "type": "int", "name": "최대 레벨",
        "description": "캐릭터가 도달할 수 있는 최대 레벨입니다. -1은 순정 기본값을 의미합니다.",
        "value": -1, "default": -1, "max": 9999,
    },
    "easyrpg_use_rpg2k_battle_commands": {
        "type": "bool", "name": "RPG2000 전투 명령 사용",
        "description": "RPG Maker 2000 방식의 전투 명령 세트를 사용합니다.",
        "value": False, "default": False,
    },
    "easyrpg_default_actorai": {
        "type": "enum", "name": "기본 아군 AI",
        "description": "별도 AI 지정이 없는 아군 전투원에게 적용되는 기본 AI입니다.",
        "value": -1, "default": -1,
        "options": {
            "-1": "기본값",
            "0": "RPG_RT (원작 엔진과 동일, 버그 포함)",
            "1": "RPG_RT+ (원작 기반 + AI 버그 수정)",
            "2": "ATTACK (일반 공격만 수행)",
        },
    },
    "easyrpg_default_enemyai": {
        "type": "enum", "name": "기본 적 AI",
        "description": "별도 AI 지정이 없는 적에게 적용되는 기본 AI입니다. ATTACK(2)은 적에게는 적용되지 않습니다.",
        "value": -1, "default": -1,
        "options": {
            "-1": "기본값",
            "0": "RPG_RT (원작 엔진과 동일, 버그 포함)",
            "1": "RPG_RT+ (원작 기반 + AI 버그 수정)",
            "2": "ATTACK (일반 공격만 수행)",
        },
    },
    "easyrpg_battle_options": {
        "type": "list", "name": "전투 명령",
        "description": "전투 중 사용 가능한 명령과 그 순서입니다.",
        "value": [0, 1, 2], "default": [0, 1, 2],
        "options": {"0": "Battle", "1": "Auto Battle", "2": "Escape"},
    },
}


# ------------------------------------------------------------------
# 공통 JSON 입출력
# ------------------------------------------------------------------
def read_json_safe(path, default_factory):
    """JSON을 안전하게 읽습니다. 없거나 손상되었으면 손상본을 백업하고 기본값으로 새로 만듭니다."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[{path}] JSON 손상 감지 ({e}) - 손상 파일을 백업하고 새로 생성합니다.")
            try:
                os.replace(path, path + ".bak")
            except Exception as be:
                print(f"손상 파일 백업 실패: {be}")
            messagebox.showwarning(
                "설정 파일 복구",
                f"설정 파일이 손상되어 있어 새로 만들었습니다:\n{path}\n\n"
                f"기존 파일은 '{os.path.basename(path)}.bak'로 백업되었습니다."
            )
    data = default_factory()
    write_json_safe(path, data)
    return data


def write_json_safe(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[{path}] 저장 실패: {e}")
        messagebox.showerror("저장 실패", f"설정 파일을 저장하지 못했습니다:\n{path}\n\n사유: {e}")
        return False


# ------------------------------------------------------------------
# ConfigManager: 공통 설정 + 프로젝트(게임별) 설정 + 게임 폴더 선택
# ------------------------------------------------------------------
class ConfigManager:
    def __init__(self, program_dir):
        self.program_dir = program_dir
        self.lcf2xml_bin = os.path.join(self.program_dir, "lcf2xml.exe")
        self.config_file = os.path.join(self.program_dir, "config.json")
        self.projects_dir = os.path.join(self.program_dir, "projects")

        self.common_config = {}
        self.current_config = {"system_limits": {}, "items": [], "skills": []}

        self.game_dir = None
        self.ldb_file = None
        self.edb_file = None
        self.ini_file = None
        self.project_title = None
        self.project_dir = None
        self.project_config_file = None

    def check_program_prerequisites(self):
        missing = []
        if not os.path.exists(self.lcf2xml_bin):
            missing.append(f"- lcf2xml.exe  (위치: {self.program_dir})")
        if missing:
            messagebox.showerror(
                "실행 실패",
                "다음 필수 파일을 찾을 수 없습니다:\n\n" + "\n".join(missing) +
                "\n\n프로그램 파일(py/exe)과 같은 폴더에 배치해 주세요."
            )
            return False
        return True

    # ---- 공통 설정 (프로그램 폴더의 config.json) ----
    def default_common_config(self):
        return {
            "last_game_dir": "",
            "recent_projects": [],
            "settings": {"theme": "dark"},
            "system_limits": copy.deepcopy(DEFAULT_SYSTEM_DEFS),
        }

    def load_common_config(self):
        self.common_config = read_json_safe(self.config_file, self.default_common_config)
        changed = False
        for key, val in self.default_common_config().items():
            if key not in self.common_config:
                self.common_config[key] = val
                changed = True
        if not isinstance(self.common_config.get("system_limits"), dict) or not self.common_config["system_limits"]:
            self.common_config["system_limits"] = copy.deepcopy(DEFAULT_SYSTEM_DEFS)
            changed = True
        else:
            self.common_config["system_limits"] = migrate_system_limits(self.common_config["system_limits"])
            self.common_config["system_limits"] = merge_system_defs(self.common_config["system_limits"], DEFAULT_SYSTEM_DEFS)
        if changed:
            self.save_common_config()

    def save_common_config(self):
        return write_json_safe(self.config_file, self.common_config)

    # ---- 게임 폴더 선택 / 프로젝트 결정 ----
    def select_game_folder(self):
        last_dir = self.common_config.get("last_game_dir", "")
        initial = last_dir if last_dir and os.path.isdir(last_dir) else os.getcwd()
        while True:
            folder = filedialog.askdirectory(
                title="게임 폴더 선택 (RPG_RT.ldb가 있는 폴더)", initialdir=initial
            )
            if not folder:
                return False
            if not os.path.exists(os.path.join(folder, "RPG_RT.ldb")):
                messagebox.showerror(
                    "잘못된 폴더",
                    "선택한 폴더에서 RPG_RT.ldb 파일을 찾을 수 없습니다.\n게임 폴더를 다시 선택해 주세요."
                )
                initial = folder
                continue
            self.set_game_folder(folder)
            return True

    def set_game_folder(self, folder):
        self.game_dir = os.path.abspath(folder)
        self.ldb_file = os.path.join(self.game_dir, "RPG_RT.ldb")
        self.edb_file = os.path.join(self.game_dir, "RPG_RT.edb")
        self.ini_file = os.path.join(self.game_dir, "RPG_RT.ini")

        self.project_title, title_warning = get_project_title(self.game_dir)
        if title_warning:
            messagebox.showwarning("알림", title_warning)

        self.project_dir = os.path.join(self.projects_dir, sanitize_folder_name(self.project_title))
        try:
            os.makedirs(self.project_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("실패", f"프로젝트 폴더를 생성하지 못했습니다.\n{self.project_dir}\n\n사유: {e}")
        self.project_config_file = os.path.join(self.project_dir, "config.json")

        self.common_config["last_game_dir"] = self.game_dir
        recents = [r for r in self.common_config.get("recent_projects", []) if r.get("path") != self.game_dir]
        recents.insert(0, {"title": self.project_title, "path": self.game_dir})
        self.common_config["recent_projects"] = recents[:10]
        self.save_common_config()

    # ---- 프로젝트(게임별) 설정 ----
    def load_project_config(self):
        def factory():
            return {
                "system_limits": copy.deepcopy(self.common_config.get("system_limits", DEFAULT_SYSTEM_DEFS)),
                "items": [], "skills": [],
            }

        self.current_config = read_json_safe(self.project_config_file, factory)

        if "items" not in self.current_config: self.current_config["items"] = []
        if "skills" not in self.current_config: self.current_config["skills"] = []

        migrated = migrate_system_limits(self.current_config.get("system_limits", {}))
        merged = merge_system_defs(migrated, self.common_config.get("system_limits", DEFAULT_SYSTEM_DEFS))
        self.current_config["system_limits"] = merged

        self.save_config()

    def save_config(self):
        return write_json_safe(self.project_config_file, self.current_config)

    def find_sys_def(self, name):
        return self.current_config.get("system_limits", {}).get(name)
