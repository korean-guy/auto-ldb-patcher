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
from core.context_menu import attach_row_context_menu
from core.property_panel import make_fixed_scroll_panel, render_field_row, render_group_header, scroll_panel_to_top, DETAIL_WIDTH, DETAIL_HEIGHT
from core.logger import log
from core.i18n import t, t_field

TYPE_LABEL_MAP = {"int": t("type_label.int"), "bool": t("type_label.bool"),
                   "enum": t("type_label.enum"), "list": t("type_label.list")}


class SystemTab:
    TITLE = t("system_tab.title")

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
        ttk.Label(filter_row, text=t("system_tab.label_group_filter")).pack(side="left", padx=(0, 6))
        self.group_filter_var = tk.StringVar(value=t("system_tab.group_all"))
        self.group_filter_combo = ttk.Combobox(filter_row, textvariable=self.group_filter_var,
                                                state="readonly", width=16)
        self.group_filter_combo.pack(side="left")
        self.group_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        tree_row = ttk.Frame(left_frame)
        tree_row.pack(fill="both", expand=True)
        columns = ("이름", "그룹", "타입", "현재값", "최대값")
        self.sys_tree = ttk.Treeview(tree_row, columns=columns, show="headings", height=18)
        for col, txt in [("이름", t("system_tab.col_name")), ("그룹", t("system_tab.col_group")),
                          ("타입", t("system_tab.col_type")), ("현재값", t("system_tab.col_value")),
                          ("최대값", t("system_tab.col_max"))]:
            self.sys_tree.heading(col, text=txt)
        attach_tree_scrollbar(self.sys_tree, tree_row)
        self.sys_tree.pack(fill="both", expand=True, side="left")

        self.sys_tree.column("이름", width=170, anchor="w")
        self.sys_tree.column("그룹", width=80, anchor="center")
        self.sys_tree.column("타입", width=80, anchor="center")
        self.sys_tree.column("현재값", width=150, anchor="w")
        self.sys_tree.column("최대값", width=110, anchor="w")
        self.sys_tree.bind("<<TreeviewSelect>>", self.on_sys_select)
        enable_column_sort(self.sys_tree, columns, numeric_columns=("최대값",))
        enable_column_width_persistence(self.sys_tree, self.cfg, "sys_tree")
        attach_row_context_menu(self.sys_tree, lambda: self.move_sys_entry(-1), lambda: self.move_sys_entry(1))

        sys_side_frame = ttk.Frame(sys_frame, padding=(10, 0))
        sys_side_frame.pack(fill="y", side="right")

        self.detail_outer, self.sys_detail_frame = make_fixed_scroll_panel(
            sys_side_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

        ttk.Button(sys_side_frame, text=t("system_tab.btn_reset_all"),
                   command=self.reset_sys_limits).pack(fill="x", pady=(12, 3))

    def _show_placeholder(self):
        for w in self.sys_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.sys_detail_frame, text=t("system_tab.placeholder"), foreground=FG_DIM,
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    # ------------------------------------------------------------------
    def _all_groups(self):
        groups = sorted({defn.get("group", "일반") for defn in self.cfg.current_config.get("system_limits", {}).values()})
        return [t("system_tab.group_all")] + groups

    def refresh(self):
        self.group_filter_combo.configure(values=self._all_groups())
        if self.group_filter_var.get() not in self._all_groups():
            self.group_filter_var.set(t("system_tab.group_all"))

        selected = self.sys_tree.selection()
        prev_iid = selected[0] if selected else None

        for sys_item in self.sys_tree.get_children(): self.sys_tree.delete(sys_item)
        active_group = self.group_filter_var.get()
        for key, defn in self.cfg.current_config.get("system_limits", {}).items():
            if key == "easyrpg_max_item_count":
                continue
            group = defn.get("group", "일반")
            if active_group != t("system_tab.group_all") and group != active_group:
                continue
            self.sys_tree.insert("", "end", iid=key, values=(
                t_field("sys", key, "name", defn.get("name", key)), group,
                TYPE_LABEL_MAP.get(defn.get("type", "int"), defn.get("type")),
                self.format_sys_value(defn),
                self.format_sys_max(defn),
            ))

        if prev_iid and self.sys_tree.exists(prev_iid):
            self.sys_tree.selection_set(prev_iid)
            self.sys_tree.see(prev_iid)

    def format_sys_value(self, defn):
        field_type = defn.get("type", "int")
        val = defn.get("value")
        if field_type == "bool":
            return t("system_tab.value_bool_on") if val else t("system_tab.value_bool_off")
        if field_type == "enum":
            label = defn.get("options", {}).get(str(val))
            return f'{val} ({label})' if label else str(val)
        if field_type == "list":
            options = defn.get("options", {})
            return " → ".join(options.get(str(v), str(v)) for v in (val or [])) or t("system_tab.value_list_empty")
        return t("system_tab.value_default_limit") if val == -1 else f"{val:,}"

    def format_sys_max(self, defn):
        if defn.get("type") != "int":
            return t("system_tab.value_max_none")
        max_val = defn.get("max")
        if max_val is None:
            return t("system_tab.value_max_none")
        try:
            return f"{max_val:,}"
        except (TypeError, ValueError):
            return str(max_val)

    def find_sys_def(self, name):
        return self.cfg.find_sys_def(name)

    def move_sys_entry(self, direction):
        """필터링된 목록에서 위/아래로 인접한 항목과 실제 순서를 맞바꿉니다
        (system_limits가 dict이므로, 두 키의 삽입 순서를 바꿔 저장합니다)."""
        sel = self.sys_tree.selection()
        if not sel: return
        key = sel[0]
        visible = list(self.sys_tree.get_children(""))
        idx = visible.index(key)
        new_idx = idx + direction
        if not (0 <= new_idx < len(visible)): return
        other_key = visible[new_idx]

        limits = self.cfg.current_config["system_limits"]
        keys = list(limits.keys())
        i1, i2 = keys.index(key), keys.index(other_key)
        keys[i1], keys[i2] = keys[i2], keys[i1]
        self.cfg.current_config["system_limits"] = {k: limits[k] for k in keys}
        self.cfg.save_config()
        self.refresh()

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
        field_type = defn.get("type", "int")
        p = self.sys_detail_frame

        display_name = t_field("sys", key, "name", defn.get("name", key))
        display_desc = t_field("sys", key, "description", defn.get("description", ""))
        ttk.Label(p, text=display_name, font=("Segoe UI", 11, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 2))
        ttk.Label(p, text=key, foreground=FG_DIM).pack(anchor="w", padx=8, pady=(0, 6))
        if display_desc:
            ttk.Label(p, text=display_desc, foreground=FG_DIM,
                      wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(0, 8))

        body = ttk.Frame(p)
        body.pack(fill="x", padx=8)

        if field_type in ("int", "bool", "enum"):
            def _on_change(new_val):
                self._current_sys_def["value"] = new_val
                self.cfg.save_config()
                self.refresh()
                log.info(t("system_tab.log_field_saved", name=self._current_sys_def.get("name"), value=new_val))
            render_field_row(body, defn, defn.get("value"), _on_change)

        elif field_type == "list":
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

        ttk.Label(parent, text=t("system_tab.label_apply_order")).pack(anchor="w", pady=(10, 2))
        list_frame, self.sys_list_order_box = make_listbox_with_scroll(parent, height=5)
        list_frame.pack(anchor="w", fill="x", pady=(0, 6))

        btn_row = ttk.Frame(parent); btn_row.pack(fill="x")
        ttk.Button(btn_row, text=t("system_tab.btn_move_up"), command=lambda: self.move_sys_list_item(-1)).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_row, text=t("system_tab.btn_move_down"), command=lambda: self.move_sys_list_item(1)).pack(side="left", expand=True, fill="x")
        ttk.Button(parent, text=t("system_tab.btn_apply"), command=self.apply_sys_list).pack(fill="x", pady=(8, 4))

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
        log.info(t("system_tab.log_field_saved", name=self._current_sys_def.get("name"), value=self.sys_list_order))

    def reset_sys_limits(self):
        if not messagebox.askyesno(t("system_tab.title_confirm_reset"), t("system_tab.msg_confirm_reset")): return
        for key, defn in self.cfg.current_config.get("system_limits", {}).items():
            if key == "easyrpg_max_item_count":
                continue
            if "default" in defn:
                defn["value"] = copy.deepcopy(defn["default"])
        self.cfg.save_config()
        self.refresh()
        self._show_placeholder()
        log.info(t("system_tab.log_reset_done"))
        messagebox.showinfo(t("system_tab.title_reset_done"), t("system_tab.msg_reset_done"))
