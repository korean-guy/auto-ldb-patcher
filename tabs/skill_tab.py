"""
tabs/skill_tab.py
"스킬 세부 옵션 조절" 탭 - 속성 편집기(Property Editor) 스타일.

좌측: 프로젝트에 등록된 스킬 목록(이름검색으로 추가, 선택해서 삭제)
우측: 선택한 스킬의 EasyRPG 옵션들을 그룹별로 보여주는 고정 크기 편집 패널
      (core.property_panel 재사용 - System 탭과 동일한 방식)

새 EasyRPG 스킬 옵션은 core/skill_schema.py의 SKILL_FIELD_DEFS에 항목만
추가하면 이 탭에 자동으로 나타납니다. HP 소모 방식(easyrpg_hp_type)에 따라
easyrpg_hp_cost / easyrpg_hp_percent 중 관련 없는 쪽은 자동으로 비활성화됩니다.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import attach_tree_scrollbar, make_listbox_with_scroll
from core.property_panel import make_fixed_scroll_panel, render_field_row, render_group_header
from core.skill_schema import SKILL_FIELD_DEFS, default_skill_fields, migrate_skill_entry
from core.logger import log

DETAIL_WIDTH = 320
DETAIL_HEIGHT = 560


class SkillTab:
    TITLE = "⚡ 스킬 세부 옵션 조절"

    def __init__(self, app):
        self.app = app
        self._current_skill = None

    @property
    def cfg(self):
        return self.app.cfg

    # ------------------------------------------------------------------
    def on_project_loaded(self):
        """예전 버전 프로젝트 설정(스킬 항목이 최상위 rating/crit 등을 갖던 방식)을
        새 스키마({"id":.., "fields": {...}})로 변환합니다. 새로 추가된 필드가 있으면
        기존 스킬에도 기본값으로 채워 넣습니다."""
        skills = self.cfg.current_config.get("skills", [])
        migrated = [migrate_skill_entry(sk) for sk in skills]
        if migrated != skills:
            self.cfg.current_config["skills"] = migrated
            self.cfg.save_config()

    # ------------------------------------------------------------------
    def build(self, notebook):
        skill_frame = ttk.Frame(notebook, padding=10)
        notebook.add(skill_frame, text=self.TITLE)

        left_frame = ttk.Frame(skill_frame)
        left_frame.pack(fill="both", expand=True, side="left")

        self.skill_tree = ttk.Treeview(left_frame, columns=("ID", "이름", "위력", "크리"),
                                        show="headings", height=18)
        for col, txt in [("ID", "ID"), ("이름", "스킬 이름"), ("위력", "기본 위력"), ("크리", "크리티컬 (%)")]:
            self.skill_tree.heading(col, text=txt)
        self.skill_tree.pack(fill="both", expand=True, side="left")
        attach_tree_scrollbar(self.skill_tree, left_frame)

        self.skill_tree.column("ID", width=50, anchor="center")
        self.skill_tree.column("이름", width=220, anchor="w")
        self.skill_tree.column("위력", width=90, anchor="center")
        self.skill_tree.column("크리", width=90, anchor="center")
        self.skill_tree.bind("<<TreeviewSelect>>", self.on_skill_select)

        skill_btn_frame = ttk.Frame(skill_frame, padding=10)
        skill_btn_frame.pack(fill="y", side="right")

        ttk.Label(skill_btn_frame, text="이름 검색:").pack(anchor="w", pady=(0, 2))
        self.skill_search_entry = ttk.Entry(skill_btn_frame, width=25)
        self.skill_search_entry.pack(anchor="w", pady=(0, 2))
        self.skill_search_entry.bind("<KeyRelease>", self.on_skill_search)
        skill_search_frame, self.skill_search_listbox = make_listbox_with_scroll(skill_btn_frame, height=6)
        skill_search_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.skill_search_listbox.bind("<<ListboxSelect>>", self.on_skill_search_select)

        ttk.Label(skill_btn_frame, text="스킬 ID:").pack(anchor="w", pady=(0, 2))
        self.skill_id_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_id_entry.pack(anchor="w", pady=(0, 10))
        ttk.Button(skill_btn_frame, text="➕ 목록에 추가", command=self.add_skill_rule).pack(fill="x", pady=3)
        ttk.Button(skill_btn_frame, text="❌ 목록에서 삭제", command=self.delete_skill_rule).pack(fill="x", pady=3)

        ttk.Label(skill_btn_frame, text="일괄 설정 (등록된 항목만)").pack(anchor="w", pady=(20, 4))
        ttk.Button(skill_btn_frame, text="🗑️ 전체삭제", command=self.batch_clear_skills).pack(fill="x", pady=2)
        ttk.Button(skill_btn_frame, text="↩️ 크리티컬 초기화 (0)", command=self.batch_reset_skill_crit).pack(fill="x", pady=2)

        ttk.Label(skill_btn_frame, text="세부 옵션 편집").pack(anchor="w", pady=(20, 4))
        self.detail_outer, self.skill_detail_frame = make_fixed_scroll_panel(
            skill_btn_frame, width=DETAIL_WIDTH, height=DETAIL_HEIGHT
        )
        self.detail_outer.pack(anchor="n")
        self._show_placeholder()

    def _show_placeholder(self):
        for w in self.skill_detail_frame.winfo_children():
            w.destroy()
        ttk.Label(self.skill_detail_frame, text="왼쪽 목록에서 스킬을 선택하세요.",
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=8)

    # ------------------------------------------------------------------
    def refresh(self):
        for item in self.skill_tree.get_children(): self.skill_tree.delete(item)
        for sk in self.cfg.current_config.get("skills", []):
            sid = sk["id"]
            name = self.app.edb_master_skills.get(sid) or "⚠️ 알만툴 DB에 없음"
            fields = sk.get("fields", {})
            rating = fields.get("rating", 0)
            crit = fields.get("easyrpg_critical_hit_chance", 0)
            self.skill_tree.insert("", "end", values=(sid, name, rating, crit))

    # ------------------------------------------------------------------
    # 좌측 목록 선택 -> 우측 속성 편집기 렌더링
    # ------------------------------------------------------------------
    def on_skill_select(self, event):
        selected = self.skill_tree.selection()
        if not selected: return
        vals = self.skill_tree.item(selected)['values']
        if not vals: return
        sid = int(vals[0])
        sk = next((s for s in self.cfg.current_config["skills"] if s["id"] == sid), None)
        if sk:
            self.render_skill_detail(sk)

    def render_skill_detail(self, sk):
        for w in self.skill_detail_frame.winfo_children():
            w.destroy()
        self._current_skill = sk
        fields = sk["fields"]
        p = self.skill_detail_frame

        name = self.app.edb_master_skills.get(sk["id"], "이름 없음")
        ttk.Label(p, text=f"스킬 ID {sk['id']} - {name}", font=("Segoe UI", 10, "bold"),
                  wraplength=DETAIL_WIDTH - 30).pack(anchor="w", padx=8, pady=(8, 4))

        last_group = None
        for fd in SKILL_FIELD_DEFS:
            group = fd.get("group", "기타")
            if group != last_group:
                header_holder = ttk.Frame(p)
                header_holder.pack(fill="x", padx=8)
                render_group_header(header_holder, group)
                last_group = group

            row = ttk.Frame(p)
            row.pack(fill="x", padx=8)

            enabled = True
            cond = fd.get("enabled_when")
            if cond:
                enabled = fields.get(cond["field"]) == cond["equals"]

            control, set_enabled = render_field_row(
                row, fd, fields.get(fd["name"], fd["default"]), self._make_on_change(fd["name"])
            )
            set_enabled(enabled)

    def _make_on_change(self, field_name):
        def _on_change(new_val):
            self._current_skill["fields"][field_name] = new_val
            self.cfg.save_config()
            self.app.refresh_all_tabs()
            log.info(f"스킬 {self._current_skill['id']} - {field_name} = {new_val}")
            # 위젯을 그리던 이벤트(FocusOut 등) 처리가 끝난 뒤 안전하게 다시 그림
            # (예: HP 소모 방식이 바뀌면 관련 필드의 활성/비활성 상태를 새로 계산)
            self.skill_detail_frame.after_idle(lambda: self.render_skill_detail(self._current_skill))
        return _on_change

    # ------------------------------------------------------------------
    # 이름 검색 (드롭다운)
    # ------------------------------------------------------------------
    def on_skill_search(self, event):
        query = self.skill_search_entry.get().strip()
        self.skill_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(sid, name) for sid, name in sorted(self.app.edb_master_skills.items()) if query in name]
        for sid, name in matches[:20]:
            self.skill_search_listbox.insert(tk.END, f"{sid} - {name}")

    def on_skill_search_select(self, event):
        sel = self.skill_search_listbox.curselection()
        if not sel: return
        text = self.skill_search_listbox.get(sel[0])
        sid = text.split(" - ", 1)[0]
        self.skill_id_entry.delete(0, tk.END); self.skill_id_entry.insert(0, sid)
        self.skill_search_entry.delete(0, tk.END)
        self.skill_search_listbox.delete(0, tk.END)

    # ------------------------------------------------------------------
    # 스킬 목록 추가/삭제/일괄 설정
    # ------------------------------------------------------------------
    def add_skill_rule(self):
        try:
            sid = int(self.skill_id_entry.get().strip())
        except ValueError:
            messagebox.showerror("에러", "ID는 숫자로 입력해 주세요.")
            return
        if sid not in self.app.edb_master_skills:
            if not messagebox.askyesno("경고", "순정 스킬에 없습니다. 진행할까요?"): return
        existing = next((s for s in self.cfg.current_config["skills"] if s["id"] == sid), None)
        if existing is None:
            self.cfg.current_config["skills"].append({"id": sid, "fields": default_skill_fields()})
            self.cfg.save_config()
            log.info(f"스킬 목록에 추가 (ID {sid})")
        self.app.refresh_all_tabs()

    def delete_skill_rule(self):
        sel = self.skill_tree.selection()
        if not sel: return
        skill_vals = self.skill_tree.item(sel)['values']
        sid = int(skill_vals[0])
        self.cfg.current_config["skills"] = [s for s in self.cfg.current_config["skills"] if s["id"] != sid]
        self.cfg.save_config()
        if self._current_skill and self._current_skill.get("id") == sid:
            self._current_skill = None
            self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info(f"스킬 목록에서 삭제 (ID {sid})")

    def batch_clear_skills(self):
        if not self.cfg.current_config["skills"]:
            messagebox.showwarning("경고", "리스트에 등록된 스킬이 없습니다.")
            return
        if not messagebox.askyesno("일괄 삭제", "등록된 모든 스킬 규칙을 삭제하시겠습니까?"): return
        self.cfg.current_config["skills"] = []
        self.cfg.save_config()
        self._current_skill = None
        self._show_placeholder()
        self.app.refresh_all_tabs()
        log.info("스킬 목록 전체 삭제")

    def batch_reset_skill_crit(self):
        if not self.cfg.current_config["skills"]:
            messagebox.showwarning("경고", "리스트에 등록된 스킬이 없습니다.")
            return
        for sk in self.cfg.current_config["skills"]:
            sk["fields"]["easyrpg_critical_hit_chance"] = 0
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        if self._current_skill:
            self.render_skill_detail(self._current_skill)
        log.info(f"등록된 스킬 {len(self.cfg.current_config['skills'])}개 크리티컬 확률 초기화")
        messagebox.showinfo("완료", f"등록된 스킬 {len(self.cfg.current_config['skills'])}개의 크리티컬 확률을 0으로 초기화했습니다.")
