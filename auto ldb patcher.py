"""
auto ldb patcher.py
프로그램 진입점 (메인 파일).

이 파일이 하는 일은 다음뿐입니다:
  1. 프로그램 시작 (사전 점검 + 게임 폴더 선택)
  2. 공통 설정 로드 (core.config.ConfigManager)
  3. 메인 윈도우 생성
  4. 각 탭 로드 (tabs/*.py)
  5. 저장(edb→ldb 패치) 처리 위임 (core.lcf)

새 탭을 추가하려면 tabs/ 아래에 파일 하나만 만들고,
아래 TAB_CLASSES 목록에 한 줄만 추가하면 됩니다.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk

# 이 파일과 같은 폴더를 import 경로에 추가 (core/, tabs/ 패키지를 찾기 위함)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.utils import get_program_dir
from core.theme import BG, FG, FG_DIM, apply_dark_theme
from core.config import ConfigManager
from core import lcf

from tabs.item_tab import ItemTab
from tabs.skill_tab import SkillTab
from tabs.system_tab import SystemTab

# 새 탭은 여기에 한 줄만 추가하면 자동으로 로드됩니다.
TAB_CLASSES = [ItemTab, SkillTab, SystemTab]


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("EasyRPG DB Editor (Dynamic External Plugin Version)")
        self.root.geometry("1080x780")
        self._init_ok = False

        self.cfg = ConfigManager(get_program_dir())
        self.edb_master_items = {}
        self.edb_master_item_types = {}
        self.edb_master_skills = {}
        self.tabs = []

        apply_dark_theme(self.root)
        self.root.withdraw()

        self.cfg.load_common_config()

        if not self.cfg.check_program_prerequisites():
            self.root.destroy()
            return

        if not self.cfg.select_game_folder():
            self.root.destroy()
            return

        self.root.deiconify()

        self.sync_edb_master_data()
        self.cfg.load_project_config()
        self.create_widgets()
        self.refresh_edb_overlay()
        self._init_ok = True

    # ------------------------------------------------------------------
    # edb 동기화 (core.lcf 위임)
    # ------------------------------------------------------------------
    def sync_edb_master_data(self):
        items, item_types, skills = lcf.decompile_and_parse_edb_directly(self.cfg)
        if items is not None:
            self.edb_master_items = items
            self.edb_master_item_types = item_types
            self.edb_master_skills = skills

    def refresh_from_edb(self):
        self.sync_edb_master_data()
        self.refresh_all_tabs()
        self.refresh_edb_overlay()
        if os.path.exists(self.cfg.edb_file):
            from tkinter import messagebox
            messagebox.showinfo("완료", "순정 edb에서 개체 이름들을 실시간 동기화했습니다!")

    def change_game_folder(self):
        if self.cfg.select_game_folder():
            self.sync_edb_master_data()
            self.cfg.load_project_config()
            self.refresh_all_tabs()
            self.refresh_edb_overlay()
            if hasattr(self, "project_label"):
                self.project_label.config(text=f"프로젝트: {self.cfg.project_title}   ({self.cfg.game_dir})")

    def apply_final_patch(self):
        if lcf.apply_final_patch(self.cfg):
            self.refresh_edb_overlay()

    # ------------------------------------------------------------------
    # UI 구성
    # ------------------------------------------------------------------
    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")
        ttk.Button(top_frame, text="📥 edb로드", command=self.refresh_from_edb).pack(side="left", padx=5)
        ttk.Button(top_frame, text="🗂 게임 폴더 변경", command=self.change_game_folder).pack(side="left", padx=5)
        self.project_label = ttk.Label(
            top_frame, text=f"프로젝트: {self.cfg.project_title}   ({self.cfg.game_dir})", foreground=FG_DIM
        )
        self.project_label.pack(side="left", padx=15)
        ttk.Button(top_frame, text="💾 저장(ldb전환)", command=self.apply_final_patch).pack(side="right", padx=5)

        self.body_container = ttk.Frame(self.root)
        self.body_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.notebook = ttk.Notebook(self.body_container)
        self.notebook.place(relx=0, rely=0, relwidth=1, relheight=1)

        # 탭 로드 (TAB_CLASSES 목록 순서대로)
        for tab_cls in TAB_CLASSES:
            tab = tab_cls(self)
            tab.build(self.notebook)
            self.tabs.append(tab)

        # 오버레이 (edb 없음 안내) - 노트북과 같은 영역에 겹쳐서 표시
        self.overlay = tk.Frame(self.body_container, bg=BG)
        overlay_inner = tk.Frame(self.overlay, bg=BG)
        overlay_inner.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(overlay_inner, text="⚠", font=("Segoe UI", 40), bg=BG, fg="#e0b400").pack(pady=(0, 10))
        tk.Label(overlay_inner, text="RPG_RT.edb 파일을 찾을 수 없습니다.",
                 font=("Segoe UI", 13, "bold"), bg=BG, fg=FG).pack()
        tk.Label(overlay_inner, text="edb로드 버튼을 눌러주세요.",
                 font=("Segoe UI", 11), bg=BG, fg=FG_DIM).pack(pady=(2, 16))
        ttk.Button(overlay_inner, text="📥 edb로드", command=self.refresh_from_edb).pack()

        self.refresh_all_tabs()

    def refresh_edb_overlay(self):
        if not hasattr(self, "overlay"):
            return
        if os.path.exists(self.cfg.edb_file):
            self.overlay.place_forget()
        else:
            self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.overlay.lift()

    def refresh_all_tabs(self):
        """탭 하나가 값을 바꿀 때마다 모든 탭을 다시 그립니다 (기존 update_ui_tables와 동일한 동작)."""
        for tab in self.tabs:
            tab.refresh()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    if getattr(app, "_init_ok", False):
        root.mainloop()
