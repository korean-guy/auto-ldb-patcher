"""
tabs/item_tab.py
"[개별] 아이템 최대 소지량 조절" 탭 - 아이템 목록/이름검색/추가삭제/일괄설정.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import attach_tree_scrollbar, make_listbox_with_scroll

ITEM_TYPE_NAMES = {
    0: "일반", 1: "무기", 2: "방패", 3: "갑옷", 4: "투구", 5: "악세사리",
    6: "회복약", 7: "스킬북", 8: "씨앗", 9: "특수", 10: "스위치",
}


class ItemTab:
    TITLE = "📦 [개별] 아이템 최대 소지량 조절"

    def __init__(self, app):
        self.app = app  # 메인 App 인스턴스 (cfg, edb_master_* 공유)

    @property
    def cfg(self):
        return self.app.cfg

    def build(self, notebook):
        item_frame = ttk.Frame(notebook, padding=10)
        notebook.add(item_frame, text=self.TITLE)

        self.item_tree = ttk.Treeview(item_frame, columns=("ID", "이름", "타입", "최대수량"), show="headings", height=18)
        for col, txt in [("ID", "ID"), ("이름", "아이템 이름"), ("타입", "타입"), ("최대수량", "최대 수량")]:
            self.item_tree.heading(col, text=txt)
        self.item_tree.pack(fill="both", expand=True, side="left")
        attach_tree_scrollbar(self.item_tree, item_frame)

        self.item_tree.column("ID", width=60, anchor="center")
        self.item_tree.column("이름", width=280, anchor="w")
        self.item_tree.column("타입", width=90, anchor="center")
        self.item_tree.column("최대수량", width=120, anchor="center")
        self.item_tree.bind("<<TreeviewSelect>>", self.on_item_select)

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
        self.item_id_entry = ttk.Entry(item_btn_frame, width=25); self.item_id_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(item_btn_frame, text="최대 수량:").pack(anchor="w", pady=(0, 2))
        self.item_val_entry = ttk.Entry(item_btn_frame, width=25); self.item_val_entry.pack(anchor="w", pady=(0, 15))
        ttk.Button(item_btn_frame, text="➕ 추가/수정", command=self.add_item_rule).pack(fill="x", pady=3)
        ttk.Button(item_btn_frame, text="❌ 규칙 삭제", command=self.delete_item_rule).pack(fill="x", pady=3)

        ttk.Label(item_btn_frame, text="일괄 설정 (등록된 항목만)").pack(anchor="w", pady=(20, 4))
        ttk.Button(item_btn_frame, text="🗑️ 전체삭제", command=self.batch_clear_items).pack(fill="x", pady=2)
        ttk.Button(item_btn_frame, text="↩️ 기본값 (99)", command=lambda: self.batch_set_items(99)).pack(fill="x", pady=2)
        ttk.Button(item_btn_frame, text="⬆️ 최대값 (255)", command=lambda: self.batch_set_items(255)).pack(fill="x", pady=2)

    # ------------------------------------------------------------------
    def refresh(self):
        for item in self.item_tree.get_children(): self.item_tree.delete(item)
        for it in self.cfg.current_config.get("items", []):
            iid = it["id"]
            name = self.app.edb_master_items.get(iid) or "⚠️ 알만툴 DB에 없음"
            type_code = self.app.edb_master_item_types.get(iid)
            type_name = ITEM_TYPE_NAMES.get(type_code, "-") if type_code is not None else "-"
            display_count = it["easyrpg_max_count"] if it["easyrpg_max_count"] != -1 else "순정 제한 유지"
            self.item_tree.insert("", "end", values=(iid, name, type_name, display_count))

    def on_item_select(self, event):
        selected = self.item_tree.selection()
        if not selected: return
        vals = self.item_tree.item(selected)['values']
        if not vals: return
        iid = int(vals[0])
        it = next((i for i in self.cfg.current_config["items"] if i["id"] == iid), None)
        if it:
            self.item_id_entry.delete(0, tk.END); self.item_id_entry.insert(0, str(it["id"]))
            self.item_val_entry.delete(0, tk.END)
            if it["easyrpg_max_count"] != -1:
                self.item_val_entry.insert(0, str(it["easyrpg_max_count"]))

    def on_item_search(self, event):
        query = self.item_search_entry.get().strip()
        self.item_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(iid, name) for iid, name in sorted(self.app.edb_master_items.items()) if query in name]
        for iid, name in matches[:20]:
            self.item_search_listbox.insert(tk.END, f"{iid} - {name}")

    def on_item_search_select(self, event):
        sel = self.item_search_listbox.curselection()
        if not sel: return
        text = self.item_search_listbox.get(sel[0])
        iid = text.split(" - ", 1)[0]
        self.item_id_entry.delete(0, tk.END); self.item_id_entry.insert(0, iid)
        self.item_search_entry.delete(0, tk.END)
        self.item_search_listbox.delete(0, tk.END)

    def add_item_rule(self):
        try:
            iid = int(self.item_id_entry.get().strip())
            val_input = self.item_val_entry.get().strip()
            val = int(val_input) if val_input else -1
            if val > 255:
                val = 255
                messagebox.showwarning("수량 제한", "엔진 세이브 오동작 방지를 위해 개별 아이템 한도는 255개로 자동 한정됩니다.")
            if iid not in self.app.edb_master_items:
                if not messagebox.askyesno("경고", "순정 아이템에 없습니다. 진행할까요?"): return
            self.cfg.current_config["items"] = [i for i in self.cfg.current_config["items"] if i["id"] != iid]
            self.cfg.current_config["items"].append({"id": iid, "easyrpg_max_count": val})
            self.cfg.save_config()
            self.app.refresh_all_tabs()
        except ValueError:
            messagebox.showerror("에러", "ID와 수치는 정수 숫자로 입력해 주세요.")

    def delete_item_rule(self):
        sel = self.item_tree.selection()
        if not sel: return
        item_vals = self.item_tree.item(sel)['values']
        iid = int(item_vals[0])
        self.cfg.current_config["items"] = [i for i in self.cfg.current_config["items"] if i["id"] != iid]
        self.cfg.save_config()
        self.app.refresh_all_tabs()

    def batch_clear_items(self):
        if not self.cfg.current_config["items"]:
            messagebox.showwarning("경고", "리스트에 등록된 아이템이 없습니다.")
            return
        if not messagebox.askyesno("일괄 삭제", "등록된 모든 아이템 규칙을 삭제하시겠습니까?"): return
        self.cfg.current_config["items"] = []
        self.cfg.save_config()
        self.app.refresh_all_tabs()

    def batch_set_items(self, value):
        if not self.cfg.current_config["items"]:
            messagebox.showwarning("경고", "리스트에 등록된 아이템이 없습니다.")
            return
        for it in self.cfg.current_config["items"]:
            it["easyrpg_max_count"] = value
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        messagebox.showinfo("완료", f"등록된 아이템 {len(self.cfg.current_config['items'])}개의 최대 수량을 {value}(으)로 일괄 설정했습니다.")
