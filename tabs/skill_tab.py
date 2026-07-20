"""
tabs/skill_tab.py
"스킬 크리티컬 & 기본 데미지 위력 조절" 탭 - 스킬 목록/이름검색/추가삭제/일괄설정.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.theme import attach_tree_scrollbar, make_listbox_with_scroll


class SkillTab:
    TITLE = "⚡ 스킬 크리티컬 & 기본 데미지 위력 조절"

    def __init__(self, app):
        self.app = app

    @property
    def cfg(self):
        return self.app.cfg

    def build(self, notebook):
        skill_frame = ttk.Frame(notebook, padding=10)
        notebook.add(skill_frame, text=self.TITLE)

        self.skill_tree = ttk.Treeview(
            skill_frame, columns=("ID", "이름", "크리", "위력", "공격력비율", "정신력비율"),
            show="headings", height=18
        )
        headings = [("ID", "ID"), ("이름", "스킬 이름"), ("크리", "크리티컬 (%)"), ("위력", "기본 위력"),
                    ("공격력비율", "공격력비율"), ("정신력비율", "정신력비율")]
        for col, txt in headings: self.skill_tree.heading(col, text=txt)
        self.skill_tree.pack(fill="both", expand=True, side="left")
        attach_tree_scrollbar(self.skill_tree, skill_frame)

        self.skill_tree.column("ID", width=50, anchor="center")
        self.skill_tree.column("이름", width=220, anchor="w")
        self.skill_tree.column("크리", width=90, anchor="center")
        self.skill_tree.column("위력", width=90, anchor="center")
        self.skill_tree.column("공격력비율", width=90, anchor="center")
        self.skill_tree.column("정신력비율", width=90, anchor="center")
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
        ttk.Label(skill_btn_frame, text="크리 확률:").pack(anchor="w", pady=(0, 2))
        self.skill_val_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_val_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="스킬 위력:").pack(anchor="w", pady=(0, 2))
        self.skill_dmg_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_dmg_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="공격력 비율 (physical_rate, 1=5%):").pack(anchor="w", pady=(0, 2))
        self.skill_phys_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_phys_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="정신력 비율 (magical_rate, 1=2.5%):").pack(anchor="w", pady=(0, 2))
        self.skill_mag_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_mag_entry.pack(anchor="w", pady=(0, 15))
        ttk.Button(skill_btn_frame, text="➕ 추가/수정", command=self.add_skill_rule).pack(fill="x", pady=3)
        ttk.Button(skill_btn_frame, text="❌ 규칙 삭제", command=self.delete_skill_rule).pack(fill="x", pady=3)

        ttk.Label(skill_btn_frame, text="일괄 설정 (등록된 항목만)").pack(anchor="w", pady=(20, 4))
        ttk.Button(skill_btn_frame, text="🗑️ 전체삭제", command=self.batch_clear_skills).pack(fill="x", pady=2)
        ttk.Button(skill_btn_frame, text="↩️ 크리티컬 초기화 (0)", command=self.batch_reset_skill_crit).pack(fill="x", pady=2)

    # ------------------------------------------------------------------
    def refresh(self):
        for skill in self.skill_tree.get_children(): self.skill_tree.delete(skill)
        for sk in self.cfg.current_config.get("skills", []):
            sid = sk["id"]
            name = self.app.edb_master_skills.get(sid) or "⚠️ 알만툴 DB에 없음"
            crit = "순정 유지" if sk.get("easyrpg_critical_hit_chance") == "keep" else sk.get("easyrpg_critical_hit_chance")
            dmg = "순정 유지" if sk.get("rating") == "keep" else sk.get("rating")
            phys = "순정 유지" if sk.get("physical_rate", "keep") == "keep" else sk.get("physical_rate")
            mag = "순정 유지" if sk.get("magical_rate", "keep") == "keep" else sk.get("magical_rate")
            self.skill_tree.insert("", "end", values=(sid, name, crit, dmg, phys, mag))

    def on_skill_select(self, event):
        selected = self.skill_tree.selection()
        if not selected: return
        vals = self.skill_tree.item(selected)['values']
        if not vals: return
        sid = int(vals[0])
        sk = next((s for s in self.cfg.current_config["skills"] if s["id"] == sid), None)
        if sk:
            self.skill_id_entry.delete(0, tk.END); self.skill_id_entry.insert(0, str(sk["id"]))
            self.skill_val_entry.delete(0, tk.END)
            if sk.get("easyrpg_critical_hit_chance") != "keep":
                self.skill_val_entry.insert(0, str(sk.get("easyrpg_critical_hit_chance")))
            self.skill_dmg_entry.delete(0, tk.END)
            if sk.get("rating") != "keep":
                self.skill_dmg_entry.insert(0, str(sk.get("rating")))
            self.skill_phys_entry.delete(0, tk.END)
            if sk.get("physical_rate", "keep") != "keep":
                self.skill_phys_entry.insert(0, str(sk.get("physical_rate")))
            self.skill_mag_entry.delete(0, tk.END)
            if sk.get("magical_rate", "keep") != "keep":
                self.skill_mag_entry.insert(0, str(sk.get("magical_rate")))

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

    def add_skill_rule(self):
        try:
            sid = int(self.skill_id_entry.get().strip())
            c_input = self.skill_val_entry.get().strip()
            d_input = self.skill_dmg_entry.get().strip()
            p_input = self.skill_phys_entry.get().strip()
            m_input = self.skill_mag_entry.get().strip()
            crit_val = int(c_input) if c_input else "keep"
            dmg_val = int(d_input) if d_input else "keep"
            phys_val = int(p_input) if p_input else "keep"
            mag_val = int(m_input) if m_input else "keep"
            if sid not in self.app.edb_master_skills:
                if not messagebox.askyesno("경고", "순정 스킬에 없습니다. 진행할까요?"): return
            self.cfg.current_config["skills"] = [s for s in self.cfg.current_config["skills"] if s["id"] != sid]
            self.cfg.current_config["skills"].append({
                "id": sid, "easyrpg_critical_hit_chance": crit_val, "rating": dmg_val,
                "physical_rate": phys_val, "magical_rate": mag_val,
            })
            self.cfg.save_config()
            self.app.refresh_all_tabs()
        except ValueError:
            messagebox.showerror("에러", "ID와 수치들은 숫자로 입력해 주세요.")

    def delete_skill_rule(self):
        sel = self.skill_tree.selection()
        if not sel: return
        skill_vals = self.skill_tree.item(sel)['values']
        sid = int(skill_vals[0])
        self.cfg.current_config["skills"] = [s for s in self.cfg.current_config["skills"] if s["id"] != sid]
        self.cfg.save_config()
        self.app.refresh_all_tabs()

    def batch_clear_skills(self):
        if not self.cfg.current_config["skills"]:
            messagebox.showwarning("경고", "리스트에 등록된 스킬이 없습니다.")
            return
        if not messagebox.askyesno("일괄 삭제", "등록된 모든 스킬 규칙을 삭제하시겠습니까?"): return
        self.cfg.current_config["skills"] = []
        self.cfg.save_config()
        self.app.refresh_all_tabs()

    def batch_reset_skill_crit(self):
        if not self.cfg.current_config["skills"]:
            messagebox.showwarning("경고", "리스트에 등록된 스킬이 없습니다.")
            return
        for sk in self.cfg.current_config["skills"]:
            sk["easyrpg_critical_hit_chance"] = 0
        self.cfg.save_config()
        self.app.refresh_all_tabs()
        messagebox.showinfo("완료", f"등록된 스킬 {len(self.cfg.current_config['skills'])}개의 크리티컬 확률을 0으로 초기화했습니다.")
