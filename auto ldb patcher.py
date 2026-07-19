import os
import sys
import json
import re
import copy
import traceback
import subprocess
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


# ======================================================================
# 프로그램/경로 관련 헬퍼 함수
# ======================================================================
def get_program_dir():
    """프로그램(스크립트 또는 exe)이 위치한 폴더를 반환합니다."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def sanitize_folder_name(name):
    invalid = '<>:"/\\|?*'
    cleaned = "".join(c for c in name if c not in invalid).strip()
    return cleaned if cleaned else "untitled_project"


def get_project_title(game_dir):
    """게임 폴더의 RPG_RT.ini에서 Title 값을 읽어옵니다.
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

    m = re.search(r'^\s*Title\s*=\s*(.+?)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if not m or not m.group(1).strip():
        return fallback, "RPG_RT.ini에서 Title 값을 찾을 수 없어 폴더 이름을 프로젝트명으로 사용합니다."

    return m.group(1).strip(), None


def migrate_system_limits(raw):
    """구버전(dict 형태) system_limits를 신버전(list 형태) 스키마로 변환합니다."""
    if isinstance(raw, list):
        return copy.deepcopy(raw)
    if isinstance(raw, dict):
        migrated = []
        for key, info in raw.items():
            if isinstance(info, dict):
                val = info.get("value", -1)
                label = info.get("name", key)
                max_v = info.get("max", 999999999)
            else:
                val, label, max_v = info, key, 999999999
            default_v = 15 if key == "easyrpg_max_savefiles" else (99 if key == "easyrpg_max_item_count" else -1)
            migrated.append({"name": key, "label": label, "type": "int", "value": val, "default": default_v, "max": max_v})
        return migrated
    return []


def merge_system_defs(existing_list, template_list):
    """existing_list에 없는 항목을 template_list에서 채워 넣습니다 (새 EasyRPG 옵션 자동 반영)."""
    existing_names = {d.get("name") for d in existing_list}
    merged = list(existing_list)
    for tmpl in template_list:
        if tmpl.get("name") not in existing_names:
            merged.append(copy.deepcopy(tmpl))
    return merged


# ---- 다크 테마 색상 팔레트 ----
BG = "#1e1e1e"
BG2 = "#252526"
BG3 = "#2d2d30"
FG = "#e0e0e0"
FG_DIM = "#9a9a9a"
ACCENT = "#3c3f41"
ACCENT_HOVER = "#505354"
SELECT_BG = "#0a5a8a"
BORDER = "#454545"

# ---- 아이템 타입 코드 ----
ITEM_TYPE_NAMES = {
    0: "일반", 1: "무기", 2: "방패", 3: "갑옷", 4: "투구", 5: "악세사리",
    6: "회복약", 7: "스킬북", 8: "씨앗", 9: "특수", 10: "스위치",
}

TYPE_LABEL_MAP = {"int": "정수", "bool": "체크박스", "enum": "콤보박스", "list": "체크+순서"}

# ---- 시스템 옵션 기본 정의 (최초 설치 시 config.json 시드 데이터로 사용) ----
DEFAULT_SYSTEM_DEFS = [
    {"name": "easyrpg_max_savefiles", "label": "최대 세이브 파일 수", "type": "int",
     "value": 15, "default": 15, "max": 999},
    {"name": "easyrpg_max_item_count", "label": "기본 아이템 소지 한도", "type": "int",
     "value": 99, "default": 99, "max": 255},
    {"name": "easyrpg_max_level", "label": "최대 레벨", "type": "int",
     "value": -1, "default": -1, "max": 9999},
    {"name": "easyrpg_use_rpg2k_battle_commands", "label": "RPG2K 전투 명령어 사용", "type": "bool",
     "value": False, "default": False},
    {"name": "easyrpg_default_actorai", "label": "기본 아군 AI", "type": "enum",
     "value": -1, "default": -1,
     "options": [
         {"value": -1, "label": "기본값"},
         {"value": 0, "label": "RPG_RT (원작 엔진과 동일, 버그 포함)"},
         {"value": 1, "label": "RPG_RT+ (원작 기반 + AI 버그 수정)"},
         {"value": 2, "label": "ATTACK (일반 공격만 수행)"},
     ]},
    {"name": "easyrpg_default_enemyai", "label": "기본 적 AI", "type": "enum",
     "value": -1, "default": -1,
     "note": "ATTACK(2)은 적에게는 적용되지 않습니다.",
     "options": [
         {"value": -1, "label": "기본값"},
         {"value": 0, "label": "RPG_RT (원작 엔진과 동일, 버그 포함)"},
         {"value": 1, "label": "RPG_RT+ (원작 기반 + AI 버그 수정)"},
         {"value": 2, "label": "ATTACK (일반 공격만 수행)"},
     ]},
    {"name": "easyrpg_battle_options", "label": "전투 옵션", "type": "list",
     "value": [0, 1, 2], "default": [0, 1, 2],
     "options": [
         {"value": 0, "label": "Battle"},
         {"value": 1, "label": "Auto Battle"},
         {"value": 2, "label": "Escape"},
     ]},
]


class PureEdbEasyRpgPatcher:
    def __init__(self, root):
        self.root = root
        self.root.title("EasyRPG DB Editor (Dynamic External Plugin Version)")
        self.root.geometry("1080x780")
        self._init_ok = False

        self.program_dir = get_program_dir()
        self.lcf2xml_bin = os.path.join(self.program_dir, "lcf2xml.exe")
        self.config_file = os.path.join(self.program_dir, "config.json")
        self.projects_dir = os.path.join(self.program_dir, "projects")

        self.edb_master_items = {}
        self.edb_master_item_types = {}
        self.edb_master_skills = {}
        self.current_config = {"system_limits": [], "items": [], "skills": []}

        self.apply_dark_theme()
        self.root.withdraw()

        self.load_common_config()

        if not self.check_program_prerequisites():
            self.root.destroy()
            return

        if not self.select_game_folder():
            self.root.destroy()
            return

        self.root.deiconify()

        self.decompile_and_parse_edb_directly()
        self.load_project_config()
        self.create_widgets()
        self.refresh_edb_overlay()
        self._init_ok = True

    # ------------------------------------------------------------------
    # 사전 점검
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 게임 폴더 선택 / 프로젝트 결정
    # ------------------------------------------------------------------
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

    def change_game_folder(self):
        if self.select_game_folder():
            self.decompile_and_parse_edb_directly()
            self.load_project_config()
            self.update_ui_tables()
            self.refresh_edb_overlay()
            if hasattr(self, "project_label"):
                self.project_label.config(text=f"프로젝트: {self.project_title}   ({self.game_dir})")

    # ------------------------------------------------------------------
    # 공통 JSON 입출력 (공통 설정 / 프로젝트 설정 모두 재사용)
    # ------------------------------------------------------------------
    def read_json_safe(self, path, default_factory):
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
        self.write_json_safe(path, data)
        return data

    def write_json_safe(self, path, data):
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
    # 공통 설정 (프로그램 폴더의 config.json)
    # ------------------------------------------------------------------
    def default_common_config(self):
        return {
            "last_game_dir": "",
            "recent_projects": [],
            "settings": {"theme": "dark"},
            "system_limits": copy.deepcopy(DEFAULT_SYSTEM_DEFS),
        }

    def load_common_config(self):
        self.common_config = self.read_json_safe(self.config_file, self.default_common_config)
        changed = False
        for key, val in self.default_common_config().items():
            if key not in self.common_config:
                self.common_config[key] = val
                changed = True
        if not isinstance(self.common_config.get("system_limits"), list) or not self.common_config["system_limits"]:
            self.common_config["system_limits"] = copy.deepcopy(DEFAULT_SYSTEM_DEFS)
            changed = True
        if changed:
            self.save_common_config()

    def save_common_config(self):
        return self.write_json_safe(self.config_file, self.common_config)

    # ------------------------------------------------------------------
    # 프로젝트(게임별) 설정
    # ------------------------------------------------------------------
    def load_project_config(self):
        def factory():
            return {
                "system_limits": copy.deepcopy(self.common_config.get("system_limits", DEFAULT_SYSTEM_DEFS)),
                "items": [], "skills": [],
            }

        self.current_config = self.read_json_safe(self.project_config_file, factory)

        if "items" not in self.current_config: self.current_config["items"] = []
        if "skills" not in self.current_config: self.current_config["skills"] = []

        migrated = migrate_system_limits(self.current_config.get("system_limits", []))
        merged = merge_system_defs(migrated, self.common_config.get("system_limits", DEFAULT_SYSTEM_DEFS))
        self.current_config["system_limits"] = merged

        self.save_config()

    def save_config(self):
        return self.write_json_safe(self.project_config_file, self.current_config)

    def find_sys_def(self, name):
        return next((d for d in self.current_config.get("system_limits", []) if d.get("name") == name), None)

    # ------------------------------------------------------------------
    # 다크 테마
    # ------------------------------------------------------------------
    def apply_dark_theme(self):
        self.root.configure(bg=BG)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=BG, foreground=FG, fieldbackground=BG2,
                         bordercolor=BORDER, darkcolor=BG, lightcolor=BG)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("TButton", background=ACCENT, foreground=FG, padding=6, borderwidth=1)
        style.map("TButton",
                  background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)],
                  foreground=[("disabled", FG_DIM)])
        style.configure("TEntry", fieldbackground=BG2, foreground=FG, insertcolor=FG,
                         bordercolor=BORDER)
        style.map("TEntry", fieldbackground=[("readonly", BG2)])
        style.configure("TCombobox", fieldbackground=BG2, background=BG2, foreground=FG,
                         arrowcolor=FG, bordercolor=BORDER)
        style.map("TCombobox", fieldbackground=[("readonly", BG2)], foreground=[("readonly", FG)])
        style.configure("TNotebook", background=BG, bordercolor=BORDER)
        style.configure("TNotebook.Tab", background=ACCENT, foreground=FG, padding=(12, 6))
        style.map("TNotebook.Tab", background=[("selected", BG3)], foreground=[("selected", "#ffffff")])
        style.configure("Treeview", background=BG2, fieldbackground=BG2, foreground=FG,
                         bordercolor=BORDER, rowheight=24)
        style.configure("Treeview.Heading", background=ACCENT, foreground=FG, relief="flat")
        style.map("Treeview.Heading", background=[("active", ACCENT_HOVER)])
        style.map("Treeview", background=[("selected", SELECT_BG)], foreground=[("selected", "#ffffff")])
        style.configure("Vertical.TScrollbar", background=ACCENT, troughcolor=BG2,
                         bordercolor=BORDER, arrowcolor=FG, relief="flat")
        style.map("Vertical.TScrollbar", background=[("active", ACCENT_HOVER)])

    def attach_tree_scrollbar(self, tree, parent):
        vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="left", fill="y")

    def make_listbox_with_scroll(self, parent, height=6):
        frame = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(frame, height=height, bg=BG2, fg=FG,
                              selectbackground=SELECT_BG, selectforeground="#ffffff",
                              highlightthickness=0, relief="flat", activestyle="none",
                              yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return frame, listbox

    def make_checkbutton(self, parent, text, variable, command=None):
        return tk.Checkbutton(parent, text=text, variable=variable, command=command,
                               bg=BG, fg=FG, selectcolor=BG2, activebackground=BG,
                               activeforeground=FG, highlightthickness=0)

    # ------------------------------------------------------------------
    # lcf2xml 실행 (공통 래퍼 - 사용자 친화적 오류 메시지)
    # ------------------------------------------------------------------
    def run_lcf2xml(self, target_file):
        try:
            subprocess.run([self.lcf2xml_bin, target_file], check=True, shell=True, cwd=self.game_dir)
            return True
        except FileNotFoundError:
            messagebox.showerror("실패", "lcf2xml.exe 실행 파일을 찾을 수 없습니다.\n프로그램 폴더를 확인해 주세요.")
            return False
        except subprocess.CalledProcessError as e:
            messagebox.showerror("실패", f"lcf2xml 변환 중 오류가 발생했습니다. (종료 코드: {e.returncode})")
            return False
        except Exception as e:
            print("---- 상세 오류 ----"); traceback.print_exc()
            messagebox.showerror("실패", f"lcf2xml 실행 중 알 수 없는 오류가 발생했습니다.\n{e}")
            return False

    # ------------------------------------------------------------------
    # edb 파싱
    # ------------------------------------------------------------------
    def decompile_and_parse_edb_directly(self):
        if not os.path.exists(self.ldb_file): return
        print("[동기화] 최신 RPG_RT.edb 역변환 확보 중...")
        if not self.run_lcf2xml(self.ldb_file):
            return
        if not os.path.exists(self.edb_file):
            messagebox.showerror(
                "실패",
                "RPG_RT.edb 파일이 생성되지 않았습니다.\nlcf2xml 변환이 정상적으로 끝나지 않은 것 같습니다."
            )
            return

        print("[파싱] edb(XML) 내부에서 실시간으로 정보 색출 중...")
        try:
            with open(self.edb_file, "r", encoding="utf-8") as f:
                xml_text = f.read()
            self.edb_master_items.clear()
            self.edb_master_item_types.clear()
            self.edb_master_skills.clear()

            item_block_pattern = re.compile(r'<Item\s+id="(\d+)">(.*?)</Item>', re.DOTALL | re.IGNORECASE)
            for match in item_block_pattern.finditer(xml_text):
                iid, block = int(match.group(1)), match.group(2)
                name_m = re.search(r'<name>(.*?)</name>', block, re.DOTALL | re.IGNORECASE)
                type_m = re.search(r'<type>(.*?)</type>', block, re.DOTALL | re.IGNORECASE)
                self.edb_master_items[iid] = name_m.group(1) if name_m and name_m.group(1) else "이름 없음"
                if type_m and type_m.group(1).strip().lstrip("-").isdigit():
                    self.edb_master_item_types[iid] = int(type_m.group(1).strip())

            skill_block_pattern = re.compile(r'<Skill\s+id="(\d+)">(.*?)</Skill>', re.DOTALL | re.IGNORECASE)
            for match in skill_block_pattern.finditer(xml_text):
                sid, block = int(match.group(1)), match.group(2)
                name_m = re.search(r'<name>(.*?)</name>', block, re.DOTALL | re.IGNORECASE)
                self.edb_master_skills[sid] = name_m.group(1) if name_m and name_m.group(1) else "이름 없음"

            print(f"[동기화 완료] 아이템: {len(self.edb_master_items)}개, 스킬: {len(self.edb_master_skills)}개 매칭 성공.")
        except Exception as e:
            print("---- 상세 오류 ----"); traceback.print_exc()
            messagebox.showerror("실패", f"RPG_RT.edb 파일을 분석하는 중 오류가 발생했습니다.\n{e}")

    # ------------------------------------------------------------------
    # UI 구성
    # ------------------------------------------------------------------
    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")
        ttk.Button(top_frame, text="📥 edb로드", command=self.refresh_from_edb).pack(side="left", padx=5)
        ttk.Button(top_frame, text="🗂 게임 폴더 변경", command=self.change_game_folder).pack(side="left", padx=5)
        self.project_label = ttk.Label(
            top_frame, text=f"프로젝트: {self.project_title}   ({self.game_dir})", foreground=FG_DIM
        )
        self.project_label.pack(side="left", padx=15)
        ttk.Button(top_frame, text="💾 저장(ldb전환)", command=self.apply_final_patch).pack(side="right", padx=5)

        self.body_container = ttk.Frame(self.root)
        self.body_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.notebook = ttk.Notebook(self.body_container)
        self.notebook.place(relx=0, rely=0, relwidth=1, relheight=1)

        # 1. 아이템 탭
        item_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(item_frame, text="📦 [개별] 아이템 최대 소지량 조절")
        self.item_tree = ttk.Treeview(item_frame, columns=("ID", "이름", "타입", "최대수량"), show="headings", height=18)
        for col, txt in [("ID", "ID"), ("이름", "아이템 이름"), ("타입", "타입"), ("최대수량", "최대 수량")]: self.item_tree.heading(col, text=txt)
        self.item_tree.pack(fill="both", expand=True, side="left")
        self.attach_tree_scrollbar(self.item_tree, item_frame)

        self.item_tree.column("ID", width=60, anchor="center")
        self.item_tree.column("이름", width=280, anchor="w")
        self.item_tree.column("타입", width=90, anchor="center")
        self.item_tree.column("최대수량", width=120, anchor="center")
        self.item_tree.bind("<<TreeviewSelect>>", self.on_item_select)

        item_btn_frame = ttk.Frame(item_frame, padding=10)
        item_btn_frame.pack(fill="y", side="right")

        ttk.Label(item_btn_frame, text="이름 검색:").pack(anchor="w", pady=(0, 2))
        self.item_search_entry = ttk.Entry(item_btn_frame, width=25)
        self.item_search_entry.pack(anchor="w", pady=(0, 2))
        self.item_search_entry.bind("<KeyRelease>", self.on_item_search)
        item_search_frame, self.item_search_listbox = self.make_listbox_with_scroll(item_btn_frame, height=6)
        item_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.item_search_listbox.bind("<<ListboxSelect>>", self.on_item_search_select)

        ttk.Label(item_btn_frame, text="아이템 ID:").pack(anchor="w", pady=(0, 2))
        self.item_id_entry = ttk.Entry(item_btn_frame, width=25); self.item_id_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(item_btn_frame, text="최대 수량:").pack(anchor="w", pady=(0, 2))
        self.item_val_entry = ttk.Entry(item_btn_frame, width=25); self.item_val_entry.pack(anchor="w", pady=(0, 15))
        ttk.Button(item_btn_frame, text="➕ 추가/수정", command=self.add_item_rule).pack(fill="x", pady=3)
        ttk.Button(item_btn_frame, text="❌ 규칙 삭제", command=self.delete_item_rule).pack(fill="x", pady=3)

        ttk.Label(item_btn_frame, text="일괄 설정 (등록된 항목만)").pack(anchor="w", pady=(20, 4))
        ttk.Button(item_btn_frame, text="🗑️ 전체삭제", command=self.batch_clear_items).pack(fill="x", pady=2)
        ttk.Button(item_btn_frame, text="↩️ 기본값 (99)", command=lambda: self.batch_set_items(99)).pack(fill="x", pady=2)
        ttk.Button(item_btn_frame, text="⬆️ 최대값 (255)", command=lambda: self.batch_set_items(255)).pack(fill="x", pady=2)

        # 2. 스킬 탭
        skill_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(skill_frame, text="⚡ 스킬 크리티컬 & 기본 데미지 위력 조절")
        self.skill_tree = ttk.Treeview(skill_frame, columns=("ID", "이름", "크리", "위력", "공격력비율", "정신력비율"), show="headings", height=18)
        headings = [("ID", "ID"), ("이름", "스킬 이름"), ("크리", "크리티컬 (%)"), ("위력", "기본 위력"),
                    ("공격력비율", "공격력비율"), ("정신력비율", "정신력비율")]
        for col, txt in headings: self.skill_tree.heading(col, text=txt)
        self.skill_tree.pack(fill="both", expand=True, side="left")
        self.attach_tree_scrollbar(self.skill_tree, skill_frame)

        self.skill_tree.column("ID", width=50, anchor="center")
        self.skill_tree.column("이름", width=220, anchor="w")
        self.skill_tree.column("크리", width=90, anchor="center")
        self.skill_tree.column("위력", width=90, anchor="center")
        self.skill_tree.column("공격력비율", width=90, anchor="center")
        self.skill_tree.column("정신력비율", width=90, anchor="center")
        self.skill_tree.bind("<<TreeviewSelect>>", self.on_skill_select)

        skill_btn_frame = ttk.Frame(skill_frame, padding=10)
        skill_btn_frame.pack(fill="y", side="right")

        ttk.Label(skill_btn_frame, text="이름 검색:").pack(anchor="w", pady=(0, 2))
        self.skill_search_entry = ttk.Entry(skill_btn_frame, width=25)
        self.skill_search_entry.pack(anchor="w", pady=(0, 2))
        self.skill_search_entry.bind("<KeyRelease>", self.on_skill_search)
        skill_search_frame, self.skill_search_listbox = self.make_listbox_with_scroll(skill_btn_frame, height=6)
        skill_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.skill_search_listbox.bind("<<ListboxSelect>>", self.on_skill_search_select)

        ttk.Label(skill_btn_frame, text="스킬 ID:").pack(anchor="w", pady=(0, 2))
        self.skill_id_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_id_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="크리 확률:").pack(anchor="w", pady=(0, 2))
        self.skill_val_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_val_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="스킬 위력:").pack(anchor="w", pady=(0, 2))
        self.skill_dmg_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_dmg_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="공격력 비율 (physical_rate, 1=5%):").pack(anchor="w", pady=(0, 2))
        self.skill_phys_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_phys_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="정신력 비율 (magical_rate, 1=2.5%):").pack(anchor="w", pady=(0, 2))
        self.skill_mag_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_mag_entry.pack(anchor="w", pady=(0, 15))
        ttk.Button(skill_btn_frame, text="➕ 추가/수정", command=self.add_skill_rule).pack(fill="x", pady=3)
        ttk.Button(skill_btn_frame, text="❌ 규칙 삭제", command=self.delete_skill_rule).pack(fill="x", pady=3)

        ttk.Label(skill_btn_frame, text="일괄 설정 (등록된 항목만)").pack(anchor="w", pady=(20, 4))
        ttk.Button(skill_btn_frame, text="🗑️ 전체삭제", command=self.batch_clear_skills).pack(fill="x", pady=2)
        ttk.Button(skill_btn_frame, text="↩️ 크리티컬 초기화 (0)", command=self.batch_reset_skill_crit).pack(fill="x", pady=2)

        # 3. 시스템 탭 (타입 기반 동적 UI)
        sys_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(sys_frame, text="⚙️ 시스템 상한 제한 조절")
        self.sys_tree = ttk.Treeview(sys_frame, columns=("필드명", "이름", "타입", "현재값"), show="headings", height=18)
        for col, txt in [("필드명", "필드명"), ("이름", "옵션명"), ("타입", "타입"), ("현재값", "현재값")]: self.sys_tree.heading(col, text=txt)
        self.sys_tree.pack(fill="both", expand=True, side="left")
        self.attach_tree_scrollbar(self.sys_tree, sys_frame)

        self.sys_tree.column("필드명", width=220, anchor="w")
        self.sys_tree.column("이름", width=170, anchor="w")
        self.sys_tree.column("타입", width=90, anchor="center")
        self.sys_tree.column("현재값", width=160, anchor="w")
        self.sys_tree.bind("<<TreeviewSelect>>", self.on_sys_select)

        sys_side_frame = ttk.Frame(sys_frame, padding=10)
        sys_side_frame.pack(fill="y", side="right")
        self.sys_detail_frame = ttk.Frame(sys_side_frame, width=260)
        self.sys_detail_frame.pack(fill="x", anchor="n")
        ttk.Label(self.sys_detail_frame, text="왼쪽 목록에서 항목을 선택하세요.", foreground=FG_DIM,
                  wraplength=240).pack(anchor="w")
        ttk.Button(sys_side_frame, text="🔄 모든 항목 기본값으로 초기화", command=self.reset_sys_limits).pack(fill="x", pady=(30, 3))

        # 오버레이 (edb 없음 안내)
        self.overlay = tk.Frame(self.body_container, bg=BG)
        overlay_inner = tk.Frame(self.overlay, bg=BG)
        overlay_inner.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(overlay_inner, text="⚠", font=("Segoe UI", 40), bg=BG, fg="#e0b400").pack(pady=(0, 10))
        tk.Label(overlay_inner, text="RPG_RT.edb 파일을 찾을 수 없습니다.",
                 font=("Segoe UI", 13, "bold"), bg=BG, fg=FG).pack()
        tk.Label(overlay_inner, text="edb로드 버튼을 눌러주세요.",
                 font=("Segoe UI", 11), bg=BG, fg=FG_DIM).pack(pady=(2, 16))
        ttk.Button(overlay_inner, text="📥 edb로드", command=self.refresh_from_edb).pack()

        self.update_ui_tables()

    def refresh_edb_overlay(self):
        if not hasattr(self, "overlay"):
            return
        if os.path.exists(self.edb_file):
            self.overlay.place_forget()
        else:
            self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.overlay.lift()

    # ------------------------------------------------------------------
    # 테이블 갱신
    # ------------------------------------------------------------------
    def update_ui_tables(self):
        for item in self.item_tree.get_children(): self.item_tree.delete(item)
        for it in self.current_config.get("items", []):
            iid = it["id"]
            name = self.edb_master_items.get(iid) or "⚠️ 알만툴 DB에 없음"
            type_code = self.edb_master_item_types.get(iid)
            type_name = ITEM_TYPE_NAMES.get(type_code, "-") if type_code is not None else "-"
            display_count = it["easyrpg_max_count"] if it["easyrpg_max_count"] != -1 else "순정 제한 유지"
            self.item_tree.insert("", "end", values=(iid, name, type_name, display_count))

        for skill in self.skill_tree.get_children(): self.skill_tree.delete(skill)
        for sk in self.current_config.get("skills", []):
            sid = sk["id"]
            name = self.edb_master_skills.get(sid) or "⚠️ 알만툴 DB에 없음"
            crit = "순정 유지" if sk.get("easyrpg_critical_hit_chance") == "keep" else sk.get("easyrpg_critical_hit_chance")
            dmg = "순정 유지" if sk.get("rating") == "keep" else sk.get("rating")
            phys = "순정 유지" if sk.get("physical_rate", "keep") == "keep" else sk.get("physical_rate")
            mag = "순정 유지" if sk.get("magical_rate", "keep") == "keep" else sk.get("magical_rate")
            self.skill_tree.insert("", "end", values=(sid, name, crit, dmg, phys, mag))

        for sys_item in self.sys_tree.get_children(): self.sys_tree.delete(sys_item)
        for defn in self.current_config.get("system_limits", []):
            if defn.get("name") == "easyrpg_max_item_count":
                continue
            self.sys_tree.insert("", "end", values=(
                defn.get("name"), defn.get("label", defn.get("name")),
                TYPE_LABEL_MAP.get(defn.get("type", "int"), defn.get("type")),
                self.format_sys_value(defn),
            ))

    def format_sys_value(self, defn):
        t = defn.get("type", "int")
        val = defn.get("value")
        if t == "bool":
            return "사용" if val else "미사용"
        if t == "enum":
            opt = next((o for o in defn.get("options", []) if o.get("value") == val), None)
            return f'{val} ({opt["label"]})' if opt else str(val)
        if t == "list":
            label_map = {o.get("value"): o.get("label") for o in defn.get("options", [])}
            return " → ".join(label_map.get(v, str(v)) for v in (val or [])) or "(없음)"
        return "순정 한계 (-1)" if val == -1 else f"{val:,}"

    # ------------------------------------------------------------------
    # 선택 시 입력창 즉시 반영 (아이템 / 스킬)
    # ------------------------------------------------------------------
    def on_item_select(self, event):
        selected = self.item_tree.selection()
        if not selected: return
        vals = self.item_tree.item(selected)['values']
        if not vals: return
        iid = int(vals[0])
        it = next((i for i in self.current_config["items"] if i["id"] == iid), None)
        if it:
            self.item_id_entry.delete(0, tk.END); self.item_id_entry.insert(0, str(it["id"]))
            self.item_val_entry.delete(0, tk.END)
            if it["easyrpg_max_count"] != -1:
                self.item_val_entry.insert(0, str(it["easyrpg_max_count"]))

    def on_skill_select(self, event):
        selected = self.skill_tree.selection()
        if not selected: return
        vals = self.skill_tree.item(selected)['values']
        if not vals: return
        sid = int(vals[0])
        sk = next((s for s in self.current_config["skills"] if s["id"] == sid), None)
        if sk:
            self.skill_id_entry.delete(0, tk.END); self.skill_id_entry.insert(0, str(sk["id"]))
            self.skill_val_entry.delete(0, tk.END)
            if sk.get("easyrpg_critical_hit_chance") != "keep":
                self.skill_val_entry.insert(0, str(sk.get("easyrpg_critical_hit_chance")))
            self.skill_dmg_entry.delete(0, tk.END)
            if sk.get("rating") != "keep":
                self.skill_dmg_entry.insert(0, str(sk.get("rating")))
            self.skill_phys_entry.delete(0, tk.END)
            if sk.get("physical_rate", "keep") != "keep":
                self.skill_phys_entry.insert(0, str(sk.get("physical_rate")))
            self.skill_mag_entry.delete(0, tk.END)
            if sk.get("magical_rate", "keep") != "keep":
                self.skill_mag_entry.insert(0, str(sk.get("magical_rate")))

    # ------------------------------------------------------------------
    # 시스템 탭 - 타입별 동적 편집 패널
    # ------------------------------------------------------------------
    def on_sys_select(self, event):
        selected = self.sys_tree.selection()
        if not selected: return
        vals = self.sys_tree.item(selected)['values']
        if not vals: return
        defn = self.find_sys_def(str(vals[0]))
        if defn:
            self.render_sys_detail(defn)

    def render_sys_detail(self, defn):
        for w in self.sys_detail_frame.winfo_children():
            w.destroy()
        self._current_sys_def = defn
        t = defn.get("type", "int")

        ttk.Label(self.sys_detail_frame, text=defn.get("label", defn.get("name")),
                  font=("Segoe UI", 11, "bold"), wraplength=240).pack(anchor="w", pady=(0, 2))
        ttk.Label(self.sys_detail_frame, text=defn.get("name"), foreground=FG_DIM).pack(anchor="w", pady=(0, 8))
        if defn.get("note"):
            ttk.Label(self.sys_detail_frame, text=defn["note"], foreground="#e0b400",
                      wraplength=240).pack(anchor="w", pady=(0, 8))

        if t == "int":
            ttk.Label(self.sys_detail_frame, text="값 (-1 = 순정 기본):").pack(anchor="w")
            self.sys_int_entry = ttk.Entry(self.sys_detail_frame, width=22)
            self.sys_int_entry.pack(anchor="w", pady=(0, 10))
            self.sys_int_entry.insert(0, str(defn.get("value", -1)))
            ttk.Button(self.sys_detail_frame, text="✏️ 적용", command=self.apply_sys_int).pack(fill="x")

        elif t == "bool":
            self.sys_bool_var = tk.BooleanVar(value=bool(defn.get("value", False)))
            self.make_checkbutton(self.sys_detail_frame, "사용함", self.sys_bool_var,
                                   command=self.apply_sys_bool).pack(anchor="w")

        elif t == "enum":
            options = defn.get("options", [])
            labels = [f'{o["value"]} : {o["label"]}' for o in options]
            self.sys_enum_var = tk.StringVar()
            current_val = defn.get("value", -1)
            cur_label = next((lbl for o, lbl in zip(options, labels) if o["value"] == current_val),
                              labels[0] if labels else "")
            self.sys_enum_var.set(cur_label)
            combo = ttk.Combobox(self.sys_detail_frame, textvariable=self.sys_enum_var,
                                  values=labels, state="readonly", width=32)
            combo.pack(anchor="w", pady=(0, 10))
            ttk.Button(self.sys_detail_frame, text="✏️ 적용", command=self.apply_sys_enum).pack(fill="x")

        elif t == "list":
            options = defn.get("options", [])
            current_vals = defn.get("value", []) or []
            self.sys_list_vars = {}
            self.sys_list_order = [v for v in current_vals]

            for o in options:
                var = tk.BooleanVar(value=o["value"] in current_vals)
                self.sys_list_vars[o["value"]] = var
                self.make_checkbutton(self.sys_detail_frame, o["label"], var,
                                       command=self.refresh_sys_list_order).pack(anchor="w")

            ttk.Label(self.sys_detail_frame, text="적용 순서:").pack(anchor="w", pady=(10, 2))
            list_frame, self.sys_list_order_box = self.make_listbox_with_scroll(self.sys_detail_frame, height=5)
            list_frame.pack(anchor="w", fill="x", pady=(0, 6))

            btn_row = ttk.Frame(self.sys_detail_frame); btn_row.pack(fill="x")
            ttk.Button(btn_row, text="▲ 위로", command=lambda: self.move_sys_list_item(-1)).pack(side="left", expand=True, fill="x")
            ttk.Button(btn_row, text="▼ 아래로", command=lambda: self.move_sys_list_item(1)).pack(side="left", expand=True, fill="x")
            ttk.Button(self.sys_detail_frame, text="✏️ 적용", command=self.apply_sys_list).pack(fill="x", pady=(8, 0))

            self.refresh_sys_list_order()

    def apply_sys_int(self):
        try:
            val = int(self.sys_int_entry.get().strip())
        except ValueError:
            messagebox.showerror("에러", "정수만 입력해 주세요.")
            return
        max_limit = self._current_sys_def.get("max")
        if max_limit is not None and val > max_limit:
            val = max_limit
            messagebox.showwarning("상한 제한", f"오버플로우 방지를 위해 최대값 {max_limit:,}으로 자동 제한됩니다.")
        if val < -1: val = -1
        self._current_sys_def["value"] = val
        self.save_config()
        self.update_ui_tables()
        messagebox.showinfo("적용됨", f"[{self._current_sys_def.get('label')}] 값이 저장되었습니다.")

    def apply_sys_bool(self):
        self._current_sys_def["value"] = bool(self.sys_bool_var.get())
        self.save_config()
        self.update_ui_tables()

    def apply_sys_enum(self):
        sel = self.sys_enum_var.get()
        try:
            val = int(sel.split(":")[0].strip())
        except Exception:
            messagebox.showerror("에러", "값을 선택해 주세요.")
            return
        self._current_sys_def["value"] = val
        self.save_config()
        self.update_ui_tables()
        messagebox.showinfo("적용됨", f"[{self._current_sys_def.get('label')}] 값이 저장되었습니다.")

    def refresh_sys_list_order(self):
        checked = [v for v, var in self.sys_list_vars.items() if var.get()]
        new_order = [v for v in self.sys_list_order if v in checked]
        for v in checked:
            if v not in new_order:
                new_order.append(v)
        self.sys_list_order = new_order
        self.redraw_sys_list_order_box()

    def redraw_sys_list_order_box(self):
        self.sys_list_order_box.delete(0, tk.END)
        label_map = {o.get("value"): o.get("label") for o in self._current_sys_def.get("options", [])}
        for v in self.sys_list_order:
            self.sys_list_order_box.insert(tk.END, label_map.get(v, str(v)))

    def move_sys_list_item(self, direction):
        sel = self.sys_list_order_box.curselection()
        if not sel: return
        idx = sel[0]
        new_idx = idx + direction
        if 0 <= new_idx < len(self.sys_list_order):
            self.sys_list_order[idx], self.sys_list_order[new_idx] = self.sys_list_order[new_idx], self.sys_list_order[idx]
            self.redraw_sys_list_order_box()
            self.sys_list_order_box.selection_set(new_idx)

    def apply_sys_list(self):
        self._current_sys_def["value"] = list(self.sys_list_order)
        self.save_config()
        self.update_ui_tables()
        messagebox.showinfo("적용됨", f"[{self._current_sys_def.get('label')}] 값이 저장되었습니다.")

    def reset_sys_limits(self):
        if not messagebox.askyesno("전체 초기화", "모든 시스템 항목을 기본값으로 되돌리시겠습니까?"): return
        for defn in self.current_config.get("system_limits", []):
            if defn.get("name") == "easyrpg_max_item_count":
                continue
            if "default" in defn:
                defn["value"] = copy.deepcopy(defn["default"])
        self.save_config()
        self.update_ui_tables()
        for w in self.sys_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.sys_detail_frame, text="왼쪽 목록에서 항목을 선택하세요.", foreground=FG_DIM,
                  wraplength=240).pack(anchor="w")
        messagebox.showinfo("초기화 완료", "모든 시스템 항목이 기본값으로 복구되었습니다.")

    # ------------------------------------------------------------------
    # 이름 검색 (드롭다운)
    # ------------------------------------------------------------------
    def on_item_search(self, event):
        query = self.item_search_entry.get().strip()
        self.item_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(iid, name) for iid, name in sorted(self.edb_master_items.items()) if query in name]
        for iid, name in matches[:20]:
            self.item_search_listbox.insert(tk.END, f"{iid} - {name}")

    def on_item_search_select(self, event):
        sel = self.item_search_listbox.curselection()
        if not sel: return
        text = self.item_search_listbox.get(sel[0])
        iid = text.split(" - ", 1)[0]
        self.item_id_entry.delete(0, tk.END); self.item_id_entry.insert(0, iid)
        self.item_search_entry.delete(0, tk.END)
        self.item_search_listbox.delete(0, tk.END)

    def on_skill_search(self, event):
        query = self.skill_search_entry.get().strip()
        self.skill_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(sid, name) for sid, name in sorted(self.edb_master_skills.items()) if query in name]
        for sid, name in matches[:20]:
            self.skill_search_listbox.insert(tk.END, f"{sid} - {name}")

    def on_skill_search_select(self, event):
        sel = self.skill_search_listbox.curselection()
        if not sel: return
        text = self.skill_search_listbox.get(sel[0])
        sid = text.split(" - ", 1)[0]
        self.skill_id_entry.delete(0, tk.END); self.skill_id_entry.insert(0, sid)
        self.skill_search_entry.delete(0, tk.END)
        self.skill_search_listbox.delete(0, tk.END)

    # ------------------------------------------------------------------
    # edb 재동기화
    # ------------------------------------------------------------------
    def refresh_from_edb(self):
        self.decompile_and_parse_edb_directly()
        self.update_ui_tables()
        self.refresh_edb_overlay()
        if os.path.exists(self.edb_file):
            messagebox.showinfo("완료", "순정 edb에서 개체 이름들을 실시간 동기화했습니다!")

    # ------------------------------------------------------------------
    # 아이템 규칙
    # ------------------------------------------------------------------
    def add_item_rule(self):
        try:
            iid = int(self.item_id_entry.get().strip())
            val_input = self.item_val_entry.get().strip()
            val = int(val_input) if val_input else -1
            if val > 255:
                val = 255
                messagebox.showwarning("수량 제한", "엔진 세이브 오동작 방지를 위해 개별 아이템 한도는 255개로 자동 한정됩니다.")
            if iid not in self.edb_master_items:
                if not messagebox.askyesno("경고", "순정 아이템에 없습니다. 진행할까요?"): return
            self.current_config["items"] = [i for i in self.current_config["items"] if i["id"] != iid]
            self.current_config["items"].append({"id": iid, "easyrpg_max_count": val})
            self.save_config()
            self.update_ui_tables()
        except ValueError: messagebox.showerror("에러", "ID와 수치는 정수 숫자로 입력해 주세요.")

    def delete_item_rule(self):
        sel = self.item_tree.selection()
        if not sel: return
        item_vals = self.item_tree.item(sel)['values']
        iid = int(item_vals[0])
        self.current_config["items"] = [i for i in self.current_config["items"] if i["id"] != iid]
        self.save_config()
        self.update_ui_tables()

    def batch_clear_items(self):
        if not self.current_config["items"]:
            messagebox.showwarning("경고", "리스트에 등록된 아이템이 없습니다.")
            return
        if not messagebox.askyesno("일괄 삭제", "등록된 모든 아이템 규칙을 삭제하시겠습니까?"): return
        self.current_config["items"] = []
        self.save_config()
        self.update_ui_tables()

    def batch_set_items(self, value):
        if not self.current_config["items"]:
            messagebox.showwarning("경고", "리스트에 등록된 아이템이 없습니다.")
            return
        for it in self.current_config["items"]:
            it["easyrpg_max_count"] = value
        self.save_config()
        self.update_ui_tables()
        messagebox.showinfo("완료", f"등록된 아이템 {len(self.current_config['items'])}개의 최대 수량을 {value}(으)로 일괄 설정했습니다.")

    # ------------------------------------------------------------------
    # 스킬 규칙
    # ------------------------------------------------------------------
    def add_skill_rule(self):
        try:
            sid = int(self.skill_id_entry.get().strip())
            c_input = self.skill_val_entry.get().strip()
            d_input = self.skill_dmg_entry.get().strip()
            p_input = self.skill_phys_entry.get().strip()
            m_input = self.skill_mag_entry.get().strip()
            crit_val = int(c_input) if c_input else "keep"
            dmg_val = int(d_input) if d_input else "keep"
            phys_val = int(p_input) if p_input else "keep"
            mag_val = int(m_input) if m_input else "keep"
            if sid not in self.edb_master_skills:
                if not messagebox.askyesno("경고", "순정 스킬에 없습니다. 진행할까요?"): return
            self.current_config["skills"] = [s for s in self.current_config["skills"] if s["id"] != sid]
            self.current_config["skills"].append({
                "id": sid, "easyrpg_critical_hit_chance": crit_val, "rating": dmg_val,
                "physical_rate": phys_val, "magical_rate": mag_val,
            })
            self.save_config()
            self.update_ui_tables()
        except ValueError: messagebox.showerror("에러", "ID와 수치들은 숫자로 입력해 주세요.")

    def delete_skill_rule(self):
        sel = self.skill_tree.selection()
        if not sel: return
        skill_vals = self.skill_tree.item(sel)['values']
        sid = int(skill_vals[0])
        self.current_config["skills"] = [s for s in self.current_config["skills"] if s["id"] != sid]
        self.save_config()
        self.update_ui_tables()

    def batch_clear_skills(self):
        if not self.current_config["skills"]:
            messagebox.showwarning("경고", "리스트에 등록된 스킬이 없습니다.")
            return
        if not messagebox.askyesno("일괄 삭제", "등록된 모든 스킬 규칙을 삭제하시겠습니까?"): return
        self.current_config["skills"] = []
        self.save_config()
        self.update_ui_tables()

    def batch_reset_skill_crit(self):
        if not self.current_config["skills"]:
            messagebox.showwarning("경고", "리스트에 등록된 스킬이 없습니다.")
            return
        for sk in self.current_config["skills"]:
            sk["easyrpg_critical_hit_chance"] = 0
        self.save_config()
        self.update_ui_tables()
        messagebox.showinfo("완료", f"등록된 스킬 {len(self.current_config['skills'])}개의 크리티컬 확률을 0으로 초기화했습니다.")

    # ------------------------------------------------------------------
    # 최종 패치 적용 (edb -> ldb)
    # ------------------------------------------------------------------
    def apply_final_patch(self):
        if not os.path.exists(self.edb_file):
            messagebox.showerror("실패", "RPG_RT.edb 파일이 없습니다. 먼저 'edb로드' 버튼을 눌러주세요.")
            return

        try:
            tree = ET.parse(self.edb_file)
            root = tree.getroot()
        except Exception as e:
            print("---- 상세 오류 ----"); traceback.print_exc()
            messagebox.showerror("실패", f"RPG_RT.edb 파일을 읽는 중 오류가 발생했습니다.\n파일이 손상되었을 수 있습니다.\n{e}")
            return

        _container = root.find(".//system")
        system_container = _container if _container is not None else root.find(".//System")
        if system_container is not None:
            _node = system_container.find("System")
            actual_system_node = _node if _node is not None else system_container.find("system")
            if actual_system_node is not None:
                for defn in self.current_config.get("system_limits", []):
                    key = defn.get("name")
                    if not key: continue
                    t = defn.get("type", "int")
                    val = defn.get("value")
                    if t == "bool":
                        text_val = "1" if val else "0"
                    elif t == "list":
                        text_val = ",".join(str(v) for v in (val or []))
                    else:
                        text_val = str(val)
                    tag = actual_system_node.find(key)
                    if tag is not None: tag.text = text_val
                    else: ET.SubElement(actual_system_node, key).text = text_val
                print(" -> 시스템 옵션 한계 해제 완료.")

        try:
            for el in root.iter():
                t_low = el.tag.lower()
                if t_low == "items" or t_low == "item_container":
                    for it in self.current_config.get("items", []):
                        for item_node in el.findall("Item") + el.findall("item"):
                            nid = item_node.get("id") or (item_node.find("id").text if item_node.find("id") is not None else None)
                            if nid and int(nid) == it["id"]:
                                tag = item_node.find("easyrpg_max_count")
                                if tag is not None: tag.text = str(it["easyrpg_max_count"])
                                else: ET.SubElement(item_node, "easyrpg_max_count").text = str(it["easyrpg_max_count"])
                if t_low == "skills" or t_low == "skills_container" or t_low == "skill_container":
                    for sk in self.current_config.get("skills", []):
                        for skill_node in el.findall("Skill") + el.findall("skill"):
                            nid = skill_node.get("id") or (skill_node.find("id").text if skill_node.find("id") is not None else None)
                            if nid and int(nid) == sk["id"]:
                                if sk.get("easyrpg_critical_hit_chance") != "keep":
                                    crit_tag = skill_node.find("easyrpg_critical_hit_chance")
                                    if crit_tag is not None: crit_tag.text = str(sk["easyrpg_critical_hit_chance"])
                                    else: ET.SubElement(skill_node, "easyrpg_critical_hit_chance").text = str(sk["easyrpg_critical_hit_chance"])
                                if sk.get("rating") != "keep":
                                    r_tag = skill_node.find("rating")
                                    if r_tag is not None: r_tag.text = str(sk["rating"])
                                    else: ET.SubElement(skill_node, "rating").text = str(sk["rating"])
                                if sk.get("physical_rate", "keep") != "keep":
                                    p_tag = skill_node.find("physical_rate")
                                    if p_tag is not None: p_tag.text = str(sk["physical_rate"])
                                    else: ET.SubElement(skill_node, "physical_rate").text = str(sk["physical_rate"])
                                if sk.get("magical_rate", "keep") != "keep":
                                    m_tag = skill_node.find("magical_rate")
                                    if m_tag is not None: m_tag.text = str(sk["magical_rate"])
                                    else: ET.SubElement(skill_node, "magical_rate").text = str(sk["magical_rate"])
        except Exception as e:
            print("---- 상세 오류 ----"); traceback.print_exc()
            messagebox.showerror("실패", f"아이템/스킬 값을 적용하는 중 오류가 발생했습니다.\n{e}")
            return

        try:
            tree.write(self.edb_file, encoding="utf-8", xml_declaration=True)
        except Exception as e:
            print("---- 상세 오류 ----"); traceback.print_exc()
            messagebox.showerror("실패", f"RPG_RT.edb 파일 저장 중 오류가 발생했습니다.\n{e}")
            return

        if not self.run_lcf2xml(self.edb_file):
            return

        if not os.path.exists(self.ldb_file):
            messagebox.showerror("실패", "RPG_RT.ldb 파일이 생성되지 않았습니다. lcf2xml 변환을 다시 확인해 주세요.")
            return

        if os.path.exists(self.edb_file):
            try:
                os.remove(self.edb_file)
            except Exception as e:
                print(f"edb 삭제 실패: {e}")
                messagebox.showwarning("알림", f"패치는 완료되었지만 RPG_RT.edb 삭제에는 실패했습니다.\n(사유: {e})\n다음 'edb로드' 시 자동으로 새로 갱신됩니다.")

        self.refresh_edb_overlay()
        messagebox.showinfo("대성공", "전역 한계 해제 및 스킬/아이템 개조 패치가 완료되었습니다!\nRPG_RT.edb는 정리되었습니다. 다시 수정하려면 'edb로드'를 눌러주세요.")


if __name__ == "__main__":
    root = tk.Tk()
    app = PureEdbEasyRpgPatcher(root)
    if getattr(app, "_init_ok", False):
        root.mainloop()
