"""
core/stat_editor_popup.py
Actor 탭, Class 탭 등 "레벨(단계)별 능력치 배열"을 갖는 개체라면 공통으로 재사용하는
능력치 편집 팝업. Actor 탭 전용 코드가 아니라 core/에 둬서, 새 탭이 능력치 배열을
다뤄야 할 때 이 함수 하나만 불러쓰면 되도록 만들었습니다.

레벨 1~99 / 100~N 을 별도 탭으로 나눠서 편집하지만, 실제로 저장되는 데이터는 각
능력치 태그(maxhp/maxsp/attack/defense/spirit/agility) 안에 1레벨부터 마지막 레벨까지
하나로 이어진 공백 구분 문자열입니다 - UI만 두 구간으로 나뉘어 있을 뿐, entry["parameters"]
자체는 항상 하나의 연속된 배열입니다.

두 탭 모두 동일한 일괄 설정 도구를 제공합니다. 각 탭의 "기준 레벨(anchor)"은
Lv.1~99 탭은 Lv.1, Lv.100~N 탭은 Lv.99이며, "레벨당 상승"류 계산은 이 기준 레벨의
현재 값에서부터 누적됩니다.

[오버플로우 방지에 대한 참고]
RPG Maker 2003에서 능력치 파라미터를 편집기에서 직접 다시 저장했을 때 값이
1/0/6/7/1/1 같은 값으로 깨지는 현상이 보고되어, 능력치 값에 상한(MAX_STAT_VALUE)을
두었습니다. RPG Maker 2000/2003의 데이터베이스 편집기가 능력치류 수치를 전통적으로
9999까지만 받는 것으로 알려져 있어 이 값을 상한으로 잡았습니다 - 정확한 한계값을
알고 계시면 이 상수만 바꾸면 됩니다.
"""
import random
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import BG, BG2, FG, FG_DIM
from core.property_panel import make_horizontal_scroll_panel
from core.logger import log
from core.i18n import t

MAX_STAT_VALUE = 9999
MIN_STAT_VALUE = 0
LOW_TIER_START = 1
LOW_TIER_END = 99
HIGH_TIER_START = 100


def _clamp(v):
    return max(MIN_STAT_VALUE, min(MAX_STAT_VALUE, v))


def open_stat_editor_popup(app, cfg, entry, entity_label, final_level, stat_keys, stat_label_keys):
    """레벨별 능력치 편집 팝업을 엽니다.
    entry: {"parameters": {stat_key: [값, 값, ...]}, ...} 형태의 dict (그 자리에서 값이 수정됩니다)
    entity_label: 팝업 제목에 쓸 이름(예: "알렉스", "전사")
    final_level: 이 개체의 능력치 배열 길이(=편집 가능한 최대 레벨)
    stat_keys / stat_label_keys: 편집할 능력치 키 목록과 표시용 i18n 키 매핑
    """
    root = app.root
    main_w = max(root.winfo_width(), 800)
    main_h = max(root.winfo_height(), 600)
    popup = tk.Toplevel(root, bg=BG)
    popup.title(t("stat_editor.title", name=entity_label))
    # 닫기 버튼이 잘리지 않도록 기본 계산 높이(창의 1/3)에 여유분을 더합니다.
    popup.geometry(f"{main_w}x{(main_h // 3) + 40}")
    popup.transient(root)

    header = ttk.Frame(popup, padding=10)
    header.pack(fill="x", side="top")
    ttk.Label(header, text=t("stat_editor.notice", max=final_level),
              foreground=FG_DIM, wraplength=main_w - 40).pack(anchor="w")

    if final_level < LOW_TIER_START:
        ttk.Label(popup, text=t("stat_editor.no_levels"), padding=20).pack(anchor="w")
        ttk.Button(popup, text=t("common.btn_close"), command=popup.destroy).pack(pady=10)
        return

    # 닫기 버튼을 노트북보다 먼저 side="bottom"으로 배치해 항상 자기 공간을 확보합니다.
    # (먼저 배치하지 않으면 노트북이 남는 공간을 전부 차지해 버튼이 화면 밖으로 밀려
    #  안 보이게 됩니다 - 이 파일의 다른 스크롤바들과 같은 이유의 같은 처방입니다.)
    ttk.Button(popup, text=t("common.btn_close"), command=popup.destroy).pack(side="bottom", pady=10)

    notebook = ttk.Notebook(popup)
    notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10), side="top")

    def _on_change():
        cfg.save_config()
        app.refresh_all_tabs()

    low_end = min(LOW_TIER_END, final_level)
    tab_low = ttk.Frame(notebook, padding=5)
    notebook.add(tab_low, text=t("stat_editor.tab_low"))
    _build_tier_tab(tab_low, entry, stat_keys, stat_label_keys,
                     anchor_level=LOW_TIER_START, range_start=LOW_TIER_START, range_end=low_end,
                     main_w=main_w, on_change=_on_change, entity_label=entity_label)

    if final_level >= HIGH_TIER_START:
        tab_high = ttk.Frame(notebook, padding=5)
        notebook.add(tab_high, text=t("stat_editor.tab_high", max=final_level))
        _build_tier_tab(tab_high, entry, stat_keys, stat_label_keys,
                         anchor_level=LOW_TIER_END, range_start=HIGH_TIER_START, range_end=final_level,
                         main_w=main_w, on_change=_on_change, entity_label=entity_label)


def _draw_grid(grid_inner, entry, stat_keys, stat_label_keys, level_start, level_end, on_change):
    for w in grid_inner.winfo_children():
        w.destroy()
    levels = list(range(level_start, level_end + 1))

    tk.Label(grid_inner, text=t("stat_editor.col_level_header"), bg=BG2, fg=FG,
             width=16, relief="ridge", anchor="w").grid(row=0, column=0, sticky="nsew")
    for j, level in enumerate(levels):
        tk.Label(grid_inner, text=f"Lv.{level}", bg=BG2, fg=FG, width=7, relief="ridge").grid(row=0, column=j + 1, sticky="nsew")

    for i, key in enumerate(stat_keys):
        tk.Label(grid_inner, text=t(stat_label_keys[key]), bg=BG2, fg=FG,
                 width=16, anchor="w", relief="ridge").grid(row=i + 1, column=0, sticky="nsew")
        for j, level in enumerate(levels):
            idx = level - 1
            values = entry["parameters"].setdefault(key, [])
            current_val = values[idx] if idx < len(values) else 0
            e = tk.Entry(grid_inner, width=7, bg=BG2, fg=FG, insertbackground=FG,
                         relief="flat", justify="center")
            e.insert(0, str(current_val))
            e.grid(row=i + 1, column=j + 1, padx=1, pady=1, sticky="nsew")

            def _commit(event=None, key=key, idx=idx, entry_widget=e):
                try:
                    v = _clamp(int(entry_widget.get().strip()))
                except ValueError:
                    v = entry["parameters"][key][idx]
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, str(v))
                if entry["parameters"][key][idx] != v:
                    entry["parameters"][key][idx] = v
                    on_change()

            e._commit = _commit
            e.bind("<Return>", _commit)
            e.bind("<FocusOut>", _commit)


def _build_tier_tab(parent, entry, stat_keys, stat_label_keys, anchor_level, range_start, range_end,
                     main_w, on_change, entity_label):
    """탭 하나(Lv.1~99 또는 Lv.100~N)의 그리드 + 일괄 설정 도구를 만듭니다.
    anchor_level: 일괄 계산의 기준이 되는 레벨(그 레벨의 현재 값에서부터 누적 계산)."""
    control = ttk.Frame(parent, padding=(0, 6, 0, 0))
    control.pack(fill="x", side="bottom")

    grid_outer, grid_inner = make_horizontal_scroll_panel(parent, width=main_w - 40, height=140)
    grid_outer.pack(fill="both", expand=True, side="top")

    def rebuild_grid():
        _draw_grid(grid_inner, entry, stat_keys, stat_label_keys, range_start, range_end, on_change)

    rebuild_grid()

    def _anchor_value(key):
        values = entry["parameters"].get(key, [])
        return values[anchor_level - 1] if len(values) >= anchor_level else 0

    def apply_fill_anchor():
        # 전체 초기화 성격의 동작이라 능력치 체크박스 선택과 무관하게 항상 전부 적용됩니다.
        for key in stat_keys:
            base_val = _anchor_value(key)
            values = entry["parameters"].setdefault(key, [])
            for level in range(range_start, range_end + 1):
                values[level - 1] = _clamp(base_val)
        on_change()
        log.info(t("stat_editor.log_batch_applied", name=entity_label, max=range_end,
                   method=t("stat_editor.btn_fill_anchor", level=anchor_level)))
        rebuild_grid()

    # ---- 능력치별 선택 체크박스 ----
    # 아래 세 가지 일괄 계산(레벨당 +N ± n% 난수 / 목표치까지 점진적 상승 / 목표치까지
    # ± n% 난수 상승)은 체크된 능력치에만 적용됩니다. 예) HP만 체크하고 적용하면 HP만
    # 바뀌고 나머지는 그대로 유지되며, 이후 체크를 SP로 바꿔 다시 적용해도 앞서 바뀐
    # HP 값은 그대로 남고 SP만 추가로 바뀝니다(서로 덮어쓰지 않고 독립적으로 누적 적용).
    stat_check_vars = {key: tk.BooleanVar(value=True) for key in stat_keys}

    def _selected_keys():
        return [key for key in stat_keys if stat_check_vars[key].get()]

    def apply_increment_random():
        keys = _selected_keys()
        if not keys:
            messagebox.showwarning(t("common.title_warning"), t("stat_editor.msg_no_stat_selected"))
            return
        try:
            n = float(increment_n_entry.get().strip())
            pct = max(0.0, float(increment_pct_entry.get().strip()))
        except ValueError:
            messagebox.showerror(t("common.title_error"), t("stat_editor.msg_invalid_number"))
            return
        for key in keys:
            base_val = _anchor_value(key)
            values = entry["parameters"].setdefault(key, [])
            current = float(base_val)
            low, high = n * (1 - pct / 100.0), n * (1 + pct / 100.0)
            for level in range(range_start, range_end + 1):
                current += random.uniform(low, high)
                values[level - 1] = _clamp(round(current))
        on_change()
        log.info(t("stat_editor.log_batch_applied", name=entity_label, max=range_end,
                   method=t("stat_editor.label_increment_random") + f" {n}±{pct}% ({', '.join(keys)})"))
        rebuild_grid()

    def apply_target_random():
        # 기본 상승치는 "목표치까지 점진적 상승"과 동일하게 계산하되(레벨당 (목표-기준)/구간),
        # 매 레벨 증분에 ± n% 난수를 얹어서 누적합니다. 그래서 최종(레벨상한 시점) 값은
        # 목표치 부근에서 위아래로 흔들리며, 정확히 목표치에 맞춰지지 않을 수 있습니다
        # (요청하신 의도 그대로: 최종 능력치가 목표값보다 크거나 작을 수 있음).
        keys = _selected_keys()
        if not keys:
            messagebox.showwarning(t("common.title_warning"), t("stat_editor.msg_no_stat_selected"))
            return
        try:
            target = int(target_random_entry.get().strip())
            pct = max(0.0, float(target_random_pct_entry.get().strip()))
        except ValueError:
            messagebox.showerror(t("common.title_error"), t("stat_editor.msg_invalid_number"))
            return
        span = range_end - anchor_level
        if span <= 0:
            return
        for key in keys:
            base_val = _anchor_value(key)
            step = (target - base_val) / span
            variance = abs(step) * (pct / 100.0)
            values = entry["parameters"].setdefault(key, [])
            current = float(base_val)
            for level in range(range_start, range_end + 1):
                current += step + random.uniform(-variance, variance)
                values[level - 1] = _clamp(round(current))
        on_change()
        log.info(t("stat_editor.log_batch_applied", name=entity_label, max=range_end,
                   method=t("stat_editor.label_target_random") + f" {target}±{pct}% ({', '.join(keys)})"))
        rebuild_grid()

    row1 = ttk.Frame(control); row1.pack(fill="x", pady=2)
    ttk.Button(row1, text=t("stat_editor.btn_fill_anchor", level=anchor_level), command=apply_fill_anchor).pack(side="left")

    check_row = ttk.Frame(control); check_row.pack(fill="x", pady=(6, 2))
    ttk.Label(check_row, text=t("stat_editor.label_stat_checkboxes"), foreground=FG_DIM).pack(side="left", padx=(0, 8))
    for key in stat_keys:
        cb = tk.Checkbutton(check_row, text=t(stat_label_keys[key]), variable=stat_check_vars[key],
                             bg=BG, fg=FG, selectcolor=BG2, activebackground=BG, activeforeground=FG,
                             highlightthickness=0)
        cb.pack(side="left", padx=4)

    row2 = ttk.Frame(control); row2.pack(fill="x", pady=2)
    ttk.Label(row2, text=t("stat_editor.label_increment_random")).pack(side="left", padx=(0, 4))
    increment_n_entry = ttk.Entry(row2, width=8); increment_n_entry.insert(0, "0"); increment_n_entry.pack(side="left", padx=(0, 2))
    ttk.Label(row2, text="±").pack(side="left")
    increment_pct_entry = ttk.Entry(row2, width=6); increment_pct_entry.insert(0, "10"); increment_pct_entry.pack(side="left", padx=(2, 4))
    ttk.Label(row2, text="%").pack(side="left", padx=(0, 4))
    ttk.Button(row2, text=t("stat_editor.btn_apply"), command=apply_increment_random).pack(side="left")

    row3 = ttk.Frame(control); row3.pack(fill="x", pady=2)
    ttk.Label(row3, text=t("stat_editor.label_target_random")).pack(side="left", padx=(0, 4))
    target_random_entry = ttk.Entry(row3, width=8); target_random_entry.insert(0, "0"); target_random_entry.pack(side="left", padx=(0, 2))
    ttk.Label(row3, text="±").pack(side="left")
    target_random_pct_entry = ttk.Entry(row3, width=6); target_random_pct_entry.insert(0, "10"); target_random_pct_entry.pack(side="left", padx=(2, 4))
    ttk.Label(row3, text="%").pack(side="left", padx=(0, 4))
    ttk.Button(row3, text=t("stat_editor.btn_apply"), command=apply_target_random).pack(side="left")
