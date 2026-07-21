"""
tabs/system_tab.py
"시스템 상한 제한 조절" 탭 - config.json의 system_limits를 type(int/bool/enum/list)에
따라 자동으로 알맞은 편집 UI를 생성하는 "속성 편집기" 스타일 탭입니다.
새 EasyRPG 시스템 옵션은 core/config.py의 DEFAULT_SYSTEM_DEFS(또는 프로그램 config.json)에
항목만 추가하면 이 탭에 자동으로 나타납니다.

우측 편집 패널은 core.property_panel.make_fixed_scroll_panel()로 만든 고정 크기
컨테이너라서, 어떤 타입의 필드를 선택해도 패널 크기가 흔들리지 않습니다.
"""
import copy
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import FG_DIM, attach_tree_scrollbar, make_listbox_with_scroll, make_checkbutton, enable_column_sort, enable_column_width_persistence
from core.property_panel import make_fixed_scroll_panel, render_field_row, render_group_header, scroll_panel_to_top, DETAIL_WIDTH, DETAIL_HEIGHT
from core.logger import log

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

        left_frame = ttk.Frame(sys_frame)
        left_frame.pack(fill="both", expand=True, side="left")

        filter_row = ttk.Frame(left_frame)
        filter_row.pack(fill="x", pady=(0, 6))
        ttk.Label(filter_row, text="그룹:").pack(side="left", padx=(0, 6))
        self.group_filter_var = tk.StringVar(value="전체")
        self.group_filter_combo = ttk.Combobox(filter_row, textvariable=self.group_filter_var,
                                                state="readonly", width=16)
        self.group_filter_combo.pack(side="left")
        self.group_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        tree_row = ttk.Frame(left_frame)
        tree_row.pack(fill="both", expand=True)
        columns = ("이름", "그룹", "타입", "현재값", "최대값")
        self.sys_tree = ttk.Treeview(tree_row, columns=columns, show="headings", height=18)
        for col, txt in [("이름", "옵션명"), ("그룹", "그룹"), ("타입", "타입"),
                          ("현재값", "현재값"), ("최대값", "최대값")]:
            self.sys_tree.heading(col, text=txt)
        self.sys_tree.pack(fill="both", expand=True, side="left")
        attach_tree_scrollbar(self.sys_tree, tree_row)

        self.sys_tree.column("이름", width=170, anchor="w")
        self.sys_tree.column("그룹", width=80, anchor="center")
        self.sys_tree.column("타입", width=80, anchor="center")
        self.sys_tree.column("현재값", width=150, anchor="w")
        self.sys_tree.column("최대값", width=110, anchor="w")
        self.sys_tree.bind("<<TreeviewSelect>>", self.on_sys_select)
        enable_column_sort(self.sys_tree, columns, numeric_columns=("최대값",))
        enable_column_width_persistence(self.sys_tree, self.cfg, "sys_tree")

        sys_side_frame = ttk.Frame(sys_frame, padding=(10, 0))
        sys_side_frame.pack(fill="y", side="right")

        self.detail_outer, self.sys_detail_frame = make_fixed_scroll_panel(
            sys_side_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

        ttk.Button(sys_side_frame, text="🔄 모든 항목 기본값으로 초기화",
                   command=self.reset_sys_limits).pack(fill="x", pady=(12, 3))

    def _show_placeholder(self):
        for w in self.sys_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.sys_detail_frame, text="왼쪽 목록에서 항목을 선택하세요.", foreground=FG_DIM,
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    # ------------------------------------------------------------------
    def _all_groups(self):
        groups = sorted({defn.get("group", "일반") for defn in self.cfg.current_config.get("system_limits", {}).values()})
        return ["전체"] + groups

    def refresh(self):
        self.group_filter_combo.configure(values=self._all_groups())
        if self.group_filter_var.get() not in self._all_groups():
            self.group_filter_var.set("전체")

        selected = self.sys_tree.selection()
        prev_iid = selected[0] if selected else None

        for sys_item in self.sys_tree.get_children(): self.sys_tree.delete(sys_item)
        active_group = self.group_filter_var.get()
        for key, defn in self.cfg.current_config.get("system_limits", {}).items():
            if key == "easyrpg_max_item_count":
                continue
            group = defn.get("group", "일반")
            if active_group != "전체" and group != active_group:
                continue
            self.sys_tree.insert("", "end", iid=key, values=(
                defn.get("name", key), group,
                TYPE_LABEL_MAP.get(defn.get("type", "int"), defn.get("type")),
                self.format_sys_value(defn),
                self.format_sys_max(defn),
            ))

        if prev_iid and self.sys_tree.exists(prev_iid):
            self.sys_tree.selection_set(prev_iid)
            self.sys_tree.see(prev_iid)

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

    def format_sys_max(self, defn):
        if defn.get("type") != "int":
            return "-"
        max_val = defn.get("max")
        if max_val is None:
            return "-"
        try:
            return f"{max_val:,}"
        except (TypeError, ValueError):
            return str(max_val)

    def find_sys_def(self, name):
        return self.cfg.find_sys_def(name)

    # ------------------------------------------------------------------
    # 타입별 동적 편집 패널 (고정 크기 패널 안에서만 스크롤)
    # ------------------------------------------------------------------
    def on_sys_select(self, event):
        selected = self.sys_tree.selection()
        if not selected: return
        key = selected[0]
        defn = self.find_sys_def(key)
        if defn:
            self.render_sys_detail(key, defn)

    def render_sys_detail(self, key, defn):
        for w in self.sys_detail_frame.winfo_children():
            w.destroy()
        self._current_sys_key = key
        self._current_sys_def = defn
        t = defn.get("type", "int")
        p = self.sys_detail_frame

        ttk.Label(p, text=defn.get("name", key), font=("Segoe UI", 11, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 2))
        ttk.Label(p, text=key, foreground=FG_DIM).pack(anchor="w", padx=8, pady=(0, 6))
        if defn.get("description"):
            ttk.Label(p, text=defn["description"], foreground=FG_DIM,
                      wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(0, 8))

        body = ttk.Frame(p)
        body.pack(fill="x", padx=8)

        if t in ("int", "bool", "enum"):
            def _on_change(new_val):
                self._current_sys_def["value"] = new_val
                self.cfg.save_config()
                self.refresh()
                log.info(f"[{self._current_sys_def.get('name')}] 값 저장: {new_val}")
            render_field_row(body, defn, defn.get("value"), _on_change)

        elif t == "list":
            self._render_list_field(body, defn)

        scroll_panel_to_top(self.detail_outer)

    def _render_list_field(self, parent, defn):
        options = defn.get("options", {})
        options_sorted = sorted(options.items(), key=lambda kv: int(kv[0]))
        current_vals = defn.get("value", []) or []
        self.sys_list_vars = {}
        self.sys_list_order = [v for v in current_vals]

        for k_str, label in options_sorted:
            v = int(k_str)
            var = tk.BooleanVar(value=v in current_vals)
            self.sys_list_vars[v] = var
            make_checkbutton(parent, label, var, command=self.refresh_sys_list_order).pack(anchor="w")

        ttk.Label(parent, text="적용 순서:").pack(anchor="w", pady=(10, 2))
        list_frame, self.sys_list_order_box = make_listbox_with_scroll(parent, height=5)
        list_frame.pack(anchor="w", fill="x", pady=(0, 6))

        btn_row = ttk.Frame(parent); btn_row.pack(fill="x")
        ttk.Button(btn_row, text="▲ 위로", command=lambda: self.move_sys_list_item(-1)).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_row, text="▼ 아래로", command=lambda: self.move_sys_list_item(1)).pack(side="left", expand=True, fill="x")
        ttk.Button(parent, text="✏️ 적용", command=self.apply_sys_list).pack(fill="x", pady=(8, 4))

        self.refresh_sys_list_order()

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
        self.refresh()
        log.info(f"[{self._current_sys_def.get('name')}] 값 저장: {self.sys_list_order}")

    def reset_sys_limits(self):
        if not messagebox.askyesno("전체 초기화", "모든 시스템 항목을 기본값으로 되돌리시겠습니까?"): return
        for key, defn in self.cfg.current_config.get("system_limits", {}).items():
            if key == "easyrpg_max_item_count":
                continue
            if "default" in defn:
                defn["value"] = copy.deepcopy(defn["default"])
        self.cfg.save_config()
        self.refresh()
        self._show_placeholder()
        log.info("모든 시스템 항목을 기본값으로 초기화함")
        messagebox.showinfo("초기화 완료", "모든 시스템 항목이 기본값으로 복구되었습니다.")
