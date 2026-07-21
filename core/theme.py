"""
core/theme.py
다크 테마 색상 팔레트, ttk 스타일 적용, 여러 탭에서 공통으로 쓰는
다크 테마 위젯 생성 헬퍼(스크롤바 달린 리스트박스, 트리뷰 스크롤바, 체크박스).
"""
import tkinter as tk
from tkinter import ttk

# ---- 다크 테마 색상 팔레트 ----
BG = "#1e1e1e"
BG2 = "#252526"
BG3 = "#2d2d30"
FG = "#e0e0e0"
FG_DIM = "#9a9a9a"
ACCENT = "#3c3f41"
ACCENT_HOVER = "#505354"
SELECT_BG = "#0a5a8a"
BORDER = "#454545"


def apply_dark_theme(root):
    root.configure(bg=BG)
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=BG, foreground=FG, fieldbackground=BG2,
                     bordercolor=BORDER, darkcolor=BG, lightcolor=BG)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("TButton", background=ACCENT, foreground=FG, padding=6, borderwidth=1)
    style.map("TButton",
              background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)],
              foreground=[("disabled", FG_DIM)])
    style.configure("TEntry", fieldbackground=BG2, foreground=FG, insertcolor=FG,
                     bordercolor=BORDER)
    style.map("TEntry", fieldbackground=[("readonly", BG2)])
    style.configure("TCombobox", fieldbackground=BG2, background=BG2, foreground=FG,
                     arrowcolor=FG, bordercolor=BORDER)
    style.map("TCombobox", fieldbackground=[("readonly", BG2)], foreground=[("readonly", FG)])
    style.configure("TNotebook", background=BG, bordercolor=BORDER)
    style.configure("TNotebook.Tab", background=ACCENT, foreground=FG, padding=(12, 6))
    style.map("TNotebook.Tab", background=[("selected", BG3)], foreground=[("selected", "#ffffff")])
    style.configure("Treeview", background=BG2, fieldbackground=BG2, foreground=FG,
                     bordercolor=BORDER, rowheight=24)
    style.configure("Treeview.Heading", background=ACCENT, foreground=FG, relief="flat")
    style.map("Treeview.Heading", background=[("active", ACCENT_HOVER)])
    style.map("Treeview", background=[("selected", SELECT_BG)], foreground=[("selected", "#ffffff")])
    style.configure("Vertical.TScrollbar", background=ACCENT, troughcolor=BG2,
                     bordercolor=BORDER, arrowcolor=FG, relief="flat")
    style.map("Vertical.TScrollbar", background=[("active", ACCENT_HOVER)])


def attach_tree_scrollbar(tree, parent):
    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="left", fill="y")


def make_listbox_with_scroll(parent, height=6):
    frame = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
    scrollbar = ttk.Scrollbar(frame, orient="vertical")
    listbox = tk.Listbox(frame, height=height, bg=BG2, fg=FG,
                          selectbackground=SELECT_BG, selectforeground="#ffffff",
                          highlightthickness=0, relief="flat", activestyle="none",
                          yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return frame, listbox


def make_checkbutton(parent, text, variable, command=None):
    return tk.Checkbutton(parent, text=text, variable=variable, command=command,
                           bg=BG, fg=FG, selectcolor=BG2, activebackground=BG,
                           activeforeground=FG, highlightthickness=0)


def enable_column_sort(tree, columns, numeric_columns=None):
    """트리뷰 헤더를 클릭하면 해당 컬럼 기준으로 오름/내림차순 정렬합니다."""
    numeric_columns = set(numeric_columns or [])
    state = {"col": None, "reverse": False}

    def _sort(col):
        rows = [(tree.set(k, col), k) for k in tree.get_children("")]

        def keyfunc(pair):
            val = str(pair[0])
            if col in numeric_columns:
                try:
                    return (0, float(val.replace(",", "")))
                except ValueError:
                    return (-1, 0.0)
            return (0, val)

        reverse = (not state["reverse"]) if state["col"] == col else False
        rows.sort(key=keyfunc, reverse=reverse)
        for index, (_, k) in enumerate(rows):
            tree.move(k, "", index)
        state["col"] = col
        state["reverse"] = reverse

    for col in columns:
        tree.heading(col, command=lambda c=col: _sort(c))


def enable_column_width_persistence(tree, cfg, storage_key):
    """트리뷰 컬럼 폭을 공통 설정(config.json)에 저장했다가 다음 실행 시 복원합니다."""
    saved = cfg.common_config.setdefault("settings", {}).setdefault("column_widths", {}).get(storage_key, {})
    for col, w in saved.items():
        try:
            tree.column(col, width=int(w))
        except Exception:
            pass

    def _save(event=None):
        widths = {col: tree.column(col, "width") for col in tree["columns"]}
        cfg.common_config.setdefault("settings", {}).setdefault("column_widths", {})[storage_key] = widths
        cfg.save_common_config()

    tree.bind("<ButtonRelease-1>", _save, add="+")


def remember_selection(tree, refresh_func):
    """refresh_func()로 트리뷰를 다시 채우되, 이전에 선택되어 있던 행(iid)을 그대로 복원합니다.
    트리뷰 insert 시 iid를 명시적으로 지정해 둔 경우에만 정상 동작합니다."""
    selected = tree.selection()
    prev_iid = selected[0] if selected else None
    refresh_func()
    if prev_iid and tree.exists(prev_iid):
        tree.selection_set(prev_iid)
        tree.see(prev_iid)
