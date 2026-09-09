"""
auto ldb patcher.py
프로그램 진입점 (메인 파일).

이 파일이 하는 일은 다음뿐입니다:
  1. 프로그램 시작 (사전 점검 + RPG_RT.ldb 선택)
  2. 공통 설정 로드 (core.config.ConfigManager)
  3. 메인 윈도우 생성 (상단 툴바 + 탭 + 하단 로그 패널)
  4. 각 탭 로드 (tabs/*.py)
  5. 저장(edb→ldb 패치) 처리 위임 (core.lcf)

새 탭을 추가하려면 tabs/ 아래에 파일 하나만 만들고,
아래 TAB_CLASSES 목록에 한 줄만 추가하면 됩니다.

화면에 보이는 문자열은 직접 쓰지 않고 core.i18n.t()로 core/locales/ko.json에서
가져옵니다 - 나중에 영어/일본어를 추가할 때 이 파일들은 건드릴 필요가 없습니다.
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# 이 파일과 같은 폴더를 import 경로에 추가 (core/, tabs/ 패키지를 찾기 위함)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.utils import get_program_dir
from core.theme import BG, BG2, FG, FG_DIM, BORDER, apply_dark_theme, make_listbox_with_scroll
from core.tab_bar import WrappingNotebook
from core.config import ConfigManager
from core.logger import log
from core.i18n import t, set_language, get_language
from core import lcf

from tabs.actor_tab import ActorTab
from tabs.class_tab import ClassTab
from tabs.skill_tab import SkillTab
from tabs.item_tab import ItemTab
from tabs.enemy_tab import EnemyTab
from tabs.terrain_tab import TerrainTab
from tabs.system_tab import SystemTab

# 새 탭은 여기에 한 줄만 추가하면 자동으로 로드됩니다.
TAB_CLASSES = [ActorTab, ClassTab, SkillTab, ItemTab, EnemyTab, TerrainTab, SystemTab]

LOG_PANEL_HEIGHT = 7
LANGUAGE_OPTIONS = [("ko", "한국어"), ("en", "English"), ("ja", "日本語")]


class App:
    def __init__(self, root):
        self.root = root
        self._init_ok = False

        self.cfg = ConfigManager(get_program_dir())
        self.edb_master_items = {}
        self.edb_master_item_types = {}
        self.edb_master_skills = {}
        self.edb_master_skill_stats = {}
        self.edb_master_actors = {}
        self.edb_master_actor_data = {}
        self.edb_master_classes = {}
        self.edb_master_class_data = {}
        self.edb_master_enemies = {}
        self.edb_master_enemy_stats = {}
        self.edb_master_terrains = {}
        self.tabs = []

        apply_dark_theme(self.root)
        self.root.withdraw()

        # load_common_config() 자체가 끝에서 로그를 하나 남기는데, 그 메시지까지도
        # 올바른 언어로 나오도록 파일을 직접 살짝 미리 읽어 언어를 적용해둡니다
        # (아래에서 load_common_config()가 끝난 뒤 한 번 더 정식으로 적용합니다).
        try:
            import json as _json
            with open(self.cfg.config_file, "r", encoding="utf-8") as _f:
                set_language(_json.load(_f).get("settings", {}).get("language", "ko"))
        except Exception:
            pass

        self.cfg.load_common_config()
        # 저장된 언어 설정을 가장 먼저 적용합니다 - 창 제목을 비롯해 이 시점 이후의
        # 모든 t() 호출(사전 점검 실패 메시지 등)이 올바른 언어로 나오도록 하기 위함입니다.
        set_language(self.cfg.common_config.get("settings", {}).get("language", "ko"))

        self.root.title(t("main.window_title"))
        self.root.geometry("1200x1300")

        if not self.cfg.check_program_prerequisites():
            self.root.destroy()
            return

        if not self.cfg.select_project_file():
            self.root.destroy()
            return

        self.root.deiconify()

        self.create_widgets()  # 로그 패널을 먼저 만들어야 이후 로그가 GUI에도 표시됨
        self.sync_edb_master_data()
        self.cfg.load_project_config()
        self.notify_tabs_project_loaded()
        self.refresh_all_tabs()
        self.refresh_edb_overlay()
        self._init_ok = True

    # ------------------------------------------------------------------
    # edb 동기화 (core.lcf 위임)
    # ------------------------------------------------------------------
    def sync_edb_master_data(self):
        (items, item_types, skills, skill_stats,
         actors, actor_data, classes, class_data,
         enemies, enemy_stats, terrains) = lcf.decompile_and_parse_edb_directly(self.cfg)
        if items is not None:
            self.edb_master_items = items
            self.edb_master_item_types = item_types
            self.edb_master_skills = skills
            self.edb_master_skill_stats = skill_stats
            self.edb_master_actors = actors
            self.edb_master_actor_data = actor_data
            self.edb_master_classes = classes
            self.edb_master_class_data = class_data
            self.edb_master_enemies = enemies
            self.edb_master_enemy_stats = enemy_stats
            self.edb_master_terrains = terrains

    def notify_tabs_project_loaded(self):
        """탭이 프로젝트별 마이그레이션(예: 예전 스킬 저장 형식 변환)이 필요하면
        on_project_loaded()를 구현해두면 프로젝트를 불러올 때마다 자동 호출됩니다."""
        for tab in self.tabs:
            hook = getattr(tab, "on_project_loaded", None)
            if callable(hook):
                hook()

    def refresh_from_edb(self):
        self.sync_edb_master_data()
        self.refresh_all_tabs()
        self.refresh_edb_overlay()
        if os.path.exists(self.cfg.edb_file):
            messagebox.showinfo(t("common.title_done"), t("main.msg_edb_synced"))

    def change_project_file(self):
        if self.cfg.select_project_file():
            self.sync_edb_master_data()
            self.cfg.load_project_config()
            self.notify_tabs_project_loaded()
            self.refresh_all_tabs()
            self.refresh_edb_overlay()
            if hasattr(self, "project_label"):
                self.project_label.config(text=t("main.project_label", title=self.cfg.project_title, dir=self.cfg.game_dir))

    def on_language_changed(self, event):
        """언어 콤보박스에서 새 언어를 선택했을 때 호출됩니다. 이미 만들어진 수많은
        위젯의 문자열을 전부 실시간으로 다시 그리는 대신(위험도가 높고 복잡함), 선택한
        언어를 설정에 저장해두고 바로 재시작해서 새 언어로 다시 켜지도록 안내합니다."""
        selected_name = self.language_var.get()
        lang_code = next((code for code, name in LANGUAGE_OPTIONS if name == selected_name), "ko")
        if lang_code == self.cfg.common_config.get("settings", {}).get("language", "ko"):
            return

        self.cfg.common_config.setdefault("settings", {})["language"] = lang_code
        self.cfg.save_common_config()
        log.info(f"Language changed to '{lang_code}' (applies after restart)")

        if messagebox.askyesno(t("main.title_language_restart"), t("main.msg_language_restart_confirm")):
            self.restart_app()

    def restart_app(self):
        """프로그램을 재시작합니다.
        원래 os.execv()로 자기 자신을 대체 실행했었는데, PyInstaller --onefile 빌드에서는
        이 방식이 "Security validation failure: failed to obtain executable path for
        parent process!" 오류로 이어졌습니다 - onefile 부트로더는 임시로 압축 해제한
        내용물을 정리하기 위해 실행 파일이 정상적인 방식(새 프로세스 생성)으로만
        재실행되기를 기대하는데, execv는 현재 프로세스를 완전히 다른 프로그램으로
        바꿔치기해버려서 부트로더 입장에서는 "부모 프로세스"가 사라져버린 것과 같은
        상태가 되기 때문입니다. 그래서 대신 새 프로세스를 별도로 띄운 뒤, 지금 이
        프로세스는 평범하게 종료하는 방식으로 바꿨습니다."""
        try:
            if getattr(sys, "frozen", False):
                # PyInstaller 빌드: sys.argv[0]이 이미 실행 파일 경로 자체이므로 그대로 재실행
                subprocess.Popen(sys.argv, cwd=os.getcwd())
            else:
                # 개발 모드(python "auto ldb patcher.py"): 인터프리터 + 스크립트 경로로 재실행
                subprocess.Popen([sys.executable] + sys.argv, cwd=os.getcwd())
        except Exception as e:
            log.error(f"Failed to restart automatically: {e}")
            messagebox.showerror(t("common.title_fail"), t("main.msg_restart_fail", reason=e))
            return
        self.root.destroy()
        sys.exit(0)

    def apply_final_patch(self):
        if lcf.apply_final_patch(self.cfg):
            self.refresh_edb_overlay()

    def reset_all_tab_details(self):
        """탭들이 열어두고 있던 편집 패널을 전부 비웁니다 (다른 프로젝트에서 설정을
        통째로 불러온 직후처럼, 화면에 예전 항목의 값이 남아있으면 안 되는 경우)."""
        for tab in self.tabs:
            hook = getattr(tab, "reset_detail_panel", None)
            if callable(hook):
                hook()

    def open_import_settings_dialog(self):
        """게임을 버전업 할 때마다(예: projects의 v1 -> v2) 아이템/스킬/액터/클래스/적/
        지형/시스템 설정을 처음부터 다시 입력하지 않도록, 다른 프로젝트 폴더에 저장된
        값을 골라서 현재 프로젝트에 통째로 불러오는 창을 띄웁니다."""
        projects = self.cfg.list_other_projects()
        if not projects:
            messagebox.showinfo(t("main.dialog_import_title"), t("main.msg_import_no_projects"))
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(t("main.dialog_import_title"))
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(dialog, text=t("main.label_import_pick"), justify="left").pack(
            anchor="w", padx=14, pady=(14, 8)
        )

        list_frame, listbox = make_listbox_with_scroll(dialog, height=10)
        list_frame.pack(fill="both", expand=True, padx=14)
        for proj in projects:
            listbox.insert(tk.END, proj["folder"])
        listbox.selection_set(0)

        btn_row = ttk.Frame(dialog)
        btn_row.pack(fill="x", padx=14, pady=14)

        def do_import():
            sel = listbox.curselection()
            if not sel:
                return
            proj = projects[sel[0]]
            if not messagebox.askyesno(
                t("main.title_import_confirm"),
                t("main.msg_import_confirm", folder=proj["folder"]),
                parent=dialog,
            ):
                return
            summary = self.cfg.import_settings_from(proj["path"])
            if summary is None:
                return
            self.reset_all_tab_details()
            self.refresh_all_tabs()
            dialog.destroy()
            messagebox.showinfo(t("common.title_done"), t("main.msg_import_done", folder=proj["folder"]))

        ttk.Button(btn_row, text=t("common.btn_ok"), command=do_import).pack(side="right", padx=(6, 0))
        ttk.Button(btn_row, text=t("common.btn_cancel"), command=dialog.destroy).pack(side="right")

    # ------------------------------------------------------------------
    # UI 구성
    # ------------------------------------------------------------------
    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")
        ttk.Button(top_frame, text=t("common.btn_reload_edb"), command=self.refresh_from_edb).pack(side="left", padx=5)
        ttk.Button(top_frame, text=t("main.btn_change_project"), command=self.change_project_file).pack(side="left", padx=5)
        ttk.Button(top_frame, text=t("main.btn_import_settings"), command=self.open_import_settings_dialog).pack(side="left", padx=5)

        lang_frame = ttk.Frame(top_frame)
        lang_frame.pack(side="left", padx=(15, 5))
        ttk.Label(lang_frame, text=t("main.label_language")).pack(side="left", padx=(0, 4))
        current_name = next((name for code, name in LANGUAGE_OPTIONS if code == get_language()), LANGUAGE_OPTIONS[0][1])
        self.language_var = tk.StringVar(value=current_name)
        self.language_combo = ttk.Combobox(
            lang_frame, textvariable=self.language_var, state="readonly", width=9,
            values=[name for _, name in LANGUAGE_OPTIONS],
        )
        self.language_combo.pack(side="left")
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_changed)
        self.project_label = ttk.Label(
            top_frame, text=t("main.project_label", title=self.cfg.project_title, dir=self.cfg.game_dir), foreground=FG_DIM
        )
        self.project_label.pack(side="left", padx=15)
        ttk.Button(top_frame, text=t("common.btn_save_patch"), command=self.apply_final_patch).pack(side="right", padx=5)

        self.body_container = ttk.Frame(self.root)
        self.body_container.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        self.notebook = WrappingNotebook(self.body_container)
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
        tk.Label(overlay_inner, text=t("main.overlay_title"),
                 font=("Segoe UI", 13, "bold"), bg=BG, fg=FG).pack()
        tk.Label(overlay_inner, text=t("main.overlay_subtitle"),
                 font=("Segoe UI", 11), bg=BG, fg=FG_DIM).pack(pady=(2, 16))
        ttk.Button(overlay_inner, text=t("common.btn_reload_edb"), command=self.refresh_from_edb).pack()

        self.create_log_panel()

    def create_log_panel(self):
        log_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        log_frame.pack(fill="x", side="bottom")

        header = ttk.Frame(log_frame)
        header.pack(fill="x")
        ttk.Label(header, text=t("main.log_label"), foreground=FG_DIM).pack(side="left")
        ttk.Button(header, text=t("common.btn_clear"), command=self.clear_log).pack(side="right")

        text_row = tk.Frame(log_frame, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        text_row.pack(fill="x", pady=(4, 0))

        self.log_text = tk.Text(text_row, height=LOG_PANEL_HEIGHT, bg=BG2, fg=FG,
                                 insertbackground=FG, relief="flat", state="disabled",
                                 wrap="word")
        vsb = ttk.Scrollbar(text_row, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=vsb.set)
        # (스크롤바를 먼저 배치해야 자기 몫의 폭을 확보합니다 - core/property_panel.py 참고)
        vsb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        self.log_text.tag_configure("info", foreground=FG)
        self.log_text.tag_configure("warning", foreground="#e0b400")
        self.log_text.tag_configure("error", foreground="#ff6b6b")

        log.attach(self.log_text)
        log.info(t("main.log_started"))

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

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
