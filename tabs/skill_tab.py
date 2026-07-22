"""
tabs/skill_tab.py
"스킬 세부 옵션 조절" 탭 - 속성 편집기(Property Editor) 스타일.

좌측: 프로젝트에 등록된 스킬 목록(이름검색으로 추가, 선택해서 삭제)
우측: 선택한 스킬의 EasyRPG 옵션들을 그룹별로 보여주는 고정 크기 편집 패널
      (core.property_panel 재사용 - System/Item 탭과 동일한 방식)
      최상단의 그룹 바로가기 버튼을 누르면 해당 그룹 위치로 스크롤 이동합니다.

검색 결과를 선택하거나 ID를 직접 입력하면(Enter/포커스 아웃), 아직 목록에 없는
스킬이라도 즉시 기본값으로 추가되고 편집 패널이 바로 열립니다 - "추가" 버튼을 누르고
다시 목록에서 선택하는 과정 없이 바로 세부 옵션을 수정할 수 있습니다.

새 EasyRPG 스킬 옵션은 core/skill_schema.py의 SKILL_FIELD_DEFS에 항목만
추가하면 이 탭에 자동으로 나타납니다. HP 소모 방식(easyrpg_hp_type)에 따라
easyrpg_hp_cost / easyrpg_hp_percent 중 관련 없는 쪽은 자동으로 비활성화됩니다.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import (attach_tree_scrollbar, make_listbox_with_scroll,
                         enable_column_sort, enable_column_width_persistence)
from core.property_panel import (make_fixed_scroll_panel, render_field_row, render_group_header,
                                  scroll_panel_to_top, scroll_panel_to_widget, DETAIL_WIDTH, DETAIL_HEIGHT)
from core.skill_schema import SKILL_FIELD_DEFS, default_skill_fields, migrate_skill_entry
from core.logger import log
from core.i18n import t

# 기본 위력/공격력 비율/정신력 비율은 edb에 이미 존재하는 실제 수치를 기본값으로 사용합니다.
STAT_FIELDS_FROM_EDB = ("rating", "physical_rate", "magical_rate")

# 그룹 목록(등장 순서) - 상단 바로가기 버튼에 사용
SKILL_GROUPS_ORDERED = list(dict.fromkeys(fd.get("group", "기타") for fd in SKILL_FIELD_DEFS))


class SkillTab:
    TITLE = t("skill_tab.title")

    def __init__(self, app):
        self.app = app
        self._current_skill = None
        self._group_anchor_widgets = {}

    @property
    def cfg(self):
        return self.app.cfg

    # ------------------------------------------------------------------
    def on_project_loaded(self):
        """예전 버전 프로젝트 설정(스킬 항목이 최상위 rating/crit 등을 갖던 방식)을
        새 스키마({"id":.., "fields": {...}})로 변환합니다. 새로 추가된 필드가 있으면
        기존 스킬에도 기본값으로 채워 넣습니다."""
        skills = self.cfg.current_config.get("skills", [])
        migrated = [migrate_skill_entry(sk) for sk in skills]
        if migrated != skills:
            self.cfg.current_config["skills"] = migrated
            self.cfg.save_config()

    # ------------------------------------------------------------------
    def build(self, notebook):
        skill_frame = ttk.Frame(notebook, padding=10)
        notebook.add(skill_frame, text=self.TITLE)

        left_frame = ttk.Frame(skill_frame)
        left_frame.pack(fill="both", expand=True, side="left")

        columns = ("ID", "이름", "위력", "공격력배율", "정신력배율", "크리티컬확률")
        self.skill_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=18)
        headings = [("ID", t("skill_tab.col_id")), ("이름", t("skill_tab.col_name")), ("위력", t("skill_tab.col_rating")),
                    ("공격력배율", t("skill_tab.col_physical_rate")), ("정신력배율", t("skill_tab.col_magical_rate")),
                    ("크리티컬확률", t("skill_tab.col_crit"))]
        for col, txt in headings: self.skill_tree.heading(col, text=txt)
        attach_tree_scrollbar(self.skill_tree, left_frame)
        self.skill_tree.pack(fill="both", expand=True, side="left")

        self.skill_tree.column("ID", width=50, anchor="center")
        self.skill_tree.column("이름", width=180, anchor="w")
        self.skill_tree.column("위력", width=80, anchor="center")
        self.skill_tree.column("공격력배율", width=90, anchor="center")
        self.skill_tree.column("정신력배율", width=90, anchor="center")
        self.skill_tree.column("크리티컬확률", width=100, anchor="center")
        self.skill_tree.bind("<<TreeviewSelect>>", self.on_skill_select)
        enable_column_sort(self.skill_tree, columns, numeric_columns=("ID", "위력", "공격력배율", "정신력배율", "크리티컬확률"))
        enable_column_width_persistence(self.skill_tree, self.cfg, "skill_tree")

        skill_btn_frame = ttk.Frame(skill_frame, padding=10)
        skill_btn_frame.pack(fill="y", side="right")

        ttk.Label(skill_btn_frame, text=t("common.label_search_name")).pack(anchor="w", pady=(0, 2))
        self.skill_search_entry = ttk.Entry(skill_btn_frame, width=25)
        self.skill_search_entry.pack(anchor="w", pady=(0, 2))
        self.skill_search_entry.bind("<KeyRelease>", self.on_skill_search)
        skill_search_frame, self.skill_search_listbox = make_listbox_with_scroll(skill_btn_frame, height=6)
        skill_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.skill_search_listbox.bind("<<ListboxSelect>>", self.on_skill_search_select)

        ttk.Label(skill_btn_frame, text=t("skill_tab.label_id")).pack(anchor="w", pady=(0, 2))
        self.skill_id_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_id_entry.pack(anchor="w", pady=(0, 2))
        self.skill_id_entry.bind("<KeyRelease>", self.on_id_entry_typed)
        self.skill_id_entry.bind("<Return>", self.on_id_entry_committed)
        self.skill_id_entry.bind("<FocusOut>", self.on_id_entry_committed)
        self.selected_name_var = tk.StringVar(value=t("common.label_selected_name_empty"))
        ttk.Label(skill_btn_frame, textvariable=self.selected_name_var).pack(anchor="w", pady=(0, 10))

        add_del_row = ttk.Frame(skill_btn_frame)
        add_del_row.pack(fill="x", pady=3)
        ttk.Button(add_del_row, text=t("common.btn_add_to_list"), command=self.add_skill_rule).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(add_del_row, text=t("common.btn_remove_from_list"), command=self.delete_skill_rule).pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Label(skill_btn_frame, text=t("common.label_batch_settings")).pack(anchor="w", pady=(20, 4))
        batch_row = ttk.Frame(skill_btn_frame); batch_row.pack(fill="x", pady=2)
        ttk.Button(batch_row, text=t("common.btn_clear_all"), command=self.batch_clear_skills).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(batch_row, text=t("skill_tab.btn_reset_extra"), command=self.batch_reset_extra_options).pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Label(skill_btn_frame, text=t("common.label_detail_editor")).pack(anchor="w", pady=(20, 4))

        # 그룹 개수가 늘어나도 폭이 절대 DETAIL_WIDTH를 넘지 않도록 버튼 나열 대신
        # 드롭다운 하나로 구현합니다 (버튼을 옆으로 계속 늘어놓으면 옵션이 늘어날 때마다
        # 우측 패널 폭이 함께 넓어져서 좌측 목록 영역이 다른 탭보다 좁아지는 문제가 있었습니다).
        nav_frame = ttk.Frame(skill_btn_frame, width=DETAIL_WIDTH)
        nav_frame.pack_propagate(False)
        nav_frame.pack(fill="x", pady=(0, 4))
        ttk.Label(nav_frame, text=t("skill_tab.label_group_jump")).pack(side="left", padx=(0, 4))
        self.group_nav_var = tk.StringVar(value=SKILL_GROUPS_ORDERED[0] if SKILL_GROUPS_ORDERED else "")
        self.group_nav_combo = ttk.Combobox(nav_frame, textvariable=self.group_nav_var,
                                             values=SKILL_GROUPS_ORDERED, state="readonly")
        self.group_nav_combo.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(nav_frame, text=t("skill_tab.btn_jump"), width=5,
                   command=lambda: self.scroll_to_group(self.group_nav_var.get())).pack(side="left")

        self.detail_outer, self.skill_detail_frame = make_fixed_scroll_panel(
            skill_btn_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

    def _show_placeholder(self):
        for w in self.skill_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.skill_detail_frame, text=t("skill_tab.placeholder"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    # ------------------------------------------------------------------
    def refresh(self):
        selected = self.skill_tree.selection()
        prev_iid = selected[0] if selected else None

        for item in self.skill_tree.get_children(): self.skill_tree.delete(item)
        for sk in self.cfg.current_config.get("skills", []):
            sid = sk["id"]
            name = self.app.edb_master_skills.get(sid) or t("common.msg_not_in_master_db")
            fields = sk.get("fields", {})
            rating = fields.get("rating", 0)
            phys = fields.get("physical_rate", 0)
            mag = fields.get("magical_rate", 0)
            crit = fields.get("easyrpg_critical_hit_chance", 0)
            self.skill_tree.insert("", "end", iid=str(sid), values=(sid, name, rating, phys, mag, crit))

        if prev_iid and self.skill_tree.exists(prev_iid):
            self.skill_tree.selection_set(prev_iid)
            self.skill_tree.see(prev_iid)

    # ------------------------------------------------------------------
    def _update_selected_name_label(self, iid_text):
        try:
            iid = int(iid_text.strip())
        except ValueError:
            self.selected_name_var.set(t("common.label_selected_name_empty"))
            return
        name = self.app.edb_master_skills.get(iid)
        self.selected_name_var.set(t("common.label_selected_name", name=name) if name else t("common.label_selected_name_unknown"))

    def on_id_entry_typed(self, event):
        self._update_selected_name_label(self.skill_id_entry.get())

    def on_id_entry_committed(self, event):
        raw = self.skill_id_entry.get().strip()
        if not raw:
            return
        try:
            sid = int(raw)
        except ValueError:
            return
        self.open_editor_for_id(sid)

    # ------------------------------------------------------------------
    # 좌측 목록 선택 -> 우측 속성 편집기 렌더링
    # ------------------------------------------------------------------
    def on_skill_select(self, event):
        selected = self.skill_tree.selection()
        if not selected: return
        sid = int(selected[0])
        sk = next((s for s in self.cfg.current_config["skills"] if s["id"] == sid), None)
        if sk:
            self.skill_id_entry.delete(0, tk.END); self.skill_id_entry.insert(0, str(sid))
            self._update_selected_name_label(str(sid))
            self.render_skill_detail(sk)

    def open_editor_for_id(self, sid):
        """ID(검색 선택 또는 직접 입력)만으로 즉시 편집 패널을 엽니다.
        아직 목록에 없는 스킬이면 기본값(가능하면 edb의 실제 위력/비율 값)으로 자동 추가합니다."""
        self._update_selected_name_label(str(sid))
        existing = next((s for s in self.cfg.current_config["skills"] if s["id"] == sid), None)
        if existing is None:
            if sid not in self.app.edb_master_skills:
                if not messagebox.askyesno(t("common.title_warning"), t("skill_tab.msg_confirm_add_unknown")):
                    return
            fields = default_skill_fields()
            real_stats = self.app.edb_master_skill_stats.get(sid, {})
            for key in STAT_FIELDS_FROM_EDB:
                if key in real_stats:
                    fields[key] = real_stats[key]
            existing = {"id": sid, "fields": fields}
            self.cfg.current_config["skills"].append(existing)
            self.cfg.save_config()
            log.info(t("skill_tab.log_added", id=sid))
            self.app.refresh_all_tabs()

        if self.skill_tree.exists(str(sid)):
            self.skill_tree.selection_set(str(sid))
            self.skill_tree.see(str(sid))
        self.render_skill_detail(existing)

    def render_skill_detail(self, sk):
        for w in self.skill_detail_frame.winfo_children():
            w.destroy()
        self._current_skill = sk
        self._group_anchor_widgets = {}
        fields = sk["fields"]
        p = self.skill_detail_frame

        name = self.app.edb_master_skills.get(sk["id"], t("common.name_unknown"))
        ttk.Label(p, text=t("skill_tab.detail_header", id=sk['id'], name=name), font=("Segoe UI", 10, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 4))

        last_group = None
        for fd in SKILL_FIELD_DEFS:
            group = fd.get("group", "기타")
            if group != last_group:
                header_holder = ttk.Frame(p)
                header_holder.pack(fill="x", padx=8)
                render_group_header(header_holder, group)
                self._group_anchor_widgets[group] = header_holder
                last_group = group

            row = ttk.Frame(p)
            row.pack(fill="x", padx=8)

            enabled = True
            cond = fd.get("enabled_when")
            if cond:
                enabled = fields.get(cond["field"]) == cond["equals"]

            control, set_enabled = render_field_row(
                row, fd, fields.get(fd["name"], fd["default"]), self._make_on_change(fd["name"])
            )
            set_enabled(enabled)

        scroll_panel_to_top(self.detail_outer)

    def scroll_to_group(self, group_name):
        if self._current_skill is None:
            return
        scroll_panel_to_widget(self.detail_outer, self._group_anchor_widgets.get(group_name))

    def _make_on_change(self, field_name):
        def _on_change(new_val):
            self._current_skill["fields"][field_name] = new_val
            self.cfg.save_config()
            self.app.refresh_all_tabs()
            log.info(t("skill_tab.log_field_changed", id=self._current_skill["id"], field=field_name, value=new_val))
            # 위젯을 그리던 이벤트(FocusOut 등) 처리가 끝난 뒤 안전하게 다시 그림
            # (예: HP 소모 방식이 바뀌면 관련 필드의 활성/비활성 상태를 새로 계산)
            self.skill_detail_frame.after_idle(lambda: self.render_skill_detail(self._current_skill))
        return _on_change

    # ------------------------------------------------------------------
    # 이름 검색 (드롭다운) - 선택하면 즉시 편집 패널이 열림
    # ------------------------------------------------------------------
    def on_skill_search(self, event):
        query = self.skill_search_entry.get().strip().lower()
        self.skill_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(sid, name) for sid, name in sorted(self.app.edb_master_skills.items()) if query in name.lower()]
        for sid, name in matches[:20]:
            self.skill_search_listbox.insert(tk.END, f"{sid} - {name}")

    def on_skill_search_select(self, event):
        sel = self.skill_search_listbox.curselection()
        if not sel: return
        text = self.skill_search_listbox.get(sel[0])
        sid = int(text.split(" - ", 1)[0])
        self.skill_id_entry.delete(0, tk.END); self.skill_id_entry.insert(0, str(sid))
        self.skill_search_entry.delete(0, tk.END)
        self.skill_search_listbox.delete(0, tk.END)
        self.open_editor_for_id(sid)

    # ------------------------------------------------------------------
    # 스킬 목록 추가/삭제/일괄 설정
    # ------------------------------------------------------------------
    def add_skill_rule(self):
        try:
            sid = int(self.skill_id_entry.get().strip())
        except ValueError:
            messagebox.showerror(t("common.title_error"), t("common.msg_id_must_be_number"))
            return
        self.open_editor_for_id(sid)

    def delete_skill_rule(self):
        sel = self.skill_tree.selection()
        if not sel: return
        sid = int(sel[0])
        self.cfg.current_config["skills"] = [s for s in self.cfg.current_config["skills"] if s["id"] != sid]
        self.cfg.save_config()
        if self._current_skill and self._current_skill.get("id") == sid:
            self._current_skill = None
            self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("skill_tab.log_deleted", id=sid))

    def batch_clear_skills(self):
        if not self.cfg.current_config["skills"]:
            messagebox.showwarning(t("common.title_warning"), t("skill_tab.msg_no_skills"))
            return
        if not messagebox.askyesno(t("skill_tab.title_confirm_clear"), t("skill_tab.msg_confirm_clear")): return
        self.cfg.current_config["skills"] = []
        self.cfg.save_config()
        self._current_skill = None
        self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("skill_tab.log_cleared"))

    def batch_reset_extra_options(self):
        """기본 위력/공격력 비율/정신력 비율을 제외한 나머지 세부 옵션을 모두 기본값으로 되돌립니다."""
        if not self.cfg.current_config["skills"]:
            messagebox.showwarning(t("common.title_warning"), t("skill_tab.msg_no_skills"))
            return
        if not messagebox.askyesno(
            t("skill_tab.title_confirm_reset_extra"),
            t("skill_tab.msg_confirm_reset_extra")
        ): return
        for sk in self.cfg.current_config["skills"]:
            for fd in SKILL_FIELD_DEFS:
                if fd["name"] in STAT_FIELDS_FROM_EDB:
                    continue
                sk["fields"][fd["name"]] = fd["default"]
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        if self._current_skill:
            self.render_skill_detail(self._current_skill)
        log.info(t("skill_tab.log_reset_extra_done", count=len(self.cfg.current_config['skills'])))
        messagebox.showinfo(t("common.title_done"), t("skill_tab.msg_reset_extra_done", count=len(self.cfg.current_config['skills'])))
