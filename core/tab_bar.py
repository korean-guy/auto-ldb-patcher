"""
core/tab_bar.py
상단 탭 선택 UI를 위한 ttk.Notebook 대체 위젯 (WrappingNotebook).

기존 ttk.Notebook은 탭이 많아지면 가로로 넘쳐서 화살표 버튼이 생기거나 잘려버립니다.
이 위젯은 탭 버튼을 직접 그려서, 가로 폭이 부족해지면 자동으로 다음 줄로 넘어가는
(1줄/2줄/3줄/...) 탭 바를 구현합니다. 줄 수를 미리 정해두지 않고, 창 폭과 탭 개수에
따라 매번 새로 계산하므로 탭이 계속 추가돼도 이 파일을 건드릴 필요가 없습니다.

tabs/*.py를 건드리지 않아도 되도록 ttk.Notebook과 최소한의 사용법을 맞췄습니다:
    notebook = WrappingNotebook(parent)
    notebook.place(relx=0, rely=0, relwidth=1, relheight=1)   # 또는 pack()
    frame = ttk.Frame(notebook, padding=10)   # notebook 자신이 부모 위젯 역할(기존과 동일)
    notebook.add(frame, text="탭 이름")

주의: 탭 페이지 프레임(frame)은 반드시 이 위젯(notebook) 자신을 부모로 생성해야 합니다
(tabs/*.py가 전부 `ttk.Frame(notebook, ...)` 형태라 자동으로 그렇게 됩니다). 다른 위젯에
재부모(reparent)시키는 트릭(pack(in_=...)) 없이, 탭 바와 탭 페이지 모두 이 위젯의 직계
자식으로 두고 pack()/pack_forget()만으로 전환합니다 - 그래서 어떤 Tk 버전에서도 안전하게
동작합니다.
"""
import tkinter as tk

from core.theme import BG, FG, BG3, ACCENT, ACCENT_HOVER


class WrappingNotebook(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)

        # 탭 버튼들을 담는 영역 - 필요한 만큼 줄(행)이 늘어나며, 항상 맨 위에 고정됩니다.
        self._tabbar = tk.Frame(self, bg=BG)
        self._tabbar.pack(side="top", fill="x")
        self._row_frames = []

        # 탭 버튼 폭을 실제로 그리지 않고 측정만 하기 위한 숨김 위젯 (never packed).
        self._measurer = tk.Button(self, padx=12, pady=6, bd=0)

        self._pages = []           # [{"frame":.., "text":.., "button":..}, ...]
        self._current_frame = None
        self._last_width = None

        self.bind("<Configure>", self._on_configure)

    # ------------------------------------------------------------------
    # ttk.Notebook과 호환되는 최소 인터페이스 (add만 있으면 기존 tabs/*.py가 그대로 동작함)
    # ------------------------------------------------------------------
    def add(self, frame, text=""):
        """frame을 새 탭 페이지로 등록합니다. frame은 이 위젯(self)을 부모로 생성돼 있어야 합니다."""
        page = {"frame": frame, "text": text, "button": None}
        self._pages.append(page)

        if self._current_frame is None:
            self._current_frame = frame  # 첫 탭은 자동으로 선택된 상태로 시작

        self._relayout()
        return frame

    def select(self, frame):
        """지정한 페이지를 화면에 표시하고, 나머지는 숨깁니다."""
        for page in self._pages:
            page["frame"].pack_forget()
        frame.pack(side="top", fill="both", expand=True)
        self._current_frame = frame
        self._refresh_button_styles()

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------
    def _style_button(self, button, selected):
        if selected:
            button.configure(bg=BG3, fg="#ffffff")
        else:
            button.configure(bg=ACCENT, fg=FG)

    def _refresh_button_styles(self):
        for page in self._pages:
            if page["button"] is not None:
                self._style_button(page["button"], page["frame"] is self._current_frame)

    def _measure_width(self, text):
        self._measurer.configure(text=text)
        self._measurer.update_idletasks()
        return self._measurer.winfo_reqwidth()

    def _on_configure(self, event):
        # 폭이 실제로 바뀌었을 때만 다시 배치 (높이 변화 등 불필요한 재계산 방지)
        width = self.winfo_width()
        if width == self._last_width:
            return
        self._last_width = width
        self._relayout()

    def _relayout(self):
        """현재 창 폭 기준으로 탭 버튼들을 몇 줄에 나눠 배치할지 다시 계산합니다.
        탭 개수/폭이 늘어나면 필요한 만큼(2줄, 3줄, ...) 자연스럽게 줄이 늘어납니다."""
        available_width = self.winfo_width()
        if available_width <= 1:
            # 위젯이 아직 화면에 배치되기 전이라 실제 폭을 알 수 없는 상태입니다.
            # 여기서 강제로 재시도(after_idle)하지 않아도, 실제로 배치가 끝나면
            # <Configure> 이벤트가 자연히 발생해 _on_configure()가 다시 호출해줍니다.
            return

        gap = 4
        rows = [[]]
        used_width = 0
        for page in self._pages:
            w = self._measure_width(page["text"]) + gap
            if used_width > 0 and used_width + w > available_width:
                rows.append([])
                used_width = 0
            rows[-1].append(page)
            used_width += w

        for row in self._row_frames:
            row.destroy()
        self._row_frames = []

        for row_pages in rows:
            row_frame = tk.Frame(self._tabbar, bg=BG)
            row_frame.pack(side="top", fill="x")
            self._row_frames.append(row_frame)
            for page in row_pages:
                btn = tk.Button(
                    row_frame, text=page["text"], relief="flat", bd=0,
                    bg=ACCENT, fg=FG, activebackground=ACCENT_HOVER, activeforeground=FG,
                    padx=12, pady=6, highlightthickness=0, cursor="hand2",
                    command=lambda f=page["frame"]: self.select(f),
                )
                btn.pack(side="left", padx=(0, gap), pady=(0, 2))
                page["button"] = btn

        # 탭 페이지 자체는 줄 개수와 무관하게 그대로 유지 (선택된 것만 화면에 보임)
        if self._current_frame is not None:
            self._current_frame.pack(side="top", fill="both", expand=True)
        self._refresh_button_styles()
