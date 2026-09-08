"""
tabs/terrain_tab.py
"지형(Terrain) EasyRPG 데미지 옵션 조절" 탭 - 속성 편집기(Property Editor) 스타일.
core/item_schema.py 대신 core/terrain_schema.py의 TERRAIN_FIELD_DEFS를 사용한다는
점만 다르고 구조는 tabs/item_tab.py와 동일합니다 (검색/ID 입력만으로 즉시 편집
패널이 열립니다).

이번 요청 범위는 EasyRPG 확장 옵션 2종(easyrpg_damage_in_percent/
easyrpg_damage_can_kill)뿐이라, damage 등 알만툴 순정 지형 필드는 다루지 않습니다.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import (attach_tree_scrollbar, make_listbox_with_scroll,
                         enable_column_sort, enable_column_width_persistence)
from core.context_menu import attach_row_context_menu
from core.property_panel import (make_fixed_scroll_panel, render_field_row, render_group_header,
                                  scroll_panel_to_top, DETAIL_WIDTH, DETAIL_HEIGHT)
from core.terrain_schema import TERRAIN_FIELD_DEFS, default_terrain_fields, migrate_terrain_entry
from core.logger import log
from core.i18n import t


class TerrainTab:
    TITLE = t("terrain_tab.title")

    def __init__(self, app):
        self.app = app
        self._current_terrain = None

    @property
    def cfg(self):
        return self.app.cfg

    # ------------------------------------------------------------------
    def on_project_loaded(self):
        """새로 추가된 필드가 있으면 기존 지형 항목에도 기본값으로 채워 넣습니다
        (다른 탭과 동일한 패턴)."""
        terrains = self.cfg.current_config.get("terrains", [])
        migrated = [migrate_terrain_entry(tr) for tr in terrains]
        if migrated != terrains:
            self.cfg.current_config["terrains"] = migrated
            self.cfg.save_config()

    # ------------------------------------------------------------------
    def build(self, notebook):
        terrain_frame = ttk.Frame(notebook, padding=10)
        notebook.add(terrain_frame, text=self.TITLE)

        left_frame = ttk.Frame(terrain_frame)
        left_frame.pack(fill="both", expand=True, side="left")

        self.terrain_tree = ttk.Treeview(left_frame, columns=("ID", "이름"), show="headings", height=18)
        for col, txt in [("ID", t("terrain_tab.col_id")), ("이름", t("terrain_tab.col_name"))]:
            self.terrain_tree.heading(col, text=txt)
        attach_tree_scrollbar(self.terrain_tree, left_frame)
        self.terrain_tree.pack(fill="both", expand=True, side="left")

        self.terrain_tree.column("ID", width=60, anchor="center")
        self.terrain_tree.column("이름", width=280, anchor="w")
        self.terrain_tree.bind("<<TreeviewSelect>>", self.on_terrain_select)
        enable_column_sort(self.terrain_tree, ("ID", "이름"), numeric_columns=("ID",))
        enable_column_width_persistence(self.terrain_tree, self.cfg, "terrain_tree")
        attach_row_context_menu(self.terrain_tree, lambda: self.move_terrain(-1), lambda: self.move_terrain(1), self.delete_terrain_rule)

        terrain_btn_frame = ttk.Frame(terrain_frame, padding=10)
        terrain_btn_frame.pack(fill="y", side="right")

        ttk.Label(terrain_btn_frame, text=t("common.label_search_name")).pack(anchor="w", pady=(0, 2))
        self.terrain_search_entry = ttk.Entry(terrain_btn_frame, width=25)
        self.terrain_search_entry.pack(anchor="w", pady=(0, 2))
        self.terrain_search_entry.bind("<KeyRelease>", self.on_terrain_search)
        terrain_search_frame, self.terrain_search_listbox = make_listbox_with_scroll(terrain_btn_frame, height=6)
        terrain_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.terrain_search_listbox.bind("<<ListboxSelect>>", self.on_terrain_search_select)

        ttk.Label(terrain_btn_frame, text=t("terrain_tab.label_id")).pack(anchor="w", pady=(0, 2))
        self.terrain_id_entry = ttk.Entry(terrain_btn_frame, width=25); self.terrain_id_entry.pack(anchor="w", pady=(0, 2))
        self.terrain_id_entry.bind("<KeyRelease>", self.on_id_entry_typed)
        self.terrain_id_entry.bind("<Return>", self.on_id_entry_committed)
        self.terrain_id_entry.bind("<FocusOut>", self.on_id_entry_committed)
        self.selected_name_var = tk.StringVar(value=t("common.label_selected_name_empty"))
        ttk.Label(terrain_btn_frame, textvariable=self.selected_name_var).pack(anchor="w", pady=(0, 10))

        add_del_row = ttk.Frame(terrain_btn_frame)
        add_del_row.pack(fill="x", pady=3)
        ttk.Button(add_del_row, text=t("common.btn_add_to_list"), command=self.add_terrain_rule).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(add_del_row, text=t("common.btn_remove_from_list"), command=self.delete_terrain_rule).pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Label(terrain_btn_frame, text=t("common.label_batch_settings")).pack(anchor="w", pady=(20, 4))
        ttk.Button(terrain_btn_frame, text=t("common.btn_clear_all"), command=self.batch_clear_terrains).pack(fill="x", pady=2)

        ttk.Label(terrain_btn_frame, text=t("common.label_detail_editor")).pack(anchor="w", pady=(20, 4))
        self.detail_outer, self.terrain_detail_frame = make_fixed_scroll_panel(
            terrain_btn_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

    def _show_placeholder(self):
        for w in self.terrain_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.terrain_detail_frame, text=t("terrain_tab.placeholder"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    def reset_detail_panel(self):
        """외부(설정 불러오기 등)에서 데이터 전체가 교체됐을 때, 화면에 예전 값이
        남아있지 않도록 편집 패널을 비웁니다."""
        self._current_terrain = None
        self._show_placeholder()

    # ------------------------------------------------------------------
    def refresh(self):
        selected = self.terrain_tree.selection()
        prev_iid = selected[0] if selected else None

        self._suppress_tree_select = True
        try:
            for item in self.terrain_tree.get_children(): self.terrain_tree.delete(item)
            for tr in self.cfg.current_config.get("terrains", []):
                tid = tr["id"]
                name = self.app.edb_master_terrains.get(tid) or t("common.msg_not_in_master_db")
                self.terrain_tree.insert("", "end", iid=str(tid), values=(tid, name))

            if prev_iid and self.terrain_tree.exists(prev_iid):
                self.terrain_tree.selection_set(prev_iid)
                self.terrain_tree.see(prev_iid)
        finally:
            # selection_set()이 만드는 <<TreeviewSelect>> 이벤트는 즉시가 아니라
            # Tk 이벤트 큐에 쌓였다가 다음 idle 처리 때 발생합니다. 여기서 바로
            # 플래그를 False로 되돌리면 그 지연된 이벤트가 나중에 도착했을 때
            # 억제되지 못하고 on_*_select가 다시 실행돼(상세 패널 재생성) 버리므로,
            # 이번 이벤트 루프 한 바퀴가 다 돈 뒤(after_idle)에 해제합니다.
            self.terrain_tree.after_idle(lambda: setattr(self, "_suppress_tree_select", False))

    # ------------------------------------------------------------------
    def _update_selected_name_label(self, iid_text):
        try:
            iid = int(iid_text.strip())
        except ValueError:
            self.selected_name_var.set(t("common.label_selected_name_empty"))
            return
        name = self.app.edb_master_terrains.get(iid)
        self.selected_name_var.set(t("common.label_selected_name", name=name) if name else t("common.label_selected_name_unknown"))

    def on_id_entry_typed(self, event):
        self._update_selected_name_label(self.terrain_id_entry.get())

    def on_id_entry_committed(self, event):
        raw = self.terrain_id_entry.get().strip()
        if not raw:
            return
        try:
            iid = int(raw)
        except ValueError:
            return
        self.open_editor_for_id(iid)

    def on_terrain_select(self, event):
        if getattr(self, "_suppress_tree_select", False):
            return
        selected = self.terrain_tree.selection()
        if not selected: return
        iid = int(selected[0])
        tr = next((x for x in self.cfg.current_config["terrains"] if x["id"] == iid), None)
        if tr:
            self.terrain_id_entry.delete(0, tk.END); self.terrain_id_entry.insert(0, str(tr["id"]))
            self._update_selected_name_label(str(tr["id"]))
            self.render_terrain_detail(tr)

    def open_editor_for_id(self, iid):
        """ID(검색 선택 또는 직접 입력)만으로 즉시 편집 패널을 엽니다.
        아직 목록에 없는 지형이면 기본값으로 자동 추가합니다."""
        self._update_selected_name_label(str(iid))
        existing = next((x for x in self.cfg.current_config["terrains"] if x["id"] == iid), None)
        if existing is None:
            if iid not in self.app.edb_master_terrains:
                if not messagebox.askyesno(t("common.title_warning"), t("terrain_tab.msg_confirm_add_unknown")):
                    return
            fields = default_terrain_fields()
            existing = {"id": iid, "fields": fields}
            self.cfg.current_config["terrains"].append(existing)
            self.cfg.save_config()
            log.info(t("terrain_tab.log_added", id=iid))
            self.app.refresh_all_tabs()

        if self.terrain_tree.exists(str(iid)):
            self.terrain_tree.selection_set(str(iid))
            self.terrain_tree.see(str(iid))
        self.render_terrain_detail(existing)

    def render_terrain_detail(self, tr):
        for w in self.terrain_detail_frame.winfo_children():
            w.destroy()
        self._current_terrain = tr
        fields = tr["fields"]
        p = self.terrain_detail_frame

        name = self.app.edb_master_terrains.get(tr["id"], t("common.name_unknown"))
        ttk.Label(p, text=t("terrain_tab.detail_header", id=tr['id'], name=name), font=("Segoe UI", 10, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 4))

        last_group = None
        for fd in TERRAIN_FIELD_DEFS:
            group = fd.get("group", "기타")
            if group != last_group:
                header_holder = ttk.Frame(p)
                header_holder.pack(fill="x", padx=8)
                render_group_header(header_holder, group)
                last_group = group

            row = ttk.Frame(p)
            row.pack(fill="x", padx=8)
            control, set_enabled = render_field_row(
                row, fd, fields.get(fd["name"], fd["default"]), self._make_on_change(fd["name"])
            )
            set_enabled(True)

        scroll_panel_to_top(self.detail_outer)

    def _make_on_change(self, field_name):
        def _on_change(new_val):
            self._current_terrain["fields"][field_name] = new_val
            self.cfg.save_config()
            self.app.refresh_all_tabs()
            log.info(t("terrain_tab.log_field_changed", id=self._current_terrain["id"], field=field_name, value=new_val))
        return _on_change

    # ------------------------------------------------------------------
    # 이름 검색 (드롭다운) - 선택하면 즉시 편집 패널이 열림
    # ------------------------------------------------------------------
    def on_terrain_search(self, event):
        query = self.terrain_search_entry.get().strip().lower()
        self.terrain_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(tid, name) for tid, name in sorted(self.app.edb_master_terrains.items()) if query in name.lower()]
        for tid, name in matches[:20]:
            self.terrain_search_listbox.insert(tk.END, f"{tid} - {name}")

    def on_terrain_search_select(self, event):
        sel = self.terrain_search_listbox.curselection()
        if not sel: return
        text = self.terrain_search_listbox.get(sel[0])
        tid = int(text.split(" - ", 1)[0])
        self.terrain_id_entry.delete(0, tk.END); self.terrain_id_entry.insert(0, str(tid))
        self.terrain_search_entry.delete(0, tk.END)
        self.terrain_search_listbox.delete(0, tk.END)
        self.open_editor_for_id(tid)

    # ------------------------------------------------------------------
    # 목록 추가/삭제/일괄 설정
    # ------------------------------------------------------------------
    def move_terrain(self, direction):
        sel = self.terrain_tree.selection()
        if not sel: return
        tid = int(sel[0])
        terrains = self.cfg.current_config["terrains"]
        idx = next((i for i, x in enumerate(terrains) if x["id"] == tid), None)
        if idx is None: return
        new_idx = idx + direction
        if 0 <= new_idx < len(terrains):
            terrains[idx], terrains[new_idx] = terrains[new_idx], terrains[idx]
            self.cfg.save_config()
            self.app.refresh_all_tabs()

    def add_terrain_rule(self):
        try:
            tid = int(self.terrain_id_entry.get().strip())
        except ValueError:
            messagebox.showerror(t("common.title_error"), t("common.msg_id_must_be_number"))
            return
        self.open_editor_for_id(tid)

    def delete_terrain_rule(self):
        sel = self.terrain_tree.selection()
        if not sel: return
        tid = int(sel[0])
        self.cfg.current_config["terrains"] = [x for x in self.cfg.current_config["terrains"] if x["id"] != tid]
        self.cfg.save_config()
        if self._current_terrain and self._current_terrain.get("id") == tid:
            self._current_terrain = None
            self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("terrain_tab.log_deleted", id=tid))

    def batch_clear_terrains(self):
        if not self.cfg.current_config["terrains"]:
            messagebox.showwarning(t("common.title_warning"), t("terrain_tab.msg_no_terrains"))
            return
        if not messagebox.askyesno(t("terrain_tab.title_confirm_clear"), t("terrain_tab.msg_confirm_clear")): return
        self.cfg.current_config["terrains"] = []
        self.cfg.save_config()
        self._current_terrain = None
        self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("terrain_tab.log_cleared"))
