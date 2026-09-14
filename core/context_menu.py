"""
core/context_menu.py
좌측 리스트(Treeview)에 공통으로 붙이는 우클릭 컨텍스트 메뉴.
"위로 이동 / 아래로 이동 / 삭제"를 제공하며, 삭제는 선택적으로 뺄 수 있습니다
(예: System 탭은 항목을 삭제할 수 없으므로 on_delete를 넘기지 않습니다).

새 탭을 추가할 때도 이 함수 하나만 호출하면 동일한 우클릭 메뉴가 그대로 재사용됩니다:
    attach_row_context_menu(self.actor_tree, self.move_actor_up, self.move_actor_down, self.delete_actor_rule)
"""
import tkinter as tk
from core.theme import BG2, FG, ACCENT_HOVER, BORDER
from core.i18n import t


def attach_row_context_menu(tree, on_move_up, on_move_down, on_delete=None):
    """tree: 우클릭 메뉴를 붙일 ttk.Treeview
    on_move_up / on_move_down: 인자 없이 호출되는 콜백 (우클릭 시점에 이미 해당 행이 선택되어 있습니다)
    on_delete: None이면 삭제 메뉴 항목을 아예 표시하지 않습니다."""
    menu = tk.Menu(tree, tearoff=0, bg=BG2, fg=FG, activebackground=ACCENT_HOVER,
                    activeforeground=FG, bd=0, relief="flat")
    menu.add_command(label=t("context_menu.move_up"), command=lambda: on_move_up())
    menu.add_command(label=t("context_menu.move_down"), command=lambda: on_move_down())
    if on_delete is not None:
        menu.add_separator()
        menu.add_command(label=t("context_menu.delete"), command=lambda: on_delete())

    def _on_right_click(event):
        iid = tree.identify_row(event.y)
        if not iid:
            return
        tree.selection_set(iid)
        tree.focus(iid)
        menu.tk_popup(event.x_root, event.y_root)

    tree.bind("<Button-3>", _on_right_click)
    return menu
