"""
tabs/item_tab.py
"[개별] 아이템 최대 소지량 조절" 탭 - 속성 편집기(Property Editor) 스타일.
core/skill_schema.py 대신 core/item_schema.py의 ITEM_FIELD_DEFS를 사용한다는 점만 다르고
구조는 tabs/skill_tab.py와 동일합니다 (검색/ID 입력만으로 즉시 편집 패널이 열립니다).
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import (attach_tree_scrollbar, make_listbox_with_scroll,
                         enable_column_sort, enable_column_width_persistence)
from core.context_menu import attach_row_context_menu
from core.property_panel import (make_fixed_scroll_panel, render_field_row, render_group_header,
                                  scroll_panel_to_top, DETAIL_WIDTH, DETAIL_HEIGHT)
from core.item_schema import ITEM_FIELD_DEFS, default_item_fields, migrate_item_entry
from core.logger import log
from core.i18n import t

# 아이템 타입(일반/무기/방패/...) 표시 문자열은 core/locales/ko.json의 item_type.* 키를 사용합니다.


class ItemTab:
    TITLE = t("item_tab.title")

    def __init__(self, app):
        self.app = app
        self._current_item = None

    @property
    def cfg(self):
        return self.app.cfg

    # ------------------------------------------------------------------
    def on_project_loaded(self):
        """예전 버전 아이템 항목({"id":.., "easyrpg_max_count":..})을 새 스키마로 변환합니다."""
        items = self.cfg.current_config.get("items", [])
        migrated = [migrate_item_entry(it) for it in items]
        if migrated != items:
            self.cfg.current_config["items"] = migrated
            self.cfg.save_config()

    # ------------------------------------------------------------------
    def build(self, notebook):
        item_frame = ttk.Frame(notebook, padding=10)
        notebook.add(item_frame, text=self.TITLE)

        left_frame = ttk.Frame(item_frame)
        left_frame.pack(fill="both", expand=True, side="left")

        self.item_tree = ttk.Treeview(left_frame, columns=("ID", "이름", "타입", "최대수량"),
                                       show="headings", height=18)
        for col, txt in [("ID", t("item_tab.col_id")), ("이름", t("item_tab.col_name")),
                          ("타입", t("item_tab.col_type")), ("최대수량", t("item_tab.col_max_count"))]:
            self.item_tree.heading(col, text=txt)
        attach_tree_scrollbar(self.item_tree, left_frame)
        self.item_tree.pack(fill="both", expand=True, side="left")

        self.item_tree.column("ID", width=60, anchor="center")
        self.item_tree.column("이름", width=280, anchor="w")
        self.item_tree.column("타입", width=90, anchor="center")
        self.item_tree.column("최대수량", width=120, anchor="center")
        self.item_tree.bind("<<TreeviewSelect>>", self.on_item_select)
        enable_column_sort(self.item_tree, ("ID", "이름", "타입", "최대수량"), numeric_columns=("ID", "최대수량"))
        enable_column_width_persistence(self.item_tree, self.cfg, "item_tree")
        attach_row_context_menu(self.item_tree, lambda: self.move_item(-1), lambda: self.move_item(1), self.delete_item_rule)

        item_btn_frame = ttk.Frame(item_frame, padding=10)
        item_btn_frame.pack(fill="y", side="right")

        ttk.Label(item_btn_frame, text=t("common.label_search_name")).pack(anchor="w", pady=(0, 2))
        self.item_search_entry = ttk.Entry(item_btn_frame, width=25)
        self.item_search_entry.pack(anchor="w", pady=(0, 2))
        self.item_search_entry.bind("<KeyRelease>", self.on_item_search)
        item_search_frame, self.item_search_listbox = make_listbox_with_scroll(item_btn_frame, height=6)
        item_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.item_search_listbox.bind("<<ListboxSelect>>", self.on_item_search_select)

        ttk.Label(item_btn_frame, text=t("item_tab.label_id")).pack(anchor="w", pady=(0, 2))
        self.item_id_entry = ttk.Entry(item_btn_frame, width=25); self.item_id_entry.pack(anchor="w", pady=(0, 2))
        self.item_id_entry.bind("<KeyRelease>", self.on_id_entry_typed)
        self.item_id_entry.bind("<Return>", self.on_id_entry_committed)
        self.item_id_entry.bind("<FocusOut>", self.on_id_entry_committed)
        self.selected_name_var = tk.StringVar(value=t("common.label_selected_name_empty"))
        ttk.Label(item_btn_frame, textvariable=self.selected_name_var).pack(anchor="w", pady=(0, 10))

        add_del_row = ttk.Frame(item_btn_frame)
        add_del_row.pack(fill="x", pady=3)
        ttk.Button(add_del_row, text=t("common.btn_add_to_list"), command=self.add_item_rule).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(add_del_row, text=t("common.btn_remove_from_list"), command=self.delete_item_rule).pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Label(item_btn_frame, text=t("common.label_batch_settings")).pack(anchor="w", pady=(20, 4))
        batch_row1 = ttk.Frame(item_btn_frame); batch_row1.pack(fill="x", pady=2)
        ttk.Button(batch_row1, text=t("item_tab.btn_default"), command=lambda: self.batch_set_items(-1)).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(batch_row1, text=t("item_tab.btn_max"), command=lambda: self.batch_set_items(255)).pack(side="left", expand=True, fill="x", padx=(2, 0))
        ttk.Button(item_btn_frame, text=t("common.btn_clear_all"), command=self.batch_clear_items).pack(fill="x", pady=2)

        ttk.Label(item_btn_frame, text=t("common.label_detail_editor")).pack(anchor="w", pady=(20, 4))
        self.detail_outer, self.item_detail_frame = make_fixed_scroll_panel(
            item_btn_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

    def _show_placeholder(self):
        for w in self.item_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.item_detail_frame, text=t("item_tab.placeholder"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    # ------------------------------------------------------------------
    def refresh(self):
        selected = self.item_tree.selection()
        prev_iid = selected[0] if selected else None

        for item in self.item_tree.get_children(): self.item_tree.delete(item)
        for it in self.cfg.current_config.get("items", []):
            iid = it["id"]
            name = it.get("fields", {}).get("name") or self.app.edb_master_items.get(iid) or t("common.msg_not_in_master_db")
            type_code = self.app.edb_master_item_types.get(iid)
            type_name = t(f"item_type.{type_code}") if type_code is not None else "-"
            max_count = it.get("fields", {}).get("easyrpg_max_count", -1)
            display_count = max_count if max_count != -1 else t("item_tab.max_count_default_display")
            self.item_tree.insert("", "end", iid=str(iid), values=(iid, name, type_name, display_count))

        if prev_iid and self.item_tree.exists(prev_iid):
            self.item_tree.selection_set(prev_iid)
            self.item_tree.see(prev_iid)

    # ------------------------------------------------------------------
    def _update_selected_name_label(self, iid_text):
        try:
            iid = int(iid_text.strip())
        except ValueError:
            self.selected_name_var.set(t("common.label_selected_name_empty"))
            return
        name = self.app.edb_master_items.get(iid)
        self.selected_name_var.set(t("common.label_selected_name", name=name) if name else t("common.label_selected_name_unknown"))

    def on_id_entry_typed(self, event):
        self._update_selected_name_label(self.item_id_entry.get())

    def on_id_entry_committed(self, event):
        raw = self.item_id_entry.get().strip()
        if not raw:
            return
        try:
            iid = int(raw)
        except ValueError:
            return
        self.open_editor_for_id(iid)

    def on_item_select(self, event):
        selected = self.item_tree.selection()
        if not selected: return
        iid = int(selected[0])
        it = next((i for i in self.cfg.current_config["items"] if i["id"] == iid), None)
        if it:
            self.item_id_entry.delete(0, tk.END); self.item_id_entry.insert(0, str(it["id"]))
            self._update_selected_name_label(str(it["id"]))
            self.render_item_detail(it)

    def open_editor_for_id(self, iid):
        """ID(검색 선택 또는 직접 입력)만으로 즉시 편집 패널을 엽니다.
        아직 목록에 없는 아이템이면 기본값으로 자동 추가합니다."""
        self._update_selected_name_label(str(iid))
        existing = next((i for i in self.cfg.current_config["items"] if i["id"] == iid), None)
        if existing is None:
            if iid not in self.app.edb_master_items:
                if not messagebox.askyesno(t("common.title_warning"), t("item_tab.msg_confirm_add_unknown")):
                    return
            fields = default_item_fields()
            fields["name"] = self.app.edb_master_items.get(iid, "")
            existing = {"id": iid, "fields": fields}
            self.cfg.current_config["items"].append(existing)
            self.cfg.save_config()
            log.info(t("item_tab.log_added", id=iid))
            self.app.refresh_all_tabs()

        if self.item_tree.exists(str(iid)):
            self.item_tree.selection_set(str(iid))
            self.item_tree.see(str(iid))
        self.render_item_detail(existing)

    def render_item_detail(self, it):
        for w in self.item_detail_frame.winfo_children():
            w.destroy()
        self._current_item = it
        fields = it["fields"]
        p = self.item_detail_frame

        name = it["fields"].get("name") or self.app.edb_master_items.get(it["id"], t("common.name_unknown"))
        ttk.Label(p, text=t("item_tab.detail_header", id=it['id'], name=name), font=("Segoe UI", 10, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 4))

        last_group = None
        for fd in ITEM_FIELD_DEFS:
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
            self._current_item["fields"][field_name] = new_val
            self.cfg.save_config()
            self.app.refresh_all_tabs()
            log.info(t("item_tab.log_field_changed", id=self._current_item["id"], field=field_name, value=new_val))
            self.item_detail_frame.after_idle(lambda: self.render_item_detail(self._current_item))
        return _on_change

    # ------------------------------------------------------------------
    # 이름 검색 (드롭다운) - 선택하면 즉시 편집 패널이 열림
    # ------------------------------------------------------------------
    def on_item_search(self, event):
        query = self.item_search_entry.get().strip().lower()
        self.item_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(iid, name) for iid, name in sorted(self.app.edb_master_items.items()) if query in name.lower()]
        for iid, name in matches[:20]:
            self.item_search_listbox.insert(tk.END, f"{iid} - {name}")

    def on_item_search_select(self, event):
        sel = self.item_search_listbox.curselection()
        if not sel: return
        text = self.item_search_listbox.get(sel[0])
        iid = int(text.split(" - ", 1)[0])
        self.item_id_entry.delete(0, tk.END); self.item_id_entry.insert(0, str(iid))
        self.item_search_entry.delete(0, tk.END)
        self.item_search_listbox.delete(0, tk.END)
        self.open_editor_for_id(iid)

    # ------------------------------------------------------------------
    # 목록 추가/삭제/일괄 설정
    # ------------------------------------------------------------------
    def move_item(self, direction):
        sel = self.item_tree.selection()
        if not sel: return
        iid = int(sel[0])
        items = self.cfg.current_config["items"]
        idx = next((i for i, it in enumerate(items) if it["id"] == iid), None)
        if idx is None: return
        new_idx = idx + direction
        if 0 <= new_idx < len(items):
            items[idx], items[new_idx] = items[new_idx], items[idx]
            self.cfg.save_config()
            self.app.refresh_all_tabs()

    def add_item_rule(self):
        try:
            iid = int(self.item_id_entry.get().strip())
        except ValueError:
            messagebox.showerror(t("common.title_error"), t("common.msg_id_must_be_number"))
            return
        self.open_editor_for_id(iid)

    def delete_item_rule(self):
        sel = self.item_tree.selection()
        if not sel: return
        iid = int(sel[0])
        self.cfg.current_config["items"] = [i for i in self.cfg.current_config["items"] if i["id"] != iid]
        self.cfg.save_config()
        if self._current_item and self._current_item.get("id") == iid:
            self._current_item = None
            self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("item_tab.log_deleted", id=iid))

    def batch_clear_items(self):
        if not self.cfg.current_config["items"]:
            messagebox.showwarning(t("common.title_warning"), t("item_tab.msg_no_items"))
            return
        if not messagebox.askyesno(t("item_tab.title_confirm_clear"), t("item_tab.msg_confirm_clear")): return
        self.cfg.current_config["items"] = []
        self.cfg.save_config()
        self._current_item = None
        self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(t("item_tab.log_cleared"))

    def batch_set_items(self, value):
        if not self.cfg.current_config["items"]:
            messagebox.showwarning(t("common.title_warning"), t("item_tab.msg_no_items"))
            return
        for it in self.cfg.current_config["items"]:
            it["fields"]["easyrpg_max_count"] = value
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        if self._current_item:
            self.render_item_detail(self._current_item)
        log.info(t("item_tab.log_batch_done", value=value))
        messagebox.showinfo(t("common.title_done"), t("item_tab.msg_batch_done", count=len(self.cfg.current_config['items']), value=value))
