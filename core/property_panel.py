"""
core/property_panel.py
System 탭 / Skill 탭 등 여러 탭에서 재사용하는 "속성 편집기" 스타일 공통 컴포넌트.

- make_fixed_scroll_panel(): 크기가 고정된 컨테이너를 만듭니다. 내부 내용(필드 개수)이
  아무리 늘어나도 바깥 레이아웃은 절대 흔들리지 않고, 넘치는 내용은 안에서만 스크롤됩니다.
- render_field_row(): 필드 정의(type/label/description/...) 하나를 받아 타입에 맞는
  편집 컨트롤을 그리고, 값이 바뀔 때마다 on_change(new_value)를 호출합니다.
  (list 타입은 탭마다 UI가 크게 달라 각 탭에서 직접 그립니다.)

새로운 EasyRPG 옵션이 늘어날 때, 탭 코드는 필드 "정의(dict)"만 목록에 추가하면 되고
실제 위젯을 그리는 코드는 건드릴 필요가 없도록 하는 것이 이 모듈의 목적입니다.
"""
import tkinter as tk
from tkinter import ttk

from core.theme import BG, BG2, FG, FG_DIM, BORDER, make_checkbutton

# System/Skill/Item 탭이 공통으로 사용하는 속성 편집기 고정 크기
DETAIL_WIDTH = 320
DETAIL_HEIGHT = 560


def make_fixed_scroll_panel(parent, width=DETAIL_WIDTH, height=DETAIL_HEIGHT):
    """크기가 고정된 스크롤 패널을 만들어 (outer, inner) 프레임을 반환합니다.
    위젯은 inner 안에 pack()하면 됩니다. inner의 내용이 늘어나도 outer 크기는 고정입니다."""
    outer = tk.Frame(parent, bg=BG, width=width, height=height,
                      highlightthickness=1, highlightbackground=BORDER)
    outer.pack_propagate(False)

    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
    vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=BG)

    inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)

    def _on_inner_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>", _on_inner_configure)

    def _on_canvas_configure(event):
        canvas.itemconfig(inner_id, width=event.width)
    canvas.bind("<Configure>", _on_canvas_configure)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # 마우스가 패널 위에 있는 동안에만 전역으로 휠 이벤트를 가로챕니다.
    # (canvas 위젯에만 바인딩하면 그 위에 올라간 내부 위젯(Entry/Label 등)에
    #  마우스가 올라갔을 때는 휠 이벤트가 canvas까지 전달되지 않아 스크롤이
    #  먹통이 되므로, outer 진입/이탈 시점에 bind_all로 켜고 끕니다.)
    def _activate(event):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    def _deactivate(event):
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    outer.bind("<Enter>", _activate)
    outer.bind("<Leave>", _deactivate)

    def _on_key_scroll(event):
        if event.keysym == "Prior":
            canvas.yview_scroll(-1, "pages")
        elif event.keysym == "Next":
            canvas.yview_scroll(1, "pages")
        elif event.keysym == "Up":
            canvas.yview_scroll(-1, "units")
        elif event.keysym == "Down":
            canvas.yview_scroll(1, "units")

    canvas.bind("<Key-Prior>", _on_key_scroll)
    canvas.bind("<Key-Next>", _on_key_scroll)
    canvas.bind("<Key-Up>", _on_key_scroll)
    canvas.bind("<Key-Down>", _on_key_scroll)

    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    outer.scroll_canvas = canvas  # 렌더링 후 스크롤 위치 제어(맨 위로 리셋, 특정 그룹으로 이동 등)에 사용
    return outer, inner


def scroll_panel_to_top(outer):
    """패널 내용을 다시 그린 뒤 이전 스크롤 위치가 남아 하단(또는 엉뚱한 위치)이
    보이는 문제를 막기 위해, 스크롤 위치를 맨 위로 되돌립니다."""
    canvas = getattr(outer, "scroll_canvas", None)
    if canvas is not None:
        canvas.yview_moveto(0)


def scroll_panel_to_widget(outer, widget):
    """패널 안의 특정 위젯(예: 그룹 헤더)이 보이도록 스크롤 위치를 이동합니다."""
    canvas = getattr(outer, "scroll_canvas", None)
    if canvas is None or widget is None:
        return
    canvas.update_idletasks()
    bbox = canvas.bbox("all")
    if not bbox:
        return
    total_height = bbox[3] - bbox[1]
    if total_height <= 0:
        return
    fraction = max(0.0, min(1.0, widget.winfo_y() / total_height))
    canvas.yview_moveto(fraction)


def render_group_header(parent, text):
    ttk.Label(parent, text=text, font=("Segoe UI", 10, "bold"),
              foreground="#7fb6e0").pack(anchor="w", pady=(14, 2))
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(0, 4))


def render_field_row(parent, field_def, value, on_change):
    """필드 하나(label/description/컨트롤)를 그립니다.
    반환값: (컨트롤_위젯, set_enabled(bool) 함수) - 조건부 활성/비활성에 사용."""
    t = field_def.get("type", "int")
    name = field_def.get("name")

    ttk.Label(parent, text=field_def.get("label", name),
              font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
    if field_def.get("description"):
        ttk.Label(parent, text=field_def["description"], foreground=FG_DIM,
                  wraplength=250).pack(anchor="w")

    control = None
    set_enabled = lambda enabled: None

    if t == "int":
        entry = ttk.Entry(parent, width=24)
        entry.insert(0, str(value))

        def _commit(event=None):
            raw = entry.get().strip()
            try:
                v = int(raw)
            except ValueError:
                v = field_def.get("default", 0)
                entry.delete(0, tk.END); entry.insert(0, str(v))
            max_limit = field_def.get("max")
            if max_limit is not None and max_limit >= 0 and v > max_limit:
                v = max_limit
                entry.delete(0, tk.END); entry.insert(0, str(v))
            on_change(v)

        entry.bind("<Return>", _commit)
        entry.bind("<FocusOut>", _commit)
        entry._commit = _commit  # 테스트/자동화에서 커밋 로직을 직접 호출할 수 있도록 노출
        entry.pack(anchor="w", pady=(2, 4))
        control = entry

        def set_enabled(enabled):
            entry.configure(state="normal" if enabled else "disabled")

    elif t == "string":
        entry = ttk.Entry(parent, width=24)
        entry.insert(0, str(value))

        def _commit(event=None):
            on_change(entry.get())

        entry.bind("<Return>", _commit)
        entry.bind("<FocusOut>", _commit)
        entry._commit = _commit  # 테스트/자동화에서 커밋 로직을 직접 호출할 수 있도록 노출
        entry.pack(anchor="w", pady=(2, 4))
        control = entry

        def set_enabled(enabled):
            entry.configure(state="normal" if enabled else "disabled")

    elif t == "bool":
        var = tk.BooleanVar(value=bool(value))

        def _toggle():
            on_change(bool(var.get()))

        cb = make_checkbutton(parent, "사용함", var, command=_toggle)
        cb.pack(anchor="w", pady=(2, 4))
        control = cb

        def set_enabled(enabled):
            cb.configure(state="normal" if enabled else "disabled")

    elif t == "enum":
        options = field_def.get("options", {})
        items = sorted(options.items(), key=lambda kv: str(kv[0]))
        labels = [f"{k} : {v}" for k, v in items]
        var = tk.StringVar()
        cur_label = next((f"{k} : {v}" for k, v in items if str(k) == str(value)),
                          labels[0] if labels else "")
        var.set(cur_label)
        combo = ttk.Combobox(parent, textvariable=var, values=labels, state="readonly", width=30)

        def _select(event=None):
            sel = var.get()
            key = sel.split(":")[0].strip()
            try:
                key_cast = int(key)
            except ValueError:
                key_cast = key
            on_change(key_cast)

        combo.bind("<<ComboboxSelected>>", _select)
        combo.pack(anchor="w", pady=(2, 4))
        control = combo

        def set_enabled(enabled):
            combo.configure(state="readonly" if enabled else "disabled")

    return control, set_enabled
