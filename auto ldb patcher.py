import os
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, messagebox

# 파일 고정 경로 정의
LCF2XML_BIN = "lcf2xml.exe"
LDB_FILE = "RPG_RT.ldb"
EDB_FILE = "RPG_RT.edb"
CONFIG_FILE = os.path.join("data", "json", "easyrpg_config.json")

# 안전장치: data/json 폴더가 없으면 자동으로 생성
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

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


class PureEdbEasyRpgPatcher:
    def __init__(self, root):
        self.root = root
        self.root.title("EasyRPG DB Editor (Dynamic External Plugin Version)")
        self.root.geometry("1050x760")

        self.edb_master_items = {}
        self.edb_master_skills = {}
        self.current_config = {"system_limits": {}, "items": [], "skills": []}

        self.apply_dark_theme()
        self.decompile_and_parse_edb_directly()
        self.load_config_json()
        self.create_widgets()
        self.refresh_edb_overlay()

    def apply_dark_theme(self):
        self.root.configure(bg=BG)
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
        style.configure("TNotebook", background=BG, bordercolor=BORDER)
        style.configure("TNotebook.Tab", background=ACCENT, foreground=FG, padding=(12, 6))
        style.map("TNotebook.Tab", background=[("selected", BG3)], foreground=[("selected", "#ffffff")])
        style.configure("Treeview", background=BG2, fieldbackground=BG2, foreground=FG,
                         bordercolor=BORDER, rowheight=24)
        style.configure("Treeview.Heading", background=ACCENT, foreground=FG, relief="flat")
        style.map("Treeview.Heading", background=[("active", ACCENT_HOVER)])
        style.map("Treeview", background=[("selected", SELECT_BG)], foreground=[("selected", "#ffffff")])

    def make_listbox(self, parent, height=6):
        return tk.Listbox(parent, height=height, bg=BG2, fg=FG,
                           selectbackground=SELECT_BG, selectforeground="#ffffff",
                           highlightthickness=1, highlightbackground=BORDER,
                           relief="flat", activestyle="none")

    def decompile_and_parse_edb_directly(self):
        if not os.path.exists(LDB_FILE): return
        print("[동기화] 최신 RPG_RT.edb 역변환 확보 중...")
        try:
            subprocess.run([LCF2XML_BIN, LDB_FILE], check=True, shell=True)
        except Exception as e:
            print(f"lcf2xml 구동 실패: {e}"); return
        if not os.path.exists(EDB_FILE): return

        print("[파싱] edb(XML) 내부에서 실시간으로 정보 색출 중...")
        try:
            with open(EDB_FILE, "r", encoding="utf-8") as f:
                xml_text = f.read()
            self.edb_master_items.clear()
            self.edb_master_skills.clear()

            item_pattern = re.compile(r'<Item\s+id="(\d+)">.*?<name>(.*?)</name>', re.DOTALL | re.IGNORECASE)
            for match in item_pattern.finditer(xml_text):
                iid, name = match.group(1), match.group(2)
                self.edb_master_items[int(iid)] = name if name else "이름 없음"

            skill_pattern = re.compile(r'<Skill\s+id="(\d+)">.*?<name>(.*?)</name>', re.DOTALL | re.IGNORECASE)
            for match in skill_pattern.finditer(xml_text):
                sid, name = match.group(1), match.group(2)
                self.edb_master_skills[int(sid)] = name if name else "이름 없음"

            print(f"[동기화 완료] 아이템: {len(self.edb_master_items)}개, 스킬: {len(self.edb_master_skills)}개 매칭 성공.")
        except Exception as e:
            print(f"edb 실시간 파싱 에러: {e}")

    def load_config_json(self):
        if not os.path.exists(CONFIG_FILE):
            messagebox.showerror("실행 실패", f"필수 설정 파일인 '{CONFIG_FILE}'을 찾을 수 없습니다.\\n스크립트와 같은 폴더에 함께 배치해 주세요.")
            self.root.destroy()
            return

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                self.current_config = json.load(f)
            except Exception as e:
                messagebox.showerror("JSON 에러", f"'{CONFIG_FILE}' 해석 오류: {e}")
                self.root.destroy()
                return

        if "system_limits" not in self.current_config: self.current_config["system_limits"] = {}
        if "items" not in self.current_config: self.current_config["items"] = []
        if "skills" not in self.current_config: self.current_config["skills"] = []

        if "easyrpg_max_item_count" not in self.current_config["system_limits"]:
            self.current_config["system_limits"]["easyrpg_max_item_count"] = {"value": 99, "name": "기본 아이템 한도", "max": 250}
        elif isinstance(self.current_config["system_limits"]["easyrpg_max_item_count"], dict):
            self.current_config["system_limits"]["easyrpg_max_item_count"]["value"] = 99

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.current_config, f, ensure_ascii=False, indent=2)

    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")
        ttk.Button(top_frame, text="📥 edb로드", command=self.refresh_from_edb).pack(side="left", padx=5)
        ttk.Button(top_frame, text="💾 저장(ldb전환)", command=self.apply_final_patch).pack(side="right", padx=5)

        self.body_container = ttk.Frame(self.root)
        self.body_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.notebook = ttk.Notebook(self.body_container)
        self.notebook.place(relx=0, rely=0, relwidth=1, relheight=1)

        item_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(item_frame, text="📦 아이템 최대 소지량 조절")
        self.item_tree = ttk.Treeview(item_frame, columns=("ID", "이름", "최대수량"), show="headings", height=18)
        for col, txt in [("ID", "ID"), ("이름", "아이템 이름"), ("최대수량", "최대 수량")]: self.item_tree.heading(col, text=txt)
        self.item_tree.pack(fill="both", expand=True, side="left")

        self.item_tree.column("ID", width=60, anchor="center")
        self.item_tree.column("이름", width=350, anchor="w")
        self.item_tree.column("최대수량", width=120, anchor="center")
        self.item_tree.bind("<<TreeviewSelect>>", self.on_item_select)

        item_btn_frame = ttk.Frame(item_frame, padding=10)
        item_btn_frame.pack(fill="y", side="right")

        ttk.Label(item_btn_frame, text="이름 검색:").pack(anchor="w", pady=(0, 2))
        self.item_search_entry = ttk.Entry(item_btn_frame, width=25)
        self.item_search_entry.pack(anchor="w", pady=(0, 2))
        self.item_search_entry.bind("<KeyRelease>", self.on_item_search)
        self.item_search_listbox = self.make_listbox(item_btn_frame, height=5)
        self.item_search_listbox.pack(anchor="w", fill="x", pady=(0, 10))
        self.item_search_listbox.bind("<<ListboxSelect>>", self.on_item_search_select)

        ttk.Label(item_btn_frame, text="아이템 ID:").pack(anchor="w", pady=(0, 2))
        self.item_id_entry = ttk.Entry(item_btn_frame, width=25); self.item_id_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(item_btn_frame, text="최대 수량:").pack(anchor="w", pady=(0, 2))
        self.item_val_entry = ttk.Entry(item_btn_frame, width=25); self.item_val_entry.pack(anchor="w", pady=(0, 15))
        ttk.Button(item_btn_frame, text="➕ 추가/수정", command=self.add_item_rule).pack(fill="x", pady=3)
        ttk.Button(item_btn_frame, text="❌ 규칙 삭제", command=self.delete_item_rule).pack(fill="x", pady=3)

        ttk.Label(item_btn_frame, text="일괄 설정 (등록된 항목만)").pack(anchor="w", pady=(20, 4))
        ttk.Button(item_btn_frame, text="🗑️ 전체삭제", command=self.batch_clear_items).pack(fill="x", pady=2)
        ttk.Button(item_btn_frame, text="↩️ 기본값 (99)", command=lambda: self.batch_set_items(99)).pack(fill="x", pady=2)
        ttk.Button(item_btn_frame, text="⬆️ 최대값 (255)", command=lambda: self.batch_set_items(255)).pack(fill="x", pady=2)

        skill_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(skill_frame, text="⚡ 스킬 크리티컬 & 기본 데미지 위력 조절")
        self.skill_tree = ttk.Treeview(skill_frame, columns=("ID", "이름", "크리", "위력"), show="headings", height=18)
        for col, txt in [("ID", "ID"), ("이름", "스킬 이름"), ("크리", "크리티컬 (%)"), ("위력", "기본 위력")]: self.skill_tree.heading(col, text=txt)
        self.skill_tree.pack(fill="both", expand=True, side="left")

        self.skill_tree.column("ID", width=60, anchor="center")
        self.skill_tree.column("이름", width=350, anchor="w")
        self.skill_tree.column("크리", width=110, anchor="center")
        self.skill_tree.column("위력", width=110, anchor="center")
        self.skill_tree.bind("<<TreeviewSelect>>", self.on_skill_select)

        skill_btn_frame = ttk.Frame(skill_frame, padding=10)
        skill_btn_frame.pack(fill="y", side="right")

        ttk.Label(skill_btn_frame, text="이름 검색:").pack(anchor="w", pady=(0, 2))
        self.skill_search_entry = ttk.Entry(skill_btn_frame, width=25)
        self.skill_search_entry.pack(anchor="w", pady=(0, 2))
        self.skill_search_entry.bind("<KeyRelease>", self.on_skill_search)
        self.skill_search_listbox = self.make_listbox(skill_btn_frame, height=5)
        self.skill_search_listbox.pack(anchor="w", fill="x", pady=(0, 10))
        self.skill_search_listbox.bind("<<ListboxSelect>>", self.on_skill_search_select)

        ttk.Label(skill_btn_frame, text="스킬 ID:").pack(anchor="w", pady=(0, 2))
        self.skill_id_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_id_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="크리 확률:").pack(anchor="w", pady=(0, 2))
        self.skill_val_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_val_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="스킬 위력:").pack(anchor="w", pady=(0, 2))
        self.skill_dmg_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_dmg_entry.pack(anchor="w", pady=(0, 15))
        ttk.Button(skill_btn_frame, text="➕ 추가/수정", command=self.add_skill_rule).pack(fill="x", pady=3)
        ttk.Button(skill_btn_frame, text="❌ 규칙 삭제", command=self.delete_skill_rule).pack(fill="x", pady=3)

        ttk.Label(skill_btn_frame, text="일괄 설정 (등록된 항목만)").pack(anchor="w", pady=(20, 4))
        ttk.Button(skill_btn_frame, text="🗑️ 전체삭제", command=self.batch_clear_skills).pack(fill="x", pady=2)
        ttk.Button(skill_btn_frame, text="↩️ 크리티컬 초기화 (0)", command=self.batch_reset_skill_crit).pack(fill="x", pady=2)

        sys_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(sys_frame, text="⚙️ 시스템 상한 제한 조절")
        self.sys_tree = ttk.Treeview(sys_frame, columns=("필드명", "옵션명", "설정된수치"), show="headings", height=18)
        for col, txt in [("필드명", "시스템 태그명"), ("옵션명", "한글 기능명"), ("설정된수치", "현재 제한 수치")]: self.sys_tree.heading(col, text=txt)
        self.sys_tree.pack(fill="both", expand=True, side="left")

        self.sys_tree.column("필드명", width=240, anchor="w")
        self.sys_tree.column("옵션명", width=220, anchor="w")
        self.sys_tree.column("설정된수치", width=150, anchor="center")

        sys_btn_frame = ttk.Frame(sys_frame, padding=10)
        sys_btn_frame.pack(fill="y", side="right")
        ttk.Label(sys_btn_frame, text="변경할 수치 입력:").pack(anchor="w", pady=(0, 2))
        self.sys_val_entry = ttk.Entry(sys_btn_frame, width=25); self.sys_val_entry.pack(anchor="w", pady=(0, 15))
        ttk.Button(sys_btn_frame, text="✏️ 선택 항목 수치 변경", command=self.modify_sys_limit).pack(fill="x", pady=3)
        ttk.Button(sys_btn_frame, text="🔄 모든 전역수치 초기화", command=self.reset_sys_limits).pack(fill="x", pady=20)

        self.sys_tree.bind("<<TreeviewSelect>>", self.on_sys_select)

        self.overlay = tk.Frame(self.body_container, bg=BG)
        overlay_inner = tk.Frame(self.overlay, bg=BG)
        overlay_inner.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(overlay_inner, text="⚠", font=("Segoe UI", 40), bg=BG, fg="#e0b400").pack(pady=(0, 10))
        tk.Label(overlay_inner, text="RPG_RT.edb 파일을 찾을 수 없습니다.",
                 font=("Segoe UI", 13, "bold"), bg=BG, fg=FG).pack()
        tk.Label(overlay_inner, text="edb로드 버튼을 눌러주세요.",
                 font=("Segoe UI", 11), bg=BG, fg=FG_DIM).pack(pady=(2, 16))
        ttk.Button(overlay_inner, text="📥 edb로드", command=self.refresh_from_edb).pack()

        self.update_ui_tables()

    def refresh_edb_overlay(self):
        if not hasattr(self, "overlay"):
            return
        if os.path.exists(EDB_FILE):
            self.overlay.place_forget()
        else:
            self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.overlay.lift()

    def update_ui_tables(self):
        for item in self.item_tree.get_children(): self.item_tree.delete(item)
        for it in self.current_config.get("items", []):
            iid = it["id"]
            name = self.edb_master_items.get(iid) or "⚠️ 알만툴 DB에 없음"
            display_count = it["easyrpg_max_count"] if it["easyrpg_max_count"] != -1 else "순정 제한 유지"
            self.item_tree.insert("", "end", values=(iid, name, display_count))

        for skill in self.skill_tree.get_children(): self.skill_tree.delete(skill)
        for sk in self.current_config.get("skills", []):
            sid = sk["id"]
            name = self.edb_master_skills.get(sid) or "⚠️ 알만툴 DB에 없음"
            crit = "순정 유지" if sk.get("easyrpg_critical_hit_chance") == "keep" else sk.get("easyrpg_critical_hit_chance")
            dmg = "순정 유지" if sk.get("rating") == "keep" else sk.get("rating")
            self.skill_tree.insert("", "end", values=(sid, name, crit, dmg))

        for sys_item in self.sys_tree.get_children(): self.sys_tree.delete(sys_item)
        limits = self.current_config.get("system_limits", {})
        for key, info in limits.items():
            if key == "easyrpg_max_item_count": continue
            if isinstance(info, dict):
                val = info.get("value", -1)
                name = info.get("name", "미지정 옵션")
                display_val = "순정 한계 (-1)" if val == -1 else f"{val:,}"
                self.sys_tree.insert("", "end", values=(key, name, display_val))

    def on_item_select(self, event):
        selected = self.item_tree.selection()
        if not selected: return
        vals = self.item_tree.item(selected)['values']
        if not vals: return
        iid = int(vals[0])
        it = next((i for i in self.current_config["items"] if i["id"] == iid), None)
        if it:
            self.item_id_entry.delete(0, tk.END); self.item_id_entry.insert(0, str(it["id"]))
            self.item_val_entry.delete(0, tk.END)
            if it["easyrpg_max_count"] != -1:
                self.item_val_entry.insert(0, str(it["easyrpg_max_count"]))

    def on_skill_select(self, event):
        selected = self.skill_tree.selection()
        if not selected: return
        vals = self.skill_tree.item(selected)['values']
        if not vals: return
        sid = int(vals[0])
        sk = next((s for s in self.current_config["skills"] if s["id"] == sid), None)
        if sk:
            self.skill_id_entry.delete(0, tk.END); self.skill_id_entry.insert(0, str(sk["id"]))
            self.skill_val_entry.delete(0, tk.END)
            if sk.get("easyrpg_critical_hit_chance") != "keep":
                self.skill_val_entry.insert(0, str(sk.get("easyrpg_critical_hit_chance")))
            self.skill_dmg_entry.delete(0, tk.END)
            if sk.get("rating") != "keep":
                self.skill_dmg_entry.insert(0, str(sk.get("rating")))

    def on_sys_select(self, event):
        selected = self.sys_tree.selection()
        if not selected: return
        vals = self.sys_tree.item(selected)['values']
        if vals and len(vals) >= 3:
            raw_val = str(vals[2]).replace("순정 한계 (-1)", "-1").replace(",", "")
            self.sys_val_entry.delete(0, tk.END)
            self.sys_val_entry.insert(0, raw_val)

    def on_item_search(self, event):
        query = self.item_search_entry.get().strip()
        self.item_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(iid, name) for iid, name in sorted(self.edb_master_items.items()) if query in name]
        for iid, name in matches[:20]:
            self.item_search_listbox.insert(tk.END, f"{iid} - {name}")

    def on_item_search_select(self, event):
        sel = self.item_search_listbox.curselection()
        if not sel: return
        text = self.item_search_listbox.get(sel[0])
        iid = text.split(" - ", 1)[0]
        self.item_id_entry.delete(0, tk.END); self.item_id_entry.insert(0, iid)
        self.item_search_entry.delete(0, tk.END)
        self.item_search_listbox.delete(0, tk.END)

    def on_skill_search(self, event):
        query = self.skill_search_entry.get().strip()
        self.skill_search_listbox.delete(0, tk.END)
        if not query: return
        matches = [(sid, name) for sid, name in sorted(self.edb_master_skills.items()) if query in name]
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

    def modify_sys_limit(self):
        selected = self.sys_tree.selection()
        if not selected:
            messagebox.showwarning("경고", "수정할 시스템 항목을 표에서 먼저 클릭해 주세요.")
            return
        vals = self.sys_tree.item(selected)['values']
        key = str(vals[0])
        info = self.current_config["system_limits"][key]
        try:
            val_input = self.sys_val_entry.get().strip()
            if not val_input: return
            val = int(val_input)
            max_limit = info.get("max", 99999999)
            if val > max_limit:
                val = max_limit
                messagebox.showwarning("상한 제한 가드", f"오버플로우 방지를 위해 [{info['name']}]의 최대 수량은 {max_limit:,}으로 자동 제한됩니다.")
            if val < -1: val = -1
            self.current_config["system_limits"][key]["value"] = val
            self.save_config()
            self.update_ui_tables()
            messagebox.showinfo("성공", f"[{info['name']}]의 상한치가 {val:,}으로 저장되었습니다.")
        except ValueError: messagebox.showerror("에러", "수치는 오직 숫자로만 입력해 주세요.")

    def reset_sys_limits(self):
        if not messagebox.askyesno("전체 초기화", "모든 전역 수치를 기본값(-1 / 세이브 15)으로 되돌리시겠습니까?"): return
        for key, info in self.current_config["system_limits"].items():
            if key == "easyrpg_max_savefiles": self.current_config["system_limits"][key]["value"] = 15
            elif key == "easyrpg_max_item_count": continue
            else: self.current_config["system_limits"][key]["value"] = -1
        self.save_config()
        self.update_ui_tables()
        messagebox.showinfo("초기화 완료", "모든 시스템 상한 제한이 순정 기본값 상태로 복구되었습니다.")

    def refresh_from_edb(self):
        self.decompile_and_parse_edb_directly()
        self.update_ui_tables()
        self.refresh_edb_overlay()
        if os.path.exists(EDB_FILE):
            messagebox.showinfo("완료", "순정 edb에서 개체 이름들을 실시간 동기화했습니다!")
        else:
            messagebox.showerror("실패", f"'{LDB_FILE}' 파일을 찾지 못했거나 edb 변환에 실패했습니다.")

    def add_item_rule(self):
        try:
            iid = int(self.item_id_entry.get().strip())
            val_input = self.item_val_entry.get().strip()
            val = int(val_input) if val_input else -1
            if val > 250:
                val = 250
                messagebox.showwarning("수량 제한", "엔진 세이브 오동작 방지를 위해 개별 아이템 한도는 250개로 자동 한정됩니다.")
            if iid not in self.edb_master_items:
                if not messagebox.askyesno("경고", "순정 아이템에 없습니다. 진행할까요?"): return
            self.current_config["items"] = [i for i in self.current_config["items"] if i["id"] != iid]
            self.current_config["items"].append({"id": iid, "easyrpg_max_count": val})
            self.save_config()
            self.update_ui_tables()
        except ValueError: messagebox.showerror("에러", "ID와 수치는 정수 숫자로 입력해 주세요.")

    def delete_item_rule(self):
        sel = self.item_tree.selection()
        if not sel: return
        item_vals = self.item_tree.item(sel)['values']
        iid = int(item_vals[0])
        self.current_config["items"] = [i for i in self.current_config["items"] if i["id"] != iid]
        self.save_config()
        self.update_ui_tables()

    def batch_clear_items(self):
        if not self.current_config["items"]:
            messagebox.showwarning("경고", "리스트에 등록된 아이템이 없습니다.")
            return
        if not messagebox.askyesno("일괄 삭제", "등록된 모든 아이템 규칙을 삭제하시겠습니까?"): return
        self.current_config["items"] = []
        self.save_config()
        self.update_ui_tables()

    def batch_set_items(self, value):
        if not self.current_config["items"]:
            messagebox.showwarning("경고", "리스트에 등록된 아이템이 없습니다.")
            return
        for it in self.current_config["items"]:
            it["easyrpg_max_count"] = value
        self.save_config()
        self.update_ui_tables()
        messagebox.showinfo("완료", f"등록된 아이템 {len(self.current_config['items'])}개의 최대 수량을 {value}(으)로 일괄 설정했습니다.")

    def add_skill_rule(self):
        try:
            sid = int(self.skill_id_entry.get().strip())
            c_input = self.skill_val_entry.get().strip()
            d_input = self.skill_dmg_entry.get().strip()
            crit_val = int(c_input) if c_input else "keep"
            dmg_val = int(d_input) if d_input else "keep"
            if sid not in self.edb_master_skills:
                if not messagebox.askyesno("경고", "순정 스킬에 없습니다. 진행할까요?"): return
            self.current_config["skills"] = [s for s in self.current_config["skills"] if s["id"] != sid]
            self.current_config["skills"].append({"id": sid, "easyrpg_critical_hit_chance": crit_val, "rating": dmg_val})
            self.save_config()
            self.update_ui_tables()
        except ValueError: messagebox.showerror("에러", "ID와 수치들은 숫자로 입력해 주세요.")

    def delete_skill_rule(self):
        sel = self.skill_tree.selection()
        if not sel: return
        skill_vals = self.skill_tree.item(sel)['values']
        sid = int(skill_vals[0])
        self.current_config["skills"] = [s for s in self.current_config["skills"] if s["id"] != sid]
        self.save_config()
        self.update_ui_tables()

    def batch_clear_skills(self):
        if not self.current_config["skills"]:
            messagebox.showwarning("경고", "리스트에 등록된 스킬이 없습니다.")
            return
        if not messagebox.askyesno("일괄 삭제", "등록된 모든 스킬 규칙을 삭제하시겠습니까?"): return
        self.current_config["skills"] = []
        self.save_config()
        self.update_ui_tables()

    def batch_reset_skill_crit(self):
        if not self.current_config["skills"]:
            messagebox.showwarning("경고", "리스트에 등록된 스킬이 없습니다.")
            return
        for sk in self.current_config["skills"]:
            sk["easyrpg_critical_hit_chance"] = 0
        self.save_config()
        self.update_ui_tables()
        messagebox.showinfo("완료", f"등록된 스킬 {len(self.current_config['skills'])}개의 크리티컬 확률을 0으로 초기화했습니다.")

    def apply_final_patch(self):
        if not os.path.exists(EDB_FILE):
            messagebox.showerror("실패", "RPG_RT.edb 파일이 없습니다. 먼저 'edb로드' 버튼을 눌러주세요.")
            return
        tree = ET.parse(EDB_FILE); root = tree.getroot()
        _container = root.find(".//system")
        system_container = _container if _container is not None else root.find(".//System")
        if system_container is not None:
            _node = system_container.find("System")
            actual_system_node = _node if _node is not None else system_container.find("system")
            if actual_system_node is not None:
                for key, info in self.current_config.get("system_limits", {}).items():
                    val = info.get("value") if isinstance(info, dict) else info
                    tag = actual_system_node.find(key)
                    if tag is not None: tag.text = str(val)
                    else: ET.SubElement(actual_system_node, key).text = str(val)
                print(" -> 대문자 <System> 내부에 한계 해제 완료.")

        for el in root.iter():
            t_low = el.tag.lower()
            if t_low == "items" or t_low == "item_container":
                for it in self.current_config.get("items", []):
                    for item_node in el.findall("Item") + el.findall("item"):
                        nid = item_node.get("id") or (item_node.find("id").text if item_node.find("id") is not None else None)
                        if nid and int(nid) == it["id"]:
                            tag = item_node.find("easyrpg_max_count")
                            if tag is not None: tag.text = str(it["easyrpg_max_count"])
                            else: ET.SubElement(item_node, "easyrpg_max_count").text = str(it["easyrpg_max_count"])
            if t_low == "skills" or t_low == "skills_container" or t_low == "skill_container":
                for sk in self.current_config.get("skills", []):
                    for skill_node in el.findall("Skill") + el.findall("skill"):
                        nid = skill_node.get("id") or (skill_node.find("id").text if skill_node.find("id") is not None else None)
                        if nid and int(nid) == sk["id"]:
                            if sk.get("easyrpg_critical_hit_chance") != "keep":
                                crit_tag = skill_node.find("easyrpg_critical_hit_chance")
                                if crit_tag is not None: crit_tag.text = str(sk["easyrpg_critical_hit_chance"])
                                else: ET.SubElement(skill_node, "easyrpg_critical_hit_chance").text = str(sk["easyrpg_critical_hit_chance"])
                            if sk.get("rating") != "keep":
                                r_tag = skill_node.find("rating")
                                if r_tag is not None: r_tag.text = str(sk["rating"])
                                else: ET.SubElement(skill_node, "rating").text = str(sk["rating"])
        tree.write(EDB_FILE, encoding="utf-8", xml_declaration=True)

        try:
            subprocess.run([LCF2XML_BIN, EDB_FILE], check=True, shell=True)
        except Exception as e:
            messagebox.showerror("실패", f"lcf2xml 컴파일(edb → ldb) 실패: {e}")
            return

        if os.path.exists(EDB_FILE):
            try:
                os.remove(EDB_FILE)
            except Exception as e:
                print(f"edb 삭제 실패: {e}")

        self.refresh_edb_overlay()
        messagebox.showinfo("대성공", "전역 한계 해제 및 스킬/아이템 개조 패치가 완료되었습니다!\nRPG_RT.edb는 정리되었습니다. 다시 수정하려면 'edb로드'를 눌러주세요.")


if __name__ == "__main__":
    root = tk.Tk()
    app = PureEdbEasyRpgPatcher(root)
    root.mainloop()
