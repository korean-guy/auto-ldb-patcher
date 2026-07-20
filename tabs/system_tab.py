"""
tabs/system_tab.py
"시스템 상한 제한 조절" 탭 - config.json의 system_limits를 type(int/bool/enum/list)에
따라 자동으로 알맞은 편집 UI를 생성합니다. 새 EasyRPG 옵션은 core/config.py의
DEFAULT_SYSTEM_DEFS(또는 프로그램 config.json)에 항목만 추가하면 이 탭에 자동 반영됩니다.
"""
import copy
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import FG_DIM, attach_tree_scrollbar, make_listbox_with_scroll, make_checkbutton

TYPE_LABEL_MAP = {"int": "정수", "bool": "체크박스", "enum": "콤보박스", "list": "체크+순서"}


class SystemTab:
    TITLE = "⚙️ 시스템 상한 제한 조절"

    def __init__(self, app):
        self.app = app
        self._current_sys_key = None
        self._current_sys_def = None

    @property
    def cfg(self):
        return self.app.cfg

    def build(self, notebook):
        sys_frame = ttk.Frame(notebook, padding=10)
        notebook.add(sys_frame, text=self.TITLE)

        self.sys_tree = ttk.Treeview(sys_frame, columns=("필드명", "이름", "타입", "현재값"), show="headings", height=18)
        for col, txt in [("필드명", "필드명"), ("이름", "옵션명"), ("타입", "타입"), ("현재값", "현재값")]:
            self.sys_tree.heading(col, text=txt)
        self.sys_tree.pack(fill="both", expand=True, side="left")
        attach_tree_scrollbar(self.sys_tree, sys_frame)

        self.sys_tree.column("필드명", width=220, anchor="w")
        self.sys_tree.column("이름", width=170, anchor="w")
        self.sys_tree.column("타입", width=90, anchor="center")
        self.sys_tree.column("현재값", width=160, anchor="w")
        self.sys_tree.bind("<<TreeviewSelect>>", self.on_sys_select)

        sys_side_frame = ttk.Frame(sys_frame, padding=10)
        sys_side_frame.pack(fill="y", side="right")
        self.sys_detail_frame = ttk.Frame(sys_side_frame, width=260)
        self.sys_detail_frame.pack(fill="x", anchor="n")
        self._show_placeholder()
        ttk.Button(sys_side_frame, text="🔄 모든 항목 기본값으로 초기화", command=self.reset_sys_limits).pack(fill="x", pady=(30, 3))

    def _show_placeholder(self):
        for w in self.sys_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.sys_detail_frame, text="왼쪽 목록에서 항목을 선택하세요.", foreground=FG_DIM,
                  wraplength=240).pack(anchor="w")

    # ------------------------------------------------------------------
    def refresh(self):
        for sys_item in self.sys_tree.get_children(): self.sys_tree.delete(sys_item)
        for key, defn in self.cfg.current_config.get("system_limits", {}).items():
            if key == "easyrpg_max_item_count":
                continue
            self.sys_tree.insert("", "end", values=(
                key, defn.get("name", key),
                TYPE_LABEL_MAP.get(defn.get("type", "int"), defn.get("type")),
                self.format_sys_value(defn),
            ))

    def format_sys_value(self, defn):
        t = defn.get("type", "int")
        val = defn.get("value")
        if t == "bool":
            return "사용" if val else "미사용"
        if t == "enum":
            label = defn.get("options", {}).get(str(val))
            return f'{val} ({label})' if label else str(val)
        if t == "list":
            options = defn.get("options", {})
            return " → ".join(options.get(str(v), str(v)) for v in (val or [])) or "(없음)"
        return "순정 한계 (-1)" if val == -1 else f"{val:,}"

    def find_sys_def(self, name):
        return self.cfg.find_sys_def(name)

    # ------------------------------------------------------------------
    # 타입별 동적 편집 패널
    # ------------------------------------------------------------------
    def on_sys_select(self, event):
        selected = self.sys_tree.selection()
        if not selected: return
        vals = self.sys_tree.item(selected)['values']
        if not vals: return
        key = str(vals[0])
        defn = self.find_sys_def(key)
        if defn:
            self.render_sys_detail(key, defn)

    def render_sys_detail(self, key, defn):
        for w in self.sys_detail_frame.winfo_children():
            w.destroy()
        self._current_sys_key = key
        self._current_sys_def = defn
        t = defn.get("type", "int")

        ttk.Label(self.sys_detail_frame, text=defn.get("name", key),
                  font=("Segoe UI", 11, "bold"), wraplength=240).pack(anchor="w", pady=(0, 2))
        ttk.Label(self.sys_detail_frame, text=key, foreground=FG_DIM).pack(anchor="w", pady=(0, 6))
        if defn.get("description"):
            ttk.Label(self.sys_detail_frame, text=defn["description"], foreground=FG_DIM,
                      wraplength=240).pack(anchor="w", pady=(0, 8))

        if t == "int":
            ttk.Label(self.sys_detail_frame, text="값 (-1 = 순정 기본):").pack(anchor="w")
            self.sys_int_entry = ttk.Entry(self.sys_detail_frame, width=22)
            self.sys_int_entry.pack(anchor="w", pady=(0, 10))
            self.sys_int_entry.insert(0, str(defn.get("value", -1)))
            ttk.Button(self.sys_detail_frame, text="✏️ 적용", command=self.apply_sys_int).pack(fill="x")

        elif t == "bool":
            self.sys_bool_var = tk.BooleanVar(value=bool(defn.get("value", False)))
            make_checkbutton(self.sys_detail_frame, "사용함", self.sys_bool_var,
                              command=self.apply_sys_bool).pack(anchor="w")

        elif t == "enum":
            options = defn.get("options", {})
            items = sorted(options.items(), key=lambda kv: int(kv[0]))
            labels = [f"{k} : {v}" for k, v in items]
            self.sys_enum_var = tk.StringVar()
            current_val = defn.get("value", -1)
            cur_label = next((f"{k} : {v}" for k, v in items if int(k) == current_val),
                              labels[0] if labels else "")
            self.sys_enum_var.set(cur_label)
            combo = ttk.Combobox(self.sys_detail_frame, textvariable=self.sys_enum_var,
                                  values=labels, state="readonly", width=32)
            combo.pack(anchor="w", pady=(0, 10))
            ttk.Button(self.sys_detail_frame, text="✏️ 적용", command=self.apply_sys_enum).pack(fill="x")

        elif t == "list":
            options = defn.get("options", {})
            options_sorted = sorted(options.items(), key=lambda kv: int(kv[0]))
            current_vals = defn.get("value", []) or []
            self.sys_list_vars = {}
            self.sys_list_order = [v for v in current_vals]

            for k_str, label in options_sorted:
                v = int(k_str)
                var = tk.BooleanVar(value=v in current_vals)
                self.sys_list_vars[v] = var
                make_checkbutton(self.sys_detail_frame, label, var,
                                  command=self.refresh_sys_list_order).pack(anchor="w")

            ttk.Label(self.sys_detail_frame, text="적용 순서:").pack(anchor="w", pady=(10, 2))
            list_frame, self.sys_list_order_box = make_listbox_with_scroll(self.sys_detail_frame, height=5)
            list_frame.pack(anchor="w", fill="x", pady=(0, 6))

            btn_row = ttk.Frame(self.sys_detail_frame); btn_row.pack(fill="x")
            ttk.Button(btn_row, text="▲ 위로", command=lambda: self.move_sys_list_item(-1)).pack(side="left", expand=True, fill="x")
            ttk.Button(btn_row, text="▼ 아래로", command=lambda: self.move_sys_list_item(1)).pack(side="left", expand=True, fill="x")
            ttk.Button(self.sys_detail_frame, text="✏️ 적용", command=self.apply_sys_list).pack(fill="x", pady=(8, 0))

            self.refresh_sys_list_order()

    def apply_sys_int(self):
        try:
            val = int(self.sys_int_entry.get().strip())
        except ValueError:
            messagebox.showerror("에러", "정수만 입력해 주세요.")
            return
        max_limit = self._current_sys_def.get("max")
        if max_limit is not None and val > max_limit:
            val = max_limit
            messagebox.showwarning("상한 제한", f"오버플로우 방지를 위해 최대값 {max_limit:,}으로 자동 제한됩니다.")
        if val < -1: val = -1
        self._current_sys_def["value"] = val
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        messagebox.showinfo("적용됨", f"[{self._current_sys_def.get('name')}] 값이 저장되었습니다.")

    def apply_sys_bool(self):
        self._current_sys_def["value"] = bool(self.sys_bool_var.get())
        self.cfg.save_config()
        self.app.refresh_all_tabs()

    def apply_sys_enum(self):
        sel = self.sys_enum_var.get()
        try:
            val = int(sel.split(":")[0].strip())
        except Exception:
            messagebox.showerror("에러", "값을 선택해 주세요.")
            return
        self._current_sys_def["value"] = val
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        messagebox.showinfo("적용됨", f"[{self._current_sys_def.get('name')}] 값이 저장되었습니다.")

    def refresh_sys_list_order(self):
        checked = [v for v, var in self.sys_list_vars.items() if var.get()]
        new_order = [v for v in self.sys_list_order if v in checked]
        for v in checked:
            if v not in new_order:
                new_order.append(v)
        self.sys_list_order = new_order
        self.redraw_sys_list_order_box()

    def redraw_sys_list_order_box(self):
        self.sys_list_order_box.delete(0, tk.END)
        options = self._current_sys_def.get("options", {})
        for v in self.sys_list_order:
            self.sys_list_order_box.insert(tk.END, options.get(str(v), str(v)))

    def move_sys_list_item(self, direction):
        sel = self.sys_list_order_box.curselection()
        if not sel: return
        idx = sel[0]
        new_idx = idx + direction
        if 0 <= new_idx < len(self.sys_list_order):
            self.sys_list_order[idx], self.sys_list_order[new_idx] = self.sys_list_order[new_idx], self.sys_list_order[idx]
            self.redraw_sys_list_order_box()
            self.sys_list_order_box.selection_set(new_idx)

    def apply_sys_list(self):
        self._current_sys_def["value"] = list(self.sys_list_order)
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        messagebox.showinfo("적용됨", f"[{self._current_sys_def.get('name')}] 값이 저장되었습니다.")

    def reset_sys_limits(self):
        if not messagebox.askyesno("전체 초기화", "모든 시스템 항목을 기본값으로 되돌리시겠습니까?"): return
        for key, defn in self.cfg.current_config.get("system_limits", {}).items():
            if key == "easyrpg_max_item_count":
                continue
            if "default" in defn:
                defn["value"] = copy.deepcopy(defn["default"])
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        self._show_placeholder()
        messagebox.showinfo("초기화 완료", "모든 시스템 항목이 기본값으로 복구되었습니다.")
