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
from core.property_panel import (make_fixed_scroll_panel, render_field_row, render_group_header,
                                  scroll_panel_to_top, DETAIL_WIDTH, DETAIL_HEIGHT)
from core.item_schema import ITEM_FIELD_DEFS, default_item_fields, migrate_item_entry
from core.logger import log

ITEM_TYPE_NAMES = {
    0: "일반", 1: "무기", 2: "방패", 3: "갑옷", 4: "투구", 5: "악세사리",
    6: "회복약", 7: "스킬북", 8: "씨앗", 9: "특수", 10: "스위치",
}


class ItemTab:
    TITLE = "📦 [개별] 아이템 최대 소지량 조절"

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
        for col, txt in [("ID", "ID"), ("이름", "아이템 이름"), ("타입", "타입"), ("최대수량", "최대 수량")]:
            self.item_tree.heading(col, text=txt)
        self.item_tree.pack(fill="both", expand=True, side="left")
        attach_tree_scrollbar(self.item_tree, left_frame)

        self.item_tree.column("ID", width=60, anchor="center")
        self.item_tree.column("이름", width=280, anchor="w")
        self.item_tree.column("타입", width=90, anchor="center")
        self.item_tree.column("최대수량", width=120, anchor="center")
        self.item_tree.bind("<<TreeviewSelect>>", self.on_item_select)
        enable_column_sort(self.item_tree, ("ID", "이름", "타입", "최대수량"), numeric_columns=("ID", "최대수량"))
        enable_column_width_persistence(self.item_tree, self.cfg, "item_tree")

        item_btn_frame = ttk.Frame(item_frame, padding=10)
        item_btn_frame.pack(fill="y", side="right")

        ttk.Label(item_btn_frame, text="이름 검색:").pack(anchor="w", pady=(0, 2))
        self.item_search_entry = ttk.Entry(item_btn_frame, width=25)
        self.item_search_entry.pack(anchor="w", pady=(0, 2))
        self.item_search_entry.bind("<KeyRelease>", self.on_item_search)
        item_search_frame, self.item_search_listbox = make_listbox_with_scroll(item_btn_frame, height=6)
        item_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.item_search_listbox.bind("<<ListboxSelect>>", self.on_item_search_select)

        ttk.Label(item_btn_frame, text="아이템 ID:").pack(anchor="w", pady=(0, 2))
        self.item_id_entry = ttk.Entry(item_btn_frame, width=25); self.item_id_entry.pack(anchor="w", pady=(0, 2))
        self.item_id_entry.bind("<KeyRelease>", self.on_id_entry_typed)
        self.item_id_entry.bind("<Return>", self.on_id_entry_committed)
        self.item_id_entry.bind("<FocusOut>", self.on_id_entry_committed)
        self.selected_name_var = tk.StringVar(value="선택된 이름: -")
        ttk.Label(item_btn_frame, textvariable=self.selected_name_var).pack(anchor="w", pady=(0, 10))

        add_del_row = ttk.Frame(item_btn_frame)
        add_del_row.pack(fill="x", pady=3)
        ttk.Button(add_del_row, text="➕ 목록에 추가", command=self.add_item_rule).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(add_del_row, text="❌ 목록에서 삭제", command=self.delete_item_rule).pack(side="left", expand=True, fill="x", padx=(2, 0))

        ttk.Label(item_btn_frame, text="일괄 설정 (등록된 항목만)").pack(anchor="w", pady=(20, 4))
        batch_row1 = ttk.Frame(item_btn_frame); batch_row1.pack(fill="x", pady=2)
        ttk.Button(batch_row1, text="↩️ 기본값 (-1)", command=lambda: self.batch_set_items(-1)).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(batch_row1, text="⬆️ 최대값 (255)", command=lambda: self.batch_set_items(255)).pack(side="left", expand=True, fill="x", padx=(2, 0))
        ttk.Button(item_btn_frame, text="🗑️ 전체삭제", command=self.batch_clear_items).pack(fill="x", pady=2)

        ttk.Label(item_btn_frame, text="세부 옵션 편집").pack(anchor="w", pady=(20, 4))
        self.detail_outer, self.item_detail_frame = make_fixed_scroll_panel(
            item_btn_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

    def _show_placeholder(self):
        for w in self.item_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.item_detail_frame, text="왼쪽 목록에서 아이템을 선택하거나, ID/이름 검색으로\n아이템을 지정하면 편집 패널이 바로 열립니다.",
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    # ------------------------------------------------------------------
    def refresh(self):
        selected = self.item_tree.selection()
        prev_iid = selected[0] if selected else None

        for item in self.item_tree.get_children(): self.item_tree.delete(item)
        for it in self.cfg.current_config.get("items", []):
            iid = it["id"]
            name = self.app.edb_master_items.get(iid) or "⚠️ 알만툴 DB에 없음"
            type_code = self.app.edb_master_item_types.get(iid)
            type_name = ITEM_TYPE_NAMES.get(type_code, "-") if type_code is not None else "-"
            max_count = it.get("fields", {}).get("easyrpg_max_count", -1)
            display_count = max_count if max_count != -1 else "순정 제한 유지"
            self.item_tree.insert("", "end", iid=str(iid), values=(iid, name, type_name, display_count))

        if prev_iid and self.item_tree.exists(prev_iid):
            self.item_tree.selection_set(prev_iid)
            self.item_tree.see(prev_iid)

    # ------------------------------------------------------------------
    def _update_selected_name_label(self, iid_text):
        try:
            iid = int(iid_text.strip())
        except ValueError:
            self.selected_name_var.set("선택된 이름: -")
            return
        name = self.app.edb_master_items.get(iid)
        self.selected_name_var.set(f"선택된 이름: {name}" if name else "선택된 이름: (알 수 없음)")

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
                if not messagebox.askyesno("경고", "순정 아이템에 없습니다. 목록에 추가하고 편집할까요?"):
                    return
            existing = {"id": iid, "fields": default_item_fields()}
            self.cfg.current_config["items"].append(existing)
            self.cfg.save_config()
            log.info(f"아이템 목록에 추가 (ID {iid})")
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

        name = self.app.edb_master_items.get(it["id"], "이름 없음")
        ttk.Label(p, text=f"아이템 ID {it['id']} - {name}", font=("Segoe UI", 10, "bold"),
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
            log.info(f"아이템 {self._current_item['id']} - {field_name} = {new_val}")
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
    def add_item_rule(self):
        try:
            iid = int(self.item_id_entry.get().strip())
        except ValueError:
            messagebox.showerror("에러", "ID는 숫자로 입력해 주세요.")
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
        log.info(f"아이템 목록에서 삭제 (ID {iid})")

    def batch_clear_items(self):
        if not self.cfg.current_config["items"]:
            messagebox.showwarning("경고", "리스트에 등록된 아이템이 없습니다.")
            return
        if not messagebox.askyesno("일괄 삭제", "등록된 모든 아이템 규칙을 삭제하시겠습니까?"): return
        self.cfg.current_config["items"] = []
        self.cfg.save_config()
        self._current_item = None
        self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info("아이템 목록 전체 삭제")

    def batch_set_items(self, value):
        if not self.cfg.current_config["items"]:
            messagebox.showwarning("경고", "리스트에 등록된 아이템이 없습니다.")
            return
        for it in self.cfg.current_config["items"]:
            it["fields"]["easyrpg_max_count"] = value
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        if self._current_item:
            self.render_item_detail(self._current_item)
        log.info(f"아이템 일괄 설정 완료: 최대 수량 = {value}")
        messagebox.showinfo("완료", f"등록된 아이템 {len(self.cfg.current_config['items'])}개의 최대 수량을 {value}(으)로 일괄 설정했습니다.")
