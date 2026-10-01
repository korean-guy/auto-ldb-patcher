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
from core.item_schema import EQUIPMENT_ITEM_TYPES, ITEM_FIELD_DEFS, default_item_fields, migrate_item_entry
from core.logger import log
from core.i18n import t

# 아이템 타입(일반/무기/방패/...) 표시 문자열은 core/locales/ko.json의 item_type.* 키를 사용합니다.


class ItemTab:
    @property
    def TITLE(self):
        # 클래스 속성으로 두면 이 모듈이 처음 임포트될 때(항상 set_language()보다
        # 먼저 일어남 - 그래서 항상 기본 언어) 딱 한 번만 계산되어 고정돼버리므로,
        # self.TITLE로 매번 조회될 때 새로 번역하도록 property로 만들었습니다.
        return t("item_tab.title")

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

        find_frame = ttk.Frame(left_frame)
        find_frame.pack(fill="x", pady=(0, 4))
        ttk.Label(find_frame, text=t("common.label_find_in_list")).pack(side="left", padx=(0, 4))
        self.item_find_entry = ttk.Entry(find_frame)
        self.item_find_entry.pack(side="left", fill="x", expand=True)
        self.item_find_entry.bind("<KeyRelease>", self.on_find_in_list)

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
        ttk.Button(item_btn_frame, text=t("common.btn_add_all"), command=self.add_all_items).pack(fill="x", pady=(2, 0))

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

    def reset_detail_panel(self):
        """외부(설정 불러오기 등)에서 데이터 전체가 교체됐을 때, 화면에 예전 값이
        남아있지 않도록 편집 패널을 비웁니다."""
        self._current_item = None
        self._show_placeholder()

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
        # 이미 이 항목이 상세 패널에 표시되어 있으면 다시 그리지 않습니다 - refresh()가
        # 값 저장 뒤 같은 항목을 재선택할 때 불필요하게 다시 그려지는 것을 막아줍니다.
        # (타이밍 기반 억제 플래그 대신 "실제로 대상이 바뀌었는가"로 판단하므로, 다른
        # 항목을 클릭한 진짜 선택 이벤트가 무시되는 일이 없습니다.)
        if self._current_item is not None and self._current_item.get("id") == iid:
            return
        it = next((i for i in self.cfg.current_config["items"] if i["id"] == iid), None)
        if it:
            self.item_id_entry.delete(0, tk.END); self.item_id_entry.insert(0, str(it["id"]))
            self._update_selected_name_label(str(it["id"]))
            self.render_item_detail(it)

    def _build_new_entry(self, iid):
        """새로 등록할 아이템의 기본 항목을 만듭니다 (edb에 있는 실제 이름/설명/장비
        능력치로 미리 채움 - 장비 능력치는 장비류 타입일 때만). ID 직접 입력으로
        하나씩 추가할 때(open_editor_for_id)와 전체 추가(add_all_items)에서 공용으로 씁니다."""
        fields = default_item_fields()
        fields["name"] = self.app.edb_master_items.get(iid, "")
        edb_data = self.app.edb_master_item_data.get(iid, {})
        is_equipment = self.app.edb_master_item_types.get(iid) in EQUIPMENT_ITEM_TYPES
        for fd in ITEM_FIELD_DEFS:
            if fd.get("from_edb") and fd["name"] in edb_data:
                if fd.get("equipment_only") and not is_equipment:
                    continue
                fields[fd["name"]] = edb_data[fd["name"]]
        return {"id": iid, "fields": fields}

    def open_editor_for_id(self, iid):
        """ID(검색 선택 또는 직접 입력)만으로 즉시 편집 패널을 엽니다.
        아직 목록에 없는 아이템이면 기본값으로 자동 추가합니다."""
        self._update_selected_name_label(str(iid))
        existing = next((i for i in self.cfg.current_config["items"] if i["id"] == iid), None)
        if existing is None:
            if iid not in self.app.edb_master_items:
                if not messagebox.askyesno(t("common.title_warning"), t("item_tab.msg_confirm_add_unknown")):
                    return
            existing = self._build_new_entry(iid)
            self.cfg.current_config["items"].append(existing)
            self.cfg.save_config()
            log.info(t("item_tab.log_added", id=iid))
            self.app.refresh_all_tabs()

        if self.item_tree.exists(str(iid)):
            self.item_tree.selection_set(str(iid))
            self.item_tree.see(str(iid))
        self.render_item_detail(existing)

    def add_all_items(self):
        """순정 DB(edb)에 있는 아이템 중 아직 목록에 등록되지 않은 것을 전부 추가합니다."""
        existing_ids = {it["id"] for it in self.cfg.current_config["items"]}
        to_add = sorted(iid for iid in self.app.edb_master_items if iid not in existing_ids)
        if not to_add:
            messagebox.showinfo(t("common.title_notice"), t("item_tab.msg_add_all_none"))
            return
        if not messagebox.askyesno(t("item_tab.title_confirm_add_all"), t("item_tab.msg_confirm_add_all", count=len(to_add))):
            return
        for iid in to_add:
            self.cfg.current_config["items"].append(self._build_new_entry(iid))
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        log.info(t("item_tab.log_add_all_done", count=len(to_add)))
        messagebox.showinfo(t("common.title_done"), t("item_tab.msg_add_all_done", count=len(to_add)))

    def on_find_in_list(self, event):
        """좌측에 이미 등록된 목록에서 ID 또는 이름으로 검색해 해당 위치로 바로
        이동하고 선택(커서 이동)합니다 - edb 전체를 뒤지는 검색(위의 이름 검색)과 달리,
        지금 목록에 있는 항목들 사이에서만 찾습니다."""
        query = self.item_find_entry.get().strip().lower()
        if not query:
            return
        for row_iid in self.item_tree.get_children():
            values = self.item_tree.item(row_iid)["values"]
            if query in str(values[0]).lower() or query in str(values[1]).lower():
                self.item_tree.selection_set(row_iid)
                self.item_tree.see(row_iid)
                self.item_tree.focus(row_iid)
                break

    def render_item_detail(self, it):
        for w in self.item_detail_frame.winfo_children():
            w.destroy()
        self._current_item = it
        fields = it["fields"]
        p = self.item_detail_frame

        name = it["fields"].get("name") or self.app.edb_master_items.get(it["id"], t("common.name_unknown"))
        ttk.Label(p, text=t("item_tab.detail_header", id=it['id'], name=name), font=("Segoe UI", 10, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 4))

        is_equipment = self.app.edb_master_item_types.get(it["id"]) in EQUIPMENT_ITEM_TYPES

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
                row, fd, self._display_value(fd, fields, it["id"]), self._make_on_change(fd["name"]),
                namespace="item",
            )
            # 장비 능력치는 장비류 아이템일 때만 수정할 수 있습니다.
            set_enabled(not fd.get("equipment_only") or is_equipment)

        scroll_panel_to_top(self.detail_outer)

    def _display_value(self, fd, fields, iid):
        """입력칸에 보여줄 값. from_edb 필드는 저장된 값이 비어있으면(None/빈 문자열) edb의
        원래 값을 대신 보여줍니다 - 예전에 등록해둔 아이템이라 저장된 값이 없어도 현재
        내용을 알 수 있고, 손대지 않으면 저장되지 않아 원래 값이 그대로 유지됩니다."""
        val = fields.get(fd["name"], fd["default"])
        empty = val is None or (fd.get("type") == "string" and val == "")
        if empty and fd.get("from_edb"):
            edb_val = self.app.edb_master_item_data.get(iid, {}).get(fd["name"])
            if edb_val is not None:
                return edb_val
        if val is None:
            return 0 if fd.get("type") == "int" else ""
        return val

    def _make_on_change(self, field_name):
        def _on_change(new_val):
            self._current_item["fields"][field_name] = new_val
            self.cfg.save_config()
            self.app.refresh_all_tabs()
            log.info(t("item_tab.log_field_changed", id=self._current_item["id"], field=field_name, value=new_val))
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
