"""
core/config.py
JSON 읽기/쓰기, 공통/프로젝트 config 관리, 프로젝트(RPG_RT.ldb) 선택을
모두 담당하는 ConfigManager. UI(탭)들은 이 클래스의 인스턴스(cfg)를
공유해서 설정을 읽고 씁니다.
"""
import os
import json
import copy
from tkinter import messagebox, filedialog

from core.utils import get_project_title, sanitize_folder_name, migrate_system_limits, merge_system_defs
from core.logger import log
from core.i18n import t


# ---- 시스템 옵션 기본 정의 (최초 설치 시 config.json 시드 데이터로 사용) ----
# group: UI에서 옵션을 분류해 보여주기 위한 카테고리 (일반/전투/AI/능력치/HP·SP/변수 등)
DEFAULT_SYSTEM_DEFS = {
    "easyrpg_alternative_exp": {
        "type": "enum", "name": "경험치 계산 방식", "group": "전투",
        "description": "사용할 경험치 계산 공식을 선택합니다.",
        "value": 0, "default": 0,
        "options": {"0": "기본", "1": "RPG Maker 2000", "2": "RPG Maker 2003"},
    },
    "easyrpg_max_actor_hp": {
        "type": "int", "name": "아군 최대 HP", "group": "HP/SP",
        "description": "아군이 가질 수 있는 최대 HP입니다. -1은 엔진 기본값을 사용합니다.",
        "value": -1, "default": -1, "max": 2147483646,
    },
    "easyrpg_max_enemy_hp": {
        "type": "int", "name": "적 최대 HP", "group": "HP/SP",
        "description": "적이 가질 수 있는 최대 HP입니다.",
        "value": -1, "default": -1, "max": 2147483646,
    },
    "easyrpg_max_actor_sp": {
        "type": "int", "name": "아군 최대 MP", "group": "HP/SP",
        "description": "아군이 가질 수 있는 최대 MP입니다.",
        "value": -1, "default": -1, "max": 2147483646,
    },
    "easyrpg_max_enemy_sp": {
        "type": "int", "name": "적 최대 MP", "group": "HP/SP",
        "description": "적이 가질 수 있는 최대 MP입니다.",
        "value": -1, "default": -1, "max": 2147483646,
    },
    "easyrpg_max_damage": {
        "type": "int", "name": "최대 데미지", "group": "전투",
        "description": "공격으로 줄 수 있는 최대 데미지입니다.",
        "value": -1, "default": -1, "max": 2147483646,
    },
    "easyrpg_max_exp": {
        "type": "int", "name": "최대 경험치", "group": "능력치",
        "description": "캐릭터가 가질 수 있는 최대 경험치입니다.",
        "value": -1, "default": -1, "max": 2147483646,
    },
    "easyrpg_max_stat_base_value": {
        "type": "int", "name": "기본 능력치 최대값", "group": "능력치",
        "description": "기본 능력치의 최대값입니다.",
        "value": -1, "default": -1, "max": 2147483646,
    },
    "easyrpg_max_stat_battle_value": {
        "type": "int", "name": "전투 능력치 최대값", "group": "능력치",
        "description": "전투 중 적용되는 능력치 최대값입니다.",
        "value": -1, "default": -1, "max": 2147483646,
    },
    "easyrpg_variable_min_value": {
        "type": "int", "name": "변수 최소값", "group": "일반",
        "description": "게임 변수의 최소값입니다.",
        "value": 0, "default": 0, "max": 2147483646,
    },
    "easyrpg_variable_max_value": {
        "type": "int", "name": "변수 최대값", "group": "일반",
        "description": "게임 변수의 최대값입니다.",
        "value": 0, "default": 0, "max": 2147483646,
    },
    "easyrpg_use_rpg2k_battle_system": {
        "type": "bool", "name": "RPG2000 전투 시스템 사용", "group": "전투",
        "description": "RPG Maker 2003에서도 RPG Maker 2000 전투 시스템을 사용합니다.",
        "value": False, "default": False,
    },
    "easyrpg_battle_use_rpg2ke_strings": {
        "type": "bool", "name": "RPG2000 전투 용어 사용", "group": "전투",
        "description": "RPG2000 전투 시스템에서 RPG2kE 용어를 사용합니다.",
        "value": False, "default": False,
    },
    "easyrpg_use_rpg2k_battle_commands": {
        "type": "bool", "name": "RPG2000 전투 명령 사용", "group": "전투",
        "description": "RPG2000 방식의 전투 명령을 사용합니다.",
        "value": False, "default": False,
    },
    "easyrpg_max_savefiles": {
        "type": "int", "name": "최대 세이브 파일 수", "group": "일반",
        "description": "세이브 슬롯 개수입니다.",
        "value": 15, "default": 15, "max": 999,
    },
    "easyrpg_max_item_count": {
        "type": "int", "name": "기본 아이템 소지 한도", "group": "일반",
        "description": "아이템별 설정이 없을 때 적용되는 기본 소지 한도입니다.",
        "value": -1, "default": -1, "max": 255,
    },
    "easyrpg_default_actorai": {
        "type": "enum", "name": "기본 아군 AI(전체 설정)", "group": "AI",
        "description": "기본적으로 사용할 아군 AI입니다. 액터 탭에서 개별 설정한 값이 있으면 이 전체 설정보다 우선 적용됩니다.",
        "value": -1, "default": -1,
        "options": {"-1": "기본값", "0": "RPG_RT", "1": "RPG_RT+", "2": "ATTACK"},
    },
    "easyrpg_default_enemyai": {
        "type": "enum", "name": "기본 적 AI(전체 설정)", "group": "AI",
        "description": "기본적으로 사용할 적 AI입니다. 적 탭에서 개별 설정한 값이 있으면 이 전체 설정보다 우선 적용됩니다.",
        "value": -1, "default": -1,
        "options": {"-1": "기본값", "0": "RPG_RT", "1": "RPG_RT+"},
    },
    "easyrpg_battle_options": {
        "type": "list", "name": "전투 명령", "group": "전투",
        "description": "전투에서 사용할 명령과 순서를 지정합니다.",
        "value": [0, 1, 2], "default": [0, 1, 2],
        "options": {"0": "전투", "1": "자동전투", "2": "도망"},
    },
    "easyrpg_max_level": {
        "type": "int", "name": "최대 레벨", "group": "능력치",
        "description": "캐릭터가 도달할 수 있는 최대 레벨입니다. -1은 순정 기본값을 의미합니다.",
        "value": -1, "default": -1, "max": 255,
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
            log.warning(t("config.log_config_corrupted", path=os.path.basename(path), reason=e))
            try:
                os.replace(path, path + ".bak")
            except Exception as be:
                log.error(t("config.log_backup_fail", reason=be))
            messagebox.showwarning(
                t("config.title_config_recovered"),
                t("config.msg_config_corrupted", path=path, backup_name=f"{os.path.basename(path)}.bak")
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
        log.error(t("config.log_save_fail", path=path, reason=e))
        messagebox.showerror(t("common.title_save_fail"), t("config.msg_save_fail", path=path, reason=e))
        return False


def fix_invalid_variable_bounds(system_limits):
    """easyrpg_variable_min_value / easyrpg_variable_max_value는 -1을 지정하면
    게임 실행 중 잘못된 값으로 강제 종료되는 것이 확인되어, 이미 저장된 프로젝트에
    -1이 남아있다면 0으로 되돌립니다 (value뿐 아니라 "기본값 초기화" 버튼을 눌렀을 때
    다시 -1로 돌아가지 않도록 default도 함께 고칩니다). 실제로 뭔가 고쳤으면 True를 반환합니다."""
    changed = False
    for key in ("easyrpg_variable_min_value", "easyrpg_variable_max_value"):
        defn = system_limits.get(key)
        if not isinstance(defn, dict):
            continue
        if defn.get("value") == -1:
            defn["value"] = 0
            changed = True
        if defn.get("default") == -1:
            defn["default"] = 0
            changed = True
    return changed


# ------------------------------------------------------------------
# ConfigManager: 공통 설정 + 프로젝트(게임별) 설정 + 프로젝트(ldb) 선택
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
            missing.append(t("config.msg_missing_lcf2xml", dir=self.program_dir))
        if missing:
            messagebox.showerror(
                t("common.title_fail"),
                t("config.msg_missing_files", list="\n".join(missing))
            )
            return False
        return True

    # ---- 공통 설정 (프로그램 폴더의 config.json) ----
    def default_common_config(self):
        return {
            "last_game_dir": "",
            "recent_projects": [],
            "settings": {"theme": "dark", "language": "ko"},
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
        if fix_invalid_variable_bounds(self.common_config["system_limits"]):
            changed = True
        if changed:
            self.save_common_config()
        log.info(t("config.log_common_loaded"))

    def save_common_config(self):
        return write_json_safe(self.config_file, self.common_config)

    # ---- 프로젝트 선택: RPG_RT.ldb 파일을 직접 선택 ----
    def select_project_file(self):
        """RPG_RT.ldb 파일을 선택하게 하고, 선택된 파일의 폴더를 프로젝트로 인식합니다.
        폴더를 먼저 고르고 검증하던 예전 방식보다 실수(잘못된 폴더 선택)가 훨씬 줄어듭니다."""
        last_dir = self.common_config.get("last_game_dir", "")
        # os.getcwd()를 기본값으로 쓰면 실행 방식에 따라 C:\Windows\System32 같은
        # 예상치 못한 폴더가 나올 수 있어서, 마지막으로 연 폴더가 없으면 프로그램 자신의
        # 폴더(exe/py가 있는 위치)를 기준으로 시작합니다.
        initial = last_dir if last_dir and os.path.isdir(last_dir) else self.program_dir
        while True:
            file_path = filedialog.askopenfilename(
                title=t("config.dialog_select_ldb_title"),
                initialdir=initial,
                filetypes=[(t("config.filetype_ldb"), "RPG_RT.ldb"), (t("config.filetype_all"), "*.*")],
            )
            if not file_path:
                return False
            if os.path.basename(file_path).lower() != "rpg_rt.ldb":
                messagebox.showerror(
                    t("common.title_invalid"),
                    t("config.msg_invalid_ldb")
                )
                initial = os.path.dirname(file_path)
                continue
            self.set_game_folder(os.path.dirname(file_path))
            return True

    def set_game_folder(self, folder):
        self.game_dir = os.path.abspath(folder)
        self.ldb_file = os.path.join(self.game_dir, "RPG_RT.ldb")
        self.edb_file = os.path.join(self.game_dir, "RPG_RT.edb")
        self.ini_file = os.path.join(self.game_dir, "RPG_RT.ini")

        self.project_title, title_warning = get_project_title(self.game_dir)
        if title_warning:
            log.warning(title_warning)
            messagebox.showwarning(t("common.title_notice"), title_warning)

        self.project_dir = os.path.join(self.projects_dir, sanitize_folder_name(self.project_title))
        try:
            os.makedirs(self.project_dir, exist_ok=True)
        except Exception as e:
            log.error(t("config.msg_project_dir_fail", dir=self.project_dir, reason=e))
            messagebox.showerror(t("common.title_fail"), t("config.msg_project_dir_fail", dir=self.project_dir, reason=e))
        self.project_config_file = os.path.join(self.project_dir, "config.json")

        self.common_config["last_game_dir"] = self.game_dir
        recents = [r for r in self.common_config.get("recent_projects", []) if r.get("path") != self.game_dir]
        recents.insert(0, {"title": self.project_title, "path": self.game_dir})
        self.common_config["recent_projects"] = recents[:10]
        self.save_common_config()
        log.info(t("config.log_project_recognized", title=self.project_title))

    # ---- 프로젝트(게임별) 설정 ----
    def load_project_config(self):
        def factory():
            return {
                "system_limits": copy.deepcopy(self.common_config.get("system_limits", DEFAULT_SYSTEM_DEFS)),
                "items": [], "skills": [], "actors": [], "classes": [], "enemies": [], "terrains": [],
            }

        self.current_config = read_json_safe(self.project_config_file, factory)

        if "items" not in self.current_config: self.current_config["items"] = []
        if "skills" not in self.current_config: self.current_config["skills"] = []
        if "actors" not in self.current_config: self.current_config["actors"] = []
        if "classes" not in self.current_config: self.current_config["classes"] = []
        if "enemies" not in self.current_config: self.current_config["enemies"] = []
        if "terrains" not in self.current_config: self.current_config["terrains"] = []

        migrated = migrate_system_limits(self.current_config.get("system_limits", {}))
        merged = merge_system_defs(migrated, self.common_config.get("system_limits", DEFAULT_SYSTEM_DEFS))
        fix_invalid_variable_bounds(merged)
        self.current_config["system_limits"] = merged

        self.save_config()
        log.info(t("config.log_project_config_loaded"))

    def save_config(self):
        return write_json_safe(self.project_config_file, self.current_config)

    def find_sys_def(self, name):
        return self.current_config.get("system_limits", {}).get(name)

    # ---- 설정 불러오기: 다른 프로젝트(예: 이전 버전)의 값을 현재 프로젝트에 덮어쓰기 ----
    def list_other_projects(self):
        """projects_dir 아래의 다른 프로젝트 폴더들(현재 프로젝트 제외) 중 config.json이
        있는 것만 골라 반환합니다. [{"folder": 폴더명, "path": config.json 경로}, ...]
        게임을 버전업할 때(예: v1 -> v2) 예전 폴더의 설정을 새 폴더로 옮겨오는 용도입니다."""
        results = []
        if not os.path.isdir(self.projects_dir):
            return results
        current_folder = os.path.basename(self.project_dir) if self.project_dir else None
        for name in sorted(os.listdir(self.projects_dir)):
            if name == current_folder:
                continue
            folder_path = os.path.join(self.projects_dir, name)
            if not os.path.isdir(folder_path):
                continue
            config_path = os.path.join(folder_path, "config.json")
            if os.path.exists(config_path):
                results.append({"folder": name, "path": config_path})
        return results

    def import_settings_from(self, source_config_path):
        """다른 프로젝트의 config.json에서 아이템/스킬/액터/클래스/적/지형 설정 목록과
        시스템 옵션의 값(value)만 읽어와 현재 프로젝트에 덮어씁니다. 시스템 옵션은 현재
        프로젝트에 이미 존재하는 키에 한해서만 값을 옮기고(name/description/options 등
        나머지 메타데이터는 현재 스키마 것을 그대로 유지), 옮긴 뒤 곧바로 저장합니다.
        성공하면 {키: 옮겨진 개수} 형태의 요약 dict를, 파일을 읽지 못하면 None을 반환합니다."""
        try:
            with open(source_config_path, "r", encoding="utf-8") as f:
                source = json.load(f)
        except Exception as e:
            log.error(t("config.log_import_read_fail", path=source_config_path, reason=e))
            messagebox.showerror(t("common.title_fail"), t("config.msg_import_read_fail", reason=e))
            return None

        summary = {}
        for key in ("items", "skills", "actors", "classes", "enemies", "terrains"):
            values = source.get(key)
            if isinstance(values, list):
                self.current_config[key] = copy.deepcopy(values)
                summary[key] = len(values)

        src_limits = source.get("system_limits", {})
        if isinstance(src_limits, dict):
            cur_limits = self.current_config.setdefault("system_limits", {})
            applied = 0
            for name, src_defn in src_limits.items():
                cur_defn = cur_limits.get(name)
                if isinstance(cur_defn, dict) and isinstance(src_defn, dict) and "value" in src_defn:
                    cur_defn["value"] = copy.deepcopy(src_defn["value"])
                    applied += 1
            fix_invalid_variable_bounds(cur_limits)
            summary["system_limits"] = applied

        self.save_config()
        log.info(t("config.log_import_done", path=source_config_path, summary=summary))
        return summary
