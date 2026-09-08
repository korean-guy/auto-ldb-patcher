"""
tabs/enemy_tab.py
"적(Enemy) 세부 옵션 조절" 탭 - 속성 편집기(Property Editor) 스타일.

좌측: 프로젝트에 등록된 적 목록(이름검색으로 추가, 선택해서 삭제) - ID/이름만 표시
우측: 선택한 적의 기본 스테이터스(HP/SP/공격력/방어력/정신력/민첩성) +
      EasyRPG 확장 옵션들을 그룹별로 보여주는 고정 크기 편집 패널
      (core.property_panel 재사용 - Skill/Item/System 탭과 동일한 방식)

검색 결과를 선택하거나 ID를 직접 입력하면(Enter/포커스 아웃), 아직 목록에 없는
적이라도 즉시 추가되고 편집 패널이 바로 열립니다 - 이때 기본 스테이터스 6종은
edb에 있는 실제 순정 수치를 기본값으로 채워 넣습니다(core/skill_schema.py의
STAT_FIELDS_FROM_EDB와 동일한 패턴).

새 EasyRPG 적 옵션은 core/enemy_schema.py의 ENEMY_FIELD_DEFS에 항목만
추가하면 이 탭에 자동으로 나타납니다.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import (attach_tree_scrollbar, make_listbox_with_scroll,
                         enable_column_sort, enable_column_width_persistence)
from core.context_menu import attach_row_context_menu
from core.property_panel import (make_fixed_scroll_panel, render_field_row, render_group_header,
                                  scroll_panel_to_top, DETAIL_WIDTH, DETAIL_HEIGHT)
from core.enemy_schema import ENEMY_FIELD_DEFS, STAT_FIELDS_FROM_EDB, default_enemy_fields, migrate_enemy_entry
from core.logger import log
from core.i18n import t


class EnemyTab:
    TITLE = t("enemy_tab.title")

    def __init__(self, app):
        self.app = app
        self._current_enemy = None

    @property
    def cfg(self):
        return self.app.cfg

    # ------------------------------------------------------------------
    def on_project_loaded(self):
        """새로 추가된 필드가 있으면 기존 적 항목에도 기본값으로 채워 넣습니다
        (다른 탭과 동일한 패턴)."""
        enemies = self.cfg.current_config.get("enemies", [])
        migrated = [migrate_enemy_entry(en) for en in enemies]
        if migrated != enemies:
            self.cfg.current_config["enemies"] = migrated
            self.cfg.save_config()

    # ------------------------------------------------------------------
    def build(self, notebook):
        enemy_frame = ttk.Frame(notebook, padding=10)
        notebook.add(enemy_frame, text=self.TITLE)

        left_frame = ttk.Frame(enemy_frame)
        left_frame.pack(fill="both", expand=True, side="left")

        columns = ("ID", "이름", "최대체력", "최대마력", "공격력", "방어력", "정신력", "민첩성")
        self.enemy_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=18)
        headings = [
            ("ID", t("enemy_tab.col_id")), ("이름", t("enemy_tab.col_name")),
            ("최대체력", t("enemy_tab.col_max_hp")), ("최대마력", t("enemy_tab.col_max_sp")),
            ("공격력", t("enemy_tab.col_attack")), ("방어력", t("enemy_tab.col_defense")),
            ("정신력", t("enemy_tab.col_spirit")), ("민첩성", t("enemy_tab.col_agility")),
        ]
        for col, txt in headings: self.enemy_tree.heading(col, text=txt)
        attach_tree_scrollbar(self.enemy_tree, left_frame)
        self.enemy_tree.pack(fill="both", expand=True, side="left")

        self.enemy_tree.column("ID", width=50, anchor="center")
        self.enemy_tree.column("이름", width=160, anchor="w")
        self.enemy_tree.column("최대체력", width=80, anchor="center")
        self.enemy_tree.column("최대마력", width=80, anchor="center")
        self.enemy_tree.column("공격력", width=70, anchor="center")
        self.enemy_tree.column("방어력", width=70, anchor="center")
        self.enemy_tree.column("정신력", width=70, anchor="center")
        self.enemy_tree.column("민첩성", width=70, anchor="center")
        self.enemy_tree.bind("<<TreeviewSelect>>", self.on_enemy_select)
        enable_column_sort(self.enemy_tree, columns,
                            numeric_columns=("ID", "최대체력", "최대마력", "공격력", "방어력", "정신력", "민첩성"))
        enable_column_width_persistence(self.enemy_tree, self.cfg, "enemy_tree")
        attach_row_context_menu(self.enemy_tree, lambda: self.move_enemy(-1), lambda: self.move_enemy(1), self.delete_enemy_rule)

        enemy_btn_frame = ttk.Frame(enemy_frame, padding=10)
        enemy_btn_frame.pack(fill="y", side="right")

        ttk.Label(enemy_btn_frame, text=t("common.label_search_name")).pack(anchor="w", pady=(0, 2))
        self.enemy_search_entry = ttk.Entry(enemy_btn_frame, width=25)
        self.enemy_search_entry.pack(anchor="w", pady=(0, 2))
        self.enemy_search_entry.bind("<KeyRelease>", self.on_enemy_search)
        enemy_search_frame, self.enemy_search_listbox = make_listbox_with_scroll(enemy_btn_frame, height=6)
        enemy_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.enemy_search_listbox.bind("<<ListboxSelect>>", self.on_enemy_search_select)

        ttk.Label(enemy_btn_frame, text=t("enemy_tab.label_id")).pack(anchor="w", pady=(0, 2))
        self.enemy_id_entry = ttk.Entry(enemy_btn_frame, width=25); self.enemy_id_entry.pack(anchor="w", pady=(0, 2))
        self.enemy_id_entry.bind("<KeyRelease>", self.on_id_entry_typed)
        self.enemy_id_entry.bind("<Return>", self.on_id_entry_committed)
        self.enemy_id_entry.bind("<FocusOut>", self.on_id_entry_committed)
        self.selected_name_var = tk.StringVar(value=t("common.label_selected_name_empty"))
        ttk.Label(enemy_btn_frame, textvariable=self.selected_name_var).pack(anchor="w", pady=(0, 10))

        add_del_row = ttk.Frame(enemy_btn_frame)
        add_del_row.pack(fill="x", pady=3)
        ttk.Button(add_del_row, text=t("common.btn_add_to_list"), command=self.add_enemy_rule).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(add_del_row, text=t("common.btn_remove_from_list"), command=self.delete_enemy_rule).pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Label(enemy_btn_frame, text=t("common.label_batch_settings")).pack(anchor="w", pady=(20, 4))
        batch_row = ttk.Frame(enemy_btn_frame); batch_row.pack(fill="x", pady=2)
        ttk.Button(batch_row, text=t("common.btn_clear_all"), command=self.batch_clear_enemies).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(batch_row, text=t("enemy_tab.btn_reset_extra"), command=self.batch_reset_extra_options).pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Label(enemy_btn_frame, text=t("common.label_detail_editor")).pack(anchor="w", pady=(20, 4))
        self.detail_outer, self.enemy_detail_frame = make_fixed_scroll_panel(
            enemy_btn_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

    def _show_placeholder(self):
        for w in self.enemy_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.enemy_detail_frame, text=t("enemy_tab.placeholder"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    def reset_detail_panel(self):
        """외부(설정 불러오기 등)에서 데이터 전체가 교체됐을 때, 화면에 예전 값이
        남아있지 않도록 편집 패널을 비웁니다."""
        self._current_enemy = None
        self._show_placeholder()

    # ------------------------------------------------------------------
    def refresh(self):
        selected = self.enemy_tree.selection()
        prev_iid = selected[0] if selected else None

        self._suppress_tree_select = True
        try:
            for item in self.enemy_tree.get_children(): self.enemy_tree.delete(item)
            for en in self.cfg.current_config.get("enemies", []):
                eid = en["id"]
                fields = en.get("fields", {})
                name = fields.get("name") or self.app.edb_master_enemies.get(eid) or t("common.msg_not_in_master_db")
                self.enemy_tree.insert("", "end", iid=str(eid), values=(
                    eid, name,
                    fields.get("max_hp", 0), fields.get("max_sp", 0),
                    fields.get("attack", 0), fields.get("defense", 0),
                    fields.get("spirit", 0), fields.get("agility", 0),
                ))

            if prev_iid and self.enemy_tree.exists(prev_iid):
                self.enemy_tree.selection_set(prev_iid)
                self.enemy_tree.see(prev_iid)
        finally:
            # selection_set()이 만드는 <<TreeviewSelect>> 이벤트는 즉시가 아니라
            # Tk 이벤트 큐에 쌓였다가 다음 idle 처리 때 발생합니다. 여기서 바로
            # 플래그를 False로 되돌리면 그 지연된 이벤트가 나중에 도착했을 때
            # 억제되지 못하고 on_*_select가 다시 실행돼(상세 패널 재생성) 버리므로,
            # 이번 이벤트 루프 한 바퀴가 다 돈 뒤(after_idle)에 해제합니다.
            self.enemy_tree.after_idle(lambda: setattr(self, "_suppress_tree_select", False))

    # ------------------------------------------------------------------
    def _update_selected_name_label(self, iid_text):
        try:
            iid = int(iid_text.strip())
        except ValueError:
            self.selected_name_var.set(t("common.label_selected_name_empty"))
            return
        name = self.app.edb_master_enemies.get(iid)
        self.selected_name_var.set(t("common.label_selected_name", name=name) if name else t("common.label_selected_name_unknown"))

    def on_id_entry_typed(self, event):
        self._update_selected_name_label(self.enemy_id_entry.get())

    def on_id_entry_committed(self, event):
        raw = self.enemy_id_entry.get().strip()
        if not raw:
            return
        try:
            iid = int(raw)
        except ValueError:
            return
        self.open_editor_for_id(iid)

    def on_enemy_select(self, event):
        if getattr(self, "_suppress_tree_select", False):
            return
        selected = self.enemy_tree.selection()
        if not selected: return
        eid = int(selected[0])
        en = next((e for e in self.cfg.current_config["enemies"] if e["id"] == eid), None)
        if en:
            self.enemy_id_entry.delete(0, tk.END); self.enemy_id_entry.insert(0, str(en["id"]))
            self._update_selected_name_label(str(en["id"]))
            self.render_enemy_detail(en)

    def open_editor_for_id(self, eid):
        """ID(검색 선택 또는 직접 입력)만으로 즉시 편집 패널을 엽니다.
        아직 목록에 없는 적이면 기본 스테이터스를 edb 실제 수치로 채워 자동 추가합니다."""
        self._update_selected_name_label(str(eid))
        existing = next((e for e in self.cfg.current_config["enemies"] if e["id"] == eid), None)
        if existing is None:
            if eid not in self.app.edb_master_enemies:
                if not messagebox.askyesno(t("common.title_warning"), t("enemy_tab.msg_confirm_add_unknown")):
                    return
            fields = default_enemy_fields()
            real_stats = self.app.edb_master_enemy_stats.get(eid, {})
            for key in STAT_FIELDS_FROM_EDB:
                if key in real_stats:
                    fields[key] = real_stats[key]
            existing = {"id": eid, "fields": fields}
            self.cfg.current_config["enemies"].append(existing)
            self.cfg.save_config()
            log.info(t("enemy_tab.log_added", id=eid))
            self.app.refresh_all_tabs()

        if self.enemy_tree.exists(str(eid)):
            self.enemy_tree.selection_set(str(eid))
            self.enemy_tree.see(str(eid))
        self.render_enemy_detail(existing)

    def render_enemy_detail(self, en):
        for w in self.enemy_detail_frame.winfo_children():
            w.destroy()
        self._current_enemy = en
        fields = en["fields"]
        p = self.enemy_detail_frame

        name = self.app.edb_master_enemies.get(en["id"], t("common.name_unknown"))
        ttk.Label(p, text=t("enemy_tab.detail_header", id=en['id'], name=name), font=("Segoe UI", 10, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 4))

        last_group = None
        for fd in ENEMY_FIELD_DEFS:
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
            self._current_enemy["fields"][field_name] = new_val
            self.cfg.save_config()
            self.app.refresh_all_tabs()
            log.info(t("enemy_tab.log_field_changed", id=self._current_enemy["id"], field=field_name, value=new_val))
        return _on_change

    # ------------------------------------------------------------------
    # 이름 검색 (드롭다운) - 선택하면 즉시 편집 패널이 열림
    # ------------------------------------------------------------------
    def on_enemy_search(self, event):
        query = self.enemy_search_entry.get().strip().lower()
        self.enemy_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(eid, name) for eid, name in sorted(self.app.edb_master_enemies.items()) if query in name.lower()]
        for eid, name in matches[:20]:
            self.enemy_search_listbox.insert(tk.END, f"{eid} - {name}")

    def on_enemy_search_select(self, event):
        sel = self.enemy_search_listbox.curselection()
        if not sel: return
        text = self.enemy_search_listbox.get(sel[0])
        eid = int(text.split(" - ", 1)[0])
        self.enemy_id_entry.delete(0, tk.END); self.enemy_id_entry.insert(0, str(eid))
        self.enemy_search_entry.delete(0, tk.END)
        self.enemy_search_listbox.delete(0, tk.END)
        self.open_editor_for_id(eid)

    # ------------------------------------------------------------------
    # 목록 추가/삭제/일괄 설정
    # ------------------------------------------------------------------
    def move_enemy(self, direction):
        sel = self.enemy_tree.selection()
        if not sel: return
        eid = int(sel[0])
        enemies = self.cfg.current_config["enemies"]
        idx = next((i for i, e in enumerate(enemies) if e["id"] == eid), None)
        if idx is None: return
        new_idx = idx + direction
        if 0 <= new_idx < len(enemies):
            enemies[idx], enemies[new_idx] = enemies[new_idx], enemies[idx]
            self.cfg.save_config()
            self.app.refresh_all_tabs()

    def add_enemy_rule(self):
        try:
            eid = int(self.enemy_id_entry.get().strip())
        except ValueError:
            messagebox.showerror(t("common.title_error"), t("common.msg_id_must_be_number"))
            return
        self.open_editor_for_id(eid)

    def delete_enemy_rule(self):
        sel = self.enemy_tree.selection()
        if not sel: return
        eid = int(sel[0])
        self.cfg.current_config["enemies"] = [e for e in self.cfg.current_config["enemies"] if e["id"] != eid]
        self.cfg.save_config()
        if self._current_enemy and self._current_enemy.get("id") == eid:
            self._current_enemy = None
            self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("enemy_tab.log_deleted", id=eid))

    def batch_clear_enemies(self):
        if not self.cfg.current_config["enemies"]:
            messagebox.showwarning(t("common.title_warning"), t("enemy_tab.msg_no_enemies"))
            return
        if not messagebox.askyesno(t("enemy_tab.title_confirm_clear"), t("enemy_tab.msg_confirm_clear")): return
        self.cfg.current_config["enemies"] = []
        self.cfg.save_config()
        self._current_enemy = None
        self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("enemy_tab.log_cleared"))

    def batch_reset_extra_options(self):
        """기본 스테이터스(HP/SP/공격력/방어력/정신력/민첩성)를 제외한 나머지
        EasyRPG 옵션을 모두 기본값으로 되돌립니다."""
        if not self.cfg.current_config["enemies"]:
            messagebox.showwarning(t("common.title_warning"), t("enemy_tab.msg_no_enemies"))
            return
        if not messagebox.askyesno(
            t("enemy_tab.title_confirm_reset_extra"),
            t("enemy_tab.msg_confirm_reset_extra")
        ): return
        for en in self.cfg.current_config["enemies"]:
            for fd in ENEMY_FIELD_DEFS:
                if fd["name"] in STAT_FIELDS_FROM_EDB:
                    continue
                en["fields"][fd["name"]] = fd["default"]
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        if self._current_enemy:
            self.render_enemy_detail(self._current_enemy)
        log.info(t("enemy_tab.log_reset_extra_done", count=len(self.cfg.current_config['enemies'])))
        messagebox.showinfo(t("common.title_done"), t("enemy_tab.msg_reset_extra_done", count=len(self.cfg.current_config['enemies'])))
