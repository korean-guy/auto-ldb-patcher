"""
tabs/class_tab.py
"클래스 세부 옵션 조절" 탭. LDB의 <classes><Class> 데이터를 다룹니다.
구조는 Item/Actor 탭과 동일한 패턴(좌측 목록 + 우측 속성 편집기)이며,
능력치 편집 팝업은 Actor 탭과 완전히 같은 공통 컴포넌트(core/stat_editor_popup.py)를
재사용합니다.

클래스는 Actor와 달리 자체 레벨 상한(final_level) 필드가 없다고 보고, System 탭의
'최대 레벨' 설정을 그대로 따릅니다 (능력치 성장 배열 길이가 여기에 맞춰집니다).
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import (attach_tree_scrollbar, make_listbox_with_scroll,
                         enable_column_sort, enable_column_width_persistence)
from core.context_menu import attach_row_context_menu
from core.property_panel import make_fixed_scroll_panel, render_field_row, render_group_header, DETAIL_WIDTH, DETAIL_HEIGHT
from core.class_schema import CLASS_FIELD_DEFS, default_class_fields, migrate_class_entry
from core.actor_schema import STAT_ARRAY_KEYS, ABSOLUTE_MAX_LEVEL, resize_stat_array
from core.stat_editor_popup import open_stat_editor_popup
from core.logger import log
from core.i18n import t

STAT_POPUP_KEYS = ["maxhp", "maxsp", "attack", "defense", "spirit", "agility"]
STAT_POPUP_LABEL_KEYS = {
    "maxhp": "stat_label.maxhp", "maxsp": "stat_label.maxsp",
    "attack": "stat_label.attack", "defense": "stat_label.defense",
    "spirit": "stat_label.spirit", "agility": "stat_label.agility",
}


class ClassTab:
    TITLE = t("class_tab.title")

    def __init__(self, app):
        self.app = app
        self._current_class = None

    @property
    def cfg(self):
        return self.app.cfg

    # ------------------------------------------------------------------
    def on_project_loaded(self):
        if "classes" not in self.cfg.current_config:
            self.cfg.current_config["classes"] = []
        classes = self.cfg.current_config.get("classes", [])
        migrated = [migrate_class_entry(c) for c in classes]
        if migrated != classes:
            self.cfg.current_config["classes"] = migrated
            self.cfg.save_config()

    def _max_allowed_level(self):
        sys_def = self.cfg.find_sys_def("easyrpg_max_level")
        sys_max = sys_def.get("value") if sys_def else -1
        if sys_max is None or sys_max == -1:
            return ABSOLUTE_MAX_LEVEL
        return max(1, min(ABSOLUTE_MAX_LEVEL, sys_max))

    # ------------------------------------------------------------------
    def build(self, notebook):
        class_frame = ttk.Frame(notebook, padding=10)
        notebook.add(class_frame, text=self.TITLE)

        left_frame = ttk.Frame(class_frame)
        left_frame.pack(fill="both", expand=True, side="left")

        columns = ("ID", "이름", "능력치조절")
        self.class_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=18)
        for col, txt in [("ID", t("class_tab.col_id")), ("이름", t("class_tab.col_name")),
                          ("능력치조절", t("class_tab.col_stat_edit"))]:
            self.class_tree.heading(col, text=txt)
        attach_tree_scrollbar(self.class_tree, left_frame)
        self.class_tree.pack(fill="both", expand=True, side="left")

        self.class_tree.column("ID", width=50, anchor="center")
        self.class_tree.column("이름", width=220, anchor="w")
        self.class_tree.column("능력치조절", width=100, anchor="center")
        self.class_tree.bind("<<TreeviewSelect>>", self.on_class_select)
        self.class_tree.bind("<Button-1>", self.on_class_tree_click)
        enable_column_sort(self.class_tree, columns, numeric_columns=("ID",))
        enable_column_width_persistence(self.class_tree, self.cfg, "class_tree")
        attach_row_context_menu(self.class_tree, lambda: self.move_class(-1), lambda: self.move_class(1), self.delete_class_rule)

        class_btn_frame = ttk.Frame(class_frame, padding=10)
        class_btn_frame.pack(fill="y", side="right")

        ttk.Label(class_btn_frame, text=t("common.label_search_name")).pack(anchor="w", pady=(0, 2))
        self.class_search_entry = ttk.Entry(class_btn_frame, width=25)
        self.class_search_entry.pack(anchor="w", pady=(0, 2))
        self.class_search_entry.bind("<KeyRelease>", self.on_class_search)
        class_search_frame, self.class_search_listbox = make_listbox_with_scroll(class_btn_frame, height=6)
        class_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.class_search_listbox.bind("<<ListboxSelect>>", self.on_class_search_select)

        ttk.Label(class_btn_frame, text=t("class_tab.label_id")).pack(anchor="w", pady=(0, 2))
        self.class_id_entry = ttk.Entry(class_btn_frame, width=25); self.class_id_entry.pack(anchor="w", pady=(0, 2))
        self.class_id_entry.bind("<KeyRelease>", self.on_id_entry_typed)
        self.class_id_entry.bind("<Return>", self.on_id_entry_committed)
        self.class_id_entry.bind("<FocusOut>", self.on_id_entry_committed)
        self.selected_name_var = tk.StringVar(value=t("common.label_selected_name_empty"))
        ttk.Label(class_btn_frame, textvariable=self.selected_name_var).pack(anchor="w", pady=(0, 10))

        add_del_row = ttk.Frame(class_btn_frame)
        add_del_row.pack(fill="x", pady=3)
        ttk.Button(add_del_row, text=t("common.btn_add_to_list"), command=self.add_class_rule).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(add_del_row, text=t("common.btn_remove_from_list"), command=self.delete_class_rule).pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Label(class_btn_frame, text=t("common.label_batch_settings")).pack(anchor="w", pady=(20, 4))
        ttk.Button(class_btn_frame, text=t("common.btn_clear_all"), command=self.batch_clear_classes).pack(fill="x", pady=2)

        ttk.Label(class_btn_frame, text=t("common.label_detail_editor")).pack(anchor="w", pady=(20, 4))
        self.detail_outer, self.class_detail_frame = make_fixed_scroll_panel(
            class_btn_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

    def _show_placeholder(self):
        for w in self.class_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.class_detail_frame, text=t("class_tab.placeholder"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    # ------------------------------------------------------------------
    def refresh(self):
        selected = self.class_tree.selection()
        prev_iid = selected[0] if selected else None

        for item in self.class_tree.get_children(): self.class_tree.delete(item)
        for cl in self.cfg.current_config.get("classes", []):
            cid = cl["id"]
            name = self.app.edb_master_classes.get(cid) or t("common.msg_not_in_master_db")
            self.class_tree.insert("", "end", iid=str(cid), values=(cid, name, t("actor_tab.btn_stat_edit")))

        if prev_iid and self.class_tree.exists(prev_iid):
            self.class_tree.selection_set(prev_iid)
            self.class_tree.see(prev_iid)

    def on_class_tree_click(self, event):
        region = self.class_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.class_tree.identify_column(event.x)
        row = self.class_tree.identify_row(event.y)
        if not row:
            return
        if col == "#3":
            cid = int(row)
            cl = next((c for c in self.cfg.current_config["classes"] if c["id"] == cid), None)
            if cl:
                self.open_stat_editor_popup(cl)

    # ------------------------------------------------------------------
    def _update_selected_name_label(self, iid_text):
        try:
            iid = int(iid_text.strip())
        except ValueError:
            self.selected_name_var.set(t("common.label_selected_name_empty"))
            return
        name = self.app.edb_master_classes.get(iid)
        self.selected_name_var.set(t("common.label_selected_name", name=name) if name else t("common.label_selected_name_unknown"))

    def on_id_entry_typed(self, event):
        self._update_selected_name_label(self.class_id_entry.get())

    def on_id_entry_committed(self, event):
        raw = self.class_id_entry.get().strip()
        if not raw:
            return
        try:
            cid = int(raw)
        except ValueError:
            return
        self.open_editor_for_id(cid)

    def on_class_select(self, event):
        selected = self.class_tree.selection()
        if not selected: return
        cid = int(selected[0])
        cl = next((c for c in self.cfg.current_config["classes"] if c["id"] == cid), None)
        if cl:
            self.class_id_entry.delete(0, tk.END); self.class_id_entry.insert(0, str(cid))
            self._update_selected_name_label(str(cid))
            self.render_class_detail(cl)

    def open_editor_for_id(self, cid):
        self._update_selected_name_label(str(cid))
        existing = next((c for c in self.cfg.current_config["classes"] if c["id"] == cid), None)
        if existing is None:
            if cid not in self.app.edb_master_classes:
                if not messagebox.askyesno(t("common.title_warning"), t("class_tab.msg_confirm_add_unknown")):
                    return
            edb_data = self.app.edb_master_class_data.get(cid, {})
            fields = default_class_fields()
            for fd in CLASS_FIELD_DEFS:
                if fd["name"] in edb_data:
                    fields[fd["name"]] = edb_data[fd["name"]]
            level = self._max_allowed_level()
            parameters = {k: resize_stat_array(edb_data.get("parameters", {}).get(k, []), level) for k in STAT_ARRAY_KEYS}

            existing = {"id": cid, "fields": fields, "parameters": parameters}
            self.cfg.current_config["classes"].append(existing)
            self.cfg.save_config()
            log.info(t("class_tab.log_added", id=cid))
            self.app.refresh_all_tabs()

        if self.class_tree.exists(str(cid)):
            self.class_tree.selection_set(str(cid))
            self.class_tree.see(str(cid))
        self.render_class_detail(existing)

    def render_class_detail(self, cl):
        for w in self.class_detail_frame.winfo_children():
            w.destroy()
        self._current_class = cl
        fields = cl["fields"]
        p = self.class_detail_frame

        name = self.app.edb_master_classes.get(cl["id"], t("common.name_unknown"))
        ttk.Label(p, text=t("class_tab.detail_header", id=cl["id"], name=name), font=("Segoe UI", 10, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 4))

        header_holder = ttk.Frame(p); header_holder.pack(fill="x", padx=8)
        render_group_header(header_holder, t("class_tab.group_level"))

        for fd in CLASS_FIELD_DEFS:
            row = ttk.Frame(p); row.pack(fill="x", padx=8)
            control, set_enabled = render_field_row(
                row, fd, fields.get(fd["name"], fd["default"]), self._make_on_change(fd["name"])
            )
            set_enabled(True)

    def _make_on_change(self, field_name):
        def _on_change(new_val):
            self._current_class["fields"][field_name] = new_val
            self.cfg.save_config()
            self.app.refresh_all_tabs()
            log.info(t("class_tab.log_field_changed", id=self._current_class["id"], field=field_name, value=new_val))
            self.class_detail_frame.after_idle(lambda: self.render_class_detail(self._current_class))
        return _on_change

    def open_stat_editor_popup(self, cl):
        # 클래스는 자체 레벨 상한이 없으므로, 팝업을 열 때마다 System 탭의 '최대 레벨'
        # 설정에 맞춰 배열 길이를 다시 맞춰줍니다.
        level = self._max_allowed_level()
        for key in STAT_ARRAY_KEYS:
            cl["parameters"][key] = resize_stat_array(cl["parameters"].get(key, []), level)
        self.cfg.save_config()
        name = self.app.edb_master_classes.get(cl["id"], t("common.name_unknown"))
        open_stat_editor_popup(self.app, self.cfg, cl, name, level, STAT_POPUP_KEYS, STAT_POPUP_LABEL_KEYS)

    # ------------------------------------------------------------------
    def on_class_search(self, event):
        query = self.class_search_entry.get().strip().lower()
        self.class_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(cid, name) for cid, name in sorted(self.app.edb_master_classes.items()) if query in name.lower()]
        for cid, name in matches[:20]:
            self.class_search_listbox.insert(tk.END, f"{cid} - {name}")

    def on_class_search_select(self, event):
        sel = self.class_search_listbox.curselection()
        if not sel: return
        text = self.class_search_listbox.get(sel[0])
        cid = int(text.split(" - ", 1)[0])
        self.class_id_entry.delete(0, tk.END); self.class_id_entry.insert(0, str(cid))
        self.class_search_entry.delete(0, tk.END)
        self.class_search_listbox.delete(0, tk.END)
        self.open_editor_for_id(cid)

    # ------------------------------------------------------------------
    def add_class_rule(self):
        try:
            cid = int(self.class_id_entry.get().strip())
        except ValueError:
            messagebox.showerror(t("common.title_error"), t("common.msg_id_must_be_number"))
            return
        self.open_editor_for_id(cid)

    def move_class(self, direction):
        sel = self.class_tree.selection()
        if not sel: return
        cid = int(sel[0])
        classes = self.cfg.current_config["classes"]
        idx = next((i for i, c in enumerate(classes) if c["id"] == cid), None)
        if idx is None: return
        new_idx = idx + direction
        if 0 <= new_idx < len(classes):
            classes[idx], classes[new_idx] = classes[new_idx], classes[idx]
            self.cfg.save_config()
            self.app.refresh_all_tabs()

    def delete_class_rule(self):
        sel = self.class_tree.selection()
        if not sel: return
        cid = int(sel[0])
        self.cfg.current_config["classes"] = [c for c in self.cfg.current_config["classes"] if c["id"] != cid]
        self.cfg.save_config()
        if self._current_class and self._current_class.get("id") == cid:
            self._current_class = None
            self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("class_tab.log_deleted", id=cid))

    def batch_clear_classes(self):
        if not self.cfg.current_config["classes"]:
            messagebox.showwarning(t("common.title_warning"), t("class_tab.msg_no_classes"))
            return
        if not messagebox.askyesno(t("class_tab.title_confirm_clear"), t("class_tab.msg_confirm_clear")): return
        self.cfg.current_config["classes"] = []
        self.cfg.save_config()
        self._current_class = None
        self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("class_tab.log_cleared"))
