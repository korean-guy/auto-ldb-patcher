"""
tabs/actor_tab.py
"액터 세부 옵션 조절" 탭 - 속성 편집기(Property Editor) 스타일.
LDB의 <actors><Actor> 데이터를 다룹니다.

- 레벨 상한(final_level)은 절대 상한 255, 그리고 System 탭의 '최대 레벨'
  (easyrpg_max_level, -1이면 제한 없음) 설정을 넘을 수 없도록 자동으로 clamp됩니다.
- 레벨 상한을 바꾸면 maxhp/maxsp/attack/defense/spirit/agility 6개 능력치 성장
  배열의 길이가 자동으로 늘어나거나(마지막 값 반복) 줄어들어(뒤에서부터 자름)
  항상 레벨 상한과 정확히 같은 개수를 유지합니다 (개수 불일치로 인한 오버플로우 방지).
- [기본값] 버튼은 스키마 기본값이 아니라, 이 액터를 처음 목록에 추가했을 때(=EDB를
  처음 불러왔을 때) 값으로 되돌립니다.
- [전체 일괄 설정] 버튼은 현재 선택된 액터의 설정을 등록된 모든 액터에게 적용합니다
  (능력치 성장 배열은 각 액터의 레벨 상한에 맞춰 개별적으로 다시 조정됩니다).
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import (attach_tree_scrollbar, make_listbox_with_scroll,
                         enable_column_sort, enable_column_width_persistence, FG_DIM)
from core.context_menu import attach_row_context_menu
from core.property_panel import (make_fixed_scroll_panel, render_field_row, render_group_header,
                                  scroll_panel_to_top, scroll_panel_to_widget, DETAIL_WIDTH, DETAIL_HEIGHT)
from core.actor_schema import (ACTOR_FIELD_DEFS, STAT_ARRAY_KEYS, STAT_ARRAY_LABELS, ABSOLUTE_MAX_LEVEL,
                                default_actor_fields, migrate_actor_entry, resize_stat_array)
from core.logger import log
from core.i18n import t

ACTOR_GROUPS_ORDERED = [t("actor_tab.group_level")] + list(dict.fromkeys(fd.get("group", "기타") for fd in ACTOR_FIELD_DEFS))


class ActorTab:
    TITLE = t("actor_tab.title")

    def __init__(self, app):
        self.app = app
        self._current_actor = None
        self._group_anchor_widgets = {}

    @property
    def cfg(self):
        return self.app.cfg

    # ------------------------------------------------------------------
    def on_project_loaded(self):
        if "actors" not in self.cfg.current_config:
            self.cfg.current_config["actors"] = []
        actors = self.cfg.current_config.get("actors", [])
        migrated = [migrate_actor_entry(a) for a in actors]
        if migrated != actors:
            self.cfg.current_config["actors"] = migrated
            self.cfg.save_config()

    # ------------------------------------------------------------------
    def build(self, notebook):
        actor_frame = ttk.Frame(notebook, padding=10)
        notebook.add(actor_frame, text=self.TITLE)

        left_frame = ttk.Frame(actor_frame)
        left_frame.pack(fill="both", expand=True, side="left")

        columns = ("ID", "이름", "레벨상한")
        self.actor_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=18)
        for col, txt in [("ID", t("actor_tab.col_id")), ("이름", t("actor_tab.col_name")),
                          ("레벨상한", t("actor_tab.col_final_level"))]:
            self.actor_tree.heading(col, text=txt)
        attach_tree_scrollbar(self.actor_tree, left_frame)
        self.actor_tree.pack(fill="both", expand=True, side="left")

        self.actor_tree.column("ID", width=50, anchor="center")
        self.actor_tree.column("이름", width=220, anchor="w")
        self.actor_tree.column("레벨상한", width=100, anchor="center")
        self.actor_tree.bind("<<TreeviewSelect>>", self.on_actor_select)
        enable_column_sort(self.actor_tree, columns, numeric_columns=("ID", "레벨상한"))
        enable_column_width_persistence(self.actor_tree, self.cfg, "actor_tree")
        attach_row_context_menu(self.actor_tree, lambda: self.move_actor(-1), lambda: self.move_actor(1), self.delete_actor_rule)

        actor_btn_frame = ttk.Frame(actor_frame, padding=10)
        actor_btn_frame.pack(fill="y", side="right")

        ttk.Label(actor_btn_frame, text=t("common.label_search_name")).pack(anchor="w", pady=(0, 2))
        self.actor_search_entry = ttk.Entry(actor_btn_frame, width=25)
        self.actor_search_entry.pack(anchor="w", pady=(0, 2))
        self.actor_search_entry.bind("<KeyRelease>", self.on_actor_search)
        actor_search_frame, self.actor_search_listbox = make_listbox_with_scroll(actor_btn_frame, height=6)
        actor_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.actor_search_listbox.bind("<<ListboxSelect>>", self.on_actor_search_select)

        ttk.Label(actor_btn_frame, text=t("actor_tab.label_id")).pack(anchor="w", pady=(0, 2))
        self.actor_id_entry = ttk.Entry(actor_btn_frame, width=25); self.actor_id_entry.pack(anchor="w", pady=(0, 2))
        self.actor_id_entry.bind("<KeyRelease>", self.on_id_entry_typed)
        self.actor_id_entry.bind("<Return>", self.on_id_entry_committed)
        self.actor_id_entry.bind("<FocusOut>", self.on_id_entry_committed)
        self.selected_name_var = tk.StringVar(value=t("common.label_selected_name_empty"))
        ttk.Label(actor_btn_frame, textvariable=self.selected_name_var).pack(anchor="w", pady=(0, 10))

        add_del_row = ttk.Frame(actor_btn_frame)
        add_del_row.pack(fill="x", pady=3)
        ttk.Button(add_del_row, text=t("common.btn_add_to_list"), command=self.add_actor_rule).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(add_del_row, text=t("common.btn_remove_from_list"), command=self.delete_actor_rule).pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Label(actor_btn_frame, text=t("common.label_batch_settings")).pack(anchor="w", pady=(20, 4))
        batch_row1 = ttk.Frame(actor_btn_frame); batch_row1.pack(fill="x", pady=2)
        ttk.Button(batch_row1, text=t("actor_tab.btn_restore_original"), command=self.restore_original).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(batch_row1, text=t("actor_tab.btn_batch_apply"), command=self.batch_apply_to_all).pack(side="left", expand=True, fill="x", padx=(2, 0))
        ttk.Button(actor_btn_frame, text=t("common.btn_clear_all"), command=self.batch_clear_actors).pack(fill="x", pady=2)

        ttk.Label(actor_btn_frame, text=t("common.label_detail_editor")).pack(anchor="w", pady=(20, 4))

        nav_frame = ttk.Frame(actor_btn_frame, width=DETAIL_WIDTH)
        nav_frame.pack_propagate(False)
        nav_frame.pack(fill="x", pady=(0, 4))
        ttk.Label(nav_frame, text=t("skill_tab.label_group_jump")).pack(side="left", padx=(0, 4))
        self.group_nav_var = tk.StringVar(value=ACTOR_GROUPS_ORDERED[0] if ACTOR_GROUPS_ORDERED else "")
        self.group_nav_combo = ttk.Combobox(nav_frame, textvariable=self.group_nav_var,
                                             values=ACTOR_GROUPS_ORDERED, state="readonly")
        self.group_nav_combo.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(nav_frame, text=t("skill_tab.btn_jump"), width=5,
                   command=lambda: self.scroll_to_group(self.group_nav_var.get())).pack(side="left")

        self.detail_outer, self.actor_detail_frame = make_fixed_scroll_panel(
            actor_btn_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

    def _show_placeholder(self):
        for w in self.actor_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.actor_detail_frame, text=t("actor_tab.placeholder"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    # ------------------------------------------------------------------
    def refresh(self):
        selected = self.actor_tree.selection()
        prev_iid = selected[0] if selected else None

        for item in self.actor_tree.get_children(): self.actor_tree.delete(item)
        for ac in self.cfg.current_config.get("actors", []):
            aid = ac["id"]
            name = self.app.edb_master_actors.get(aid) or t("common.msg_not_in_master_db")
            self.actor_tree.insert("", "end", iid=str(aid), values=(aid, name, ac.get("final_level", "-")))

        if prev_iid and self.actor_tree.exists(prev_iid):
            self.actor_tree.selection_set(prev_iid)
            self.actor_tree.see(prev_iid)

    # ------------------------------------------------------------------
    def _update_selected_name_label(self, iid_text):
        try:
            iid = int(iid_text.strip())
        except ValueError:
            self.selected_name_var.set(t("common.label_selected_name_empty"))
            return
        name = self.app.edb_master_actors.get(iid)
        self.selected_name_var.set(t("common.label_selected_name", name=name) if name else t("common.label_selected_name_unknown"))

    def on_id_entry_typed(self, event):
        self._update_selected_name_label(self.actor_id_entry.get())

    def on_id_entry_committed(self, event):
        raw = self.actor_id_entry.get().strip()
        if not raw:
            return
        try:
            aid = int(raw)
        except ValueError:
            return
        self.open_editor_for_id(aid)

    def on_actor_select(self, event):
        selected = self.actor_tree.selection()
        if not selected: return
        aid = int(selected[0])
        ac = next((a for a in self.cfg.current_config["actors"] if a["id"] == aid), None)
        if ac:
            self.actor_id_entry.delete(0, tk.END); self.actor_id_entry.insert(0, str(aid))
            self._update_selected_name_label(str(aid))
            self.render_actor_detail(ac)

    def _max_allowed_level(self):
        sys_def = self.cfg.find_sys_def("easyrpg_max_level")
        sys_max = sys_def.get("value") if sys_def else -1
        if sys_max is None or sys_max == -1:
            return ABSOLUTE_MAX_LEVEL
        return max(1, min(ABSOLUTE_MAX_LEVEL, sys_max))

    def open_editor_for_id(self, aid):
        """ID(검색 선택 또는 직접 입력)만으로 즉시 편집 패널을 엽니다.
        아직 목록에 없는 액터면 edb의 실제 값으로 자동 추가합니다."""
        self._update_selected_name_label(str(aid))
        existing = next((a for a in self.cfg.current_config["actors"] if a["id"] == aid), None)
        if existing is None:
            if aid not in self.app.edb_master_actors:
                if not messagebox.askyesno(t("common.title_warning"), t("actor_tab.msg_confirm_add_unknown")):
                    return
            edb_data = self.app.edb_master_actor_data.get(aid, {})
            fields = default_actor_fields()
            for fd in ACTOR_FIELD_DEFS:
                if fd["name"] in edb_data:
                    fields[fd["name"]] = edb_data[fd["name"]]
            final_level = edb_data.get("final_level", ABSOLUTE_MAX_LEVEL)
            parameters = {k: resize_stat_array(edb_data.get("parameters", {}).get(k, []), final_level) for k in STAT_ARRAY_KEYS}

            existing = {
                "id": aid, "fields": fields, "final_level": final_level, "parameters": parameters,
                "original_fields": dict(fields), "original_final_level": final_level,
                "original_parameters": {k: list(v) for k, v in parameters.items()},
            }
            self.cfg.current_config["actors"].append(existing)
            self.cfg.save_config()
            log.info(t("actor_tab.log_added", id=aid))
            self.app.refresh_all_tabs()

        if self.actor_tree.exists(str(aid)):
            self.actor_tree.selection_set(str(aid))
            self.actor_tree.see(str(aid))
        self.render_actor_detail(existing)

    def render_actor_detail(self, ac):
        for w in self.actor_detail_frame.winfo_children():
            w.destroy()
        self._current_actor = ac
        self._group_anchor_widgets = {}
        fields = ac["fields"]
        p = self.actor_detail_frame

        name = self.app.edb_master_actors.get(ac["id"], t("common.name_unknown"))
        ttk.Label(p, text=t("actor_tab.detail_header", id=ac["id"], name=name), font=("Segoe UI", 10, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 4))

        # ---- 레벨 상한 (특수 처리: clamp + 능력치 성장 배열 자동 리사이즈) ----
        level_group = t("actor_tab.group_level")
        header_holder = ttk.Frame(p); header_holder.pack(fill="x", padx=8)
        render_group_header(header_holder, level_group)
        self._group_anchor_widgets[level_group] = header_holder

        level_row = ttk.Frame(p); level_row.pack(fill="x", padx=8)
        ttk.Label(level_row, text=t("actor_tab.label_final_level"), font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
        max_allowed = self._max_allowed_level()
        ttk.Label(level_row, text=t("actor_tab.desc_final_level", max=max_allowed), foreground=FG_DIM,
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w")
        level_entry = ttk.Entry(level_row, width=22)
        level_entry.insert(0, str(ac.get("final_level", max_allowed)))
        level_entry.pack(anchor="w", pady=(2, 4))

        def _commit_level(event=None):
            raw = level_entry.get().strip()
            try:
                v = int(raw)
            except ValueError:
                level_entry.delete(0, tk.END); level_entry.insert(0, str(ac.get("final_level", max_allowed)))
                return
            v = max(1, min(v, self._max_allowed_level()))
            if str(v) != raw:
                level_entry.delete(0, tk.END); level_entry.insert(0, str(v))
            if v != ac.get("final_level"):
                self.apply_final_level(ac, v)

        level_entry._commit = _commit_level  # 테스트/자동화에서 커밋 로직을 직접 호출할 수 있도록 노출
        level_entry.bind("<Return>", _commit_level)
        level_entry.bind("<FocusOut>", _commit_level)

        stat_info = ", ".join(f"{STAT_ARRAY_LABELS[k]} {len(ac.get('parameters', {}).get(k, []))}단계" for k in STAT_ARRAY_KEYS)
        ttk.Label(level_row, text=t("actor_tab.stat_array_info", info=stat_info), foreground=FG_DIM,
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", pady=(4, 8))

        # ---- 나머지 그룹 (경험치/AI/전투/맨손 공격) ----
        last_group = None
        for fd in ACTOR_FIELD_DEFS:
            group = fd.get("group", "기타")
            if group != last_group:
                header_holder2 = ttk.Frame(p); header_holder2.pack(fill="x", padx=8)
                render_group_header(header_holder2, group)
                self._group_anchor_widgets[group] = header_holder2
                last_group = group

            row = ttk.Frame(p); row.pack(fill="x", padx=8)
            control, set_enabled = render_field_row(
                row, fd, fields.get(fd["name"], fd["default"]), self._make_on_change(fd["name"])
            )
            set_enabled(True)

        scroll_panel_to_top(self.detail_outer)

    def scroll_to_group(self, group_name):
        if self._current_actor is None:
            return
        scroll_panel_to_widget(self.detail_outer, self._group_anchor_widgets.get(group_name))

    def apply_final_level(self, ac, new_level):
        ac["final_level"] = new_level
        parameters = ac.setdefault("parameters", {})
        for key in STAT_ARRAY_KEYS:
            parameters[key] = resize_stat_array(parameters.get(key, []), new_level)
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        log.info(t("actor_tab.log_level_changed", id=ac["id"], level=new_level))
        self.actor_detail_frame.after_idle(lambda: self.render_actor_detail(ac))

    def _make_on_change(self, field_name):
        def _on_change(new_val):
            self._current_actor["fields"][field_name] = new_val
            self.cfg.save_config()
            self.app.refresh_all_tabs()
            log.info(t("actor_tab.log_field_changed", id=self._current_actor["id"], field=field_name, value=new_val))
            self.actor_detail_frame.after_idle(lambda: self.render_actor_detail(self._current_actor))
        return _on_change

    # ------------------------------------------------------------------
    # 이름 검색 (드롭다운) - 선택하면 즉시 편집 패널이 열림
    # ------------------------------------------------------------------
    def on_actor_search(self, event):
        query = self.actor_search_entry.get().strip().lower()
        self.actor_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(aid, name) for aid, name in sorted(self.app.edb_master_actors.items()) if query in name.lower()]
        for aid, name in matches[:20]:
            self.actor_search_listbox.insert(tk.END, f"{aid} - {name}")

    def on_actor_search_select(self, event):
        sel = self.actor_search_listbox.curselection()
        if not sel: return
        text = self.actor_search_listbox.get(sel[0])
        aid = int(text.split(" - ", 1)[0])
        self.actor_id_entry.delete(0, tk.END); self.actor_id_entry.insert(0, str(aid))
        self.actor_search_entry.delete(0, tk.END)
        self.actor_search_listbox.delete(0, tk.END)
        self.open_editor_for_id(aid)

    # ------------------------------------------------------------------
    # 목록 추가/삭제/이동/일괄 설정
    # ------------------------------------------------------------------
    def add_actor_rule(self):
        try:
            aid = int(self.actor_id_entry.get().strip())
        except ValueError:
            messagebox.showerror(t("common.title_error"), t("common.msg_id_must_be_number"))
            return
        self.open_editor_for_id(aid)

    def move_actor(self, direction):
        sel = self.actor_tree.selection()
        if not sel: return
        aid = int(sel[0])
        actors = self.cfg.current_config["actors"]
        idx = next((i for i, a in enumerate(actors) if a["id"] == aid), None)
        if idx is None: return
        new_idx = idx + direction
        if 0 <= new_idx < len(actors):
            actors[idx], actors[new_idx] = actors[new_idx], actors[idx]
            self.cfg.save_config()
            self.app.refresh_all_tabs()

    def delete_actor_rule(self):
        sel = self.actor_tree.selection()
        if not sel: return
        aid = int(sel[0])
        self.cfg.current_config["actors"] = [a for a in self.cfg.current_config["actors"] if a["id"] != aid]
        self.cfg.save_config()
        if self._current_actor and self._current_actor.get("id") == aid:
            self._current_actor = None
            self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("actor_tab.log_deleted", id=aid))

    def batch_clear_actors(self):
        if not self.cfg.current_config["actors"]:
            messagebox.showwarning(t("common.title_warning"), t("actor_tab.msg_no_actors"))
            return
        if not messagebox.askyesno(t("actor_tab.title_confirm_clear"), t("actor_tab.msg_confirm_clear")): return
        self.cfg.current_config["actors"] = []
        self.cfg.save_config()
        self._current_actor = None
        self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("actor_tab.log_cleared"))

    def restore_original(self):
        ac = self._current_actor
        if not ac:
            messagebox.showwarning(t("common.title_warning"), t("actor_tab.msg_no_actors"))
            return
        if not messagebox.askyesno(t("actor_tab.title_confirm_restore"), t("actor_tab.msg_confirm_restore")): return
        ac["fields"] = dict(ac["original_fields"])
        ac["final_level"] = ac["original_final_level"]
        ac["parameters"] = {k: list(v) for k, v in ac["original_parameters"].items()}
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        self.render_actor_detail(ac)
        log.info(t("actor_tab.log_restore_done", id=ac["id"]))
        messagebox.showinfo(t("common.title_done"), t("actor_tab.msg_restore_done", id=ac["id"]))

    def batch_apply_to_all(self):
        ac = self._current_actor
        if not ac:
            messagebox.showwarning(t("common.title_warning"), t("actor_tab.msg_no_actors"))
            return
        actors = self.cfg.current_config["actors"]
        if not actors:
            messagebox.showwarning(t("common.title_warning"), t("actor_tab.msg_no_actors"))
            return
        name = self.app.edb_master_actors.get(ac["id"], t("common.name_unknown"))
        if not messagebox.askyesno(
            t("actor_tab.title_confirm_batch_apply"),
            t("actor_tab.msg_confirm_batch_apply", name=name, count=len(actors))
        ): return

        max_allowed = self._max_allowed_level()
        target_level = max(1, min(ac.get("final_level", max_allowed), max_allowed))
        for other in actors:
            other["fields"] = dict(ac["fields"])
            other["final_level"] = target_level
            other_params = other.setdefault("parameters", {})
            for key in STAT_ARRAY_KEYS:
                other_params[key] = resize_stat_array(other_params.get(key, []), target_level)

        self.cfg.save_config()
        self.app.refresh_all_tabs()
        if self._current_actor:
            self.render_actor_detail(self._current_actor)
        log.info(t("actor_tab.log_batch_apply_done", count=len(actors)))
        messagebox.showinfo(t("common.title_done"), t("actor_tab.msg_batch_apply_done", count=len(actors)))
