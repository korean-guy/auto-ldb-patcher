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
