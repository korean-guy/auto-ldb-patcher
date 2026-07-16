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
CONFIG_FILE = "easyrpg_config.json"

class PureEdbEasyRpgPatcher:
    def __init__(self, root):
        self.root = root
        self.root.title("EasyRPG DB Editor (Dynamic External Plugin Version)")
        self.root.geometry("950x700")
        
        # 실시간 데이터베이스 마스터룸 메모리 사전
        self.edb_master_items = {}
        self.edb_master_skills = {}
        self.current_config = {"system_limits": {}, "items": [], "skills": []}
        
        self.decompile_and_parse_edb_directly()
        self.load_config_json()
        self.create_widgets()

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
            self.current_config["system_limits"]["easyrpg_max_item_count"] = { "value": 99, "name": "기본 아이템 한도", "max": 250 }
        elif isinstance(self.current_config["system_limits"]["easyrpg_max_item_count"], dict):
            self.current_config["system_limits"]["easyrpg_max_item_count"]["value"] = 99
    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")
        ttk.Button(top_frame, text="🔄 알만툴 에디터 저장내용 실시간 동기화 (edb 다이렉트)", command=self.refresh_from_edb).pack(side="left", padx=5)
        ttk.Button(top_frame, text="💾 최종 패치 적용 (LDB 컴파일 빌드)", command=self.apply_final_patch).pack(side="right", padx=5)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. 아이템 탭 빌드
        item_frame = ttk.Frame(notebook, padding=10)
        notebook.add(item_frame, text="📦 아이템 최대 소지량 조절")
        self.item_tree = ttk.Treeview(item_frame, columns=("ID", "이름", "최대수량"), show="headings", height=18)
        for col, txt in [("ID", "ID"), ("이름", "아이템 이름"), ("최대수량", "최대 수량")]: self.item_tree.heading(col, text=txt)
        self.item_tree.pack(fill="both", expand=True, side="left")
        
        self.item_tree.column("ID", width=60, anchor="center")
        self.item_tree.column("이름", width=350, anchor="w")
        self.item_tree.column("최대수량", width=120, anchor="center")
        
        item_btn_frame = ttk.Frame(item_frame, padding=10)
        item_btn_frame.pack(fill="y", side="right")
        ttk.Label(item_btn_frame, text="아이템 ID:").pack(anchor="w", pady=(0, 2))
        self.item_id_entry = ttk.Entry(item_btn_frame, width=25); self.item_id_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(item_btn_frame, text="최대 수량:").pack(anchor="w", pady=(0, 2))
        self.item_val_entry = ttk.Entry(item_btn_frame, width=25); self.item_val_entry.pack(anchor="w", pady=(0, 15))
        ttk.Button(item_btn_frame, text="➕ 추가/수정", command=self.add_item_rule).pack(fill="x", pady=3)
        ttk.Button(item_btn_frame, text="❌ 규칙 삭제", command=self.delete_item_rule).pack(fill="x", pady=3)

        # 2. 스킬 탭 빌드
        skill_frame = ttk.Frame(notebook, padding=10)
        notebook.add(skill_frame, text="⚡ 스킬 크리티컬 & 기본 데미지 위력 조절")
        self.skill_tree = ttk.Treeview(skill_frame, columns=("ID", "이름", "크리", "위력"), show="headings", height=18)
        for col, txt in [("ID", "ID"), ("이름", "스킬 이름"), ("크리", "크리티컬 (%)"), ("위력", "기본 위력")]: self.skill_tree.heading(col, text=txt)
        self.skill_tree.pack(fill="both", expand=True, side="left")
        
        self.skill_tree.column("ID", width=60, anchor="center")
        self.skill_tree.column("이름", width=350, anchor="w")
        self.skill_tree.column("크리", width=110, anchor="center")
        self.skill_tree.column("위력", width=110, anchor="center")
        
        skill_btn_frame = ttk.Frame(skill_frame, padding=10)
        skill_btn_frame.pack(fill="y", side="right")
        ttk.Label(skill_btn_frame, text="스킬 ID:").pack(anchor="w", pady=(0, 2))
        self.skill_id_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_id_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="크리 확률:").pack(anchor="w", pady=(0, 2))
        self.skill_val_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_val_entry.pack(anchor="w", pady=(0, 10))
        ttk.Label(skill_btn_frame, text="스킬 위력:").pack(anchor="w", pady=(0, 2))
        self.skill_dmg_entry = ttk.Entry(skill_btn_frame, width=25); self.skill_dmg_entry.pack(anchor="w", pady=(0, 15))
        ttk.Button(skill_btn_frame, text="➕ 추가/수정", command=self.add_skill_rule).pack(fill="x", pady=3)
        ttk.Button(skill_btn_frame, text="❌ 규칙 삭제", command=self.delete_skill_rule).pack(fill="x", pady=3)

        # 3. 시스템 제한 탭 빌드
        sys_frame = ttk.Frame(notebook, padding=10)
        notebook.add(sys_frame, text="⚙️ 시스템 상한 제한 조절")
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
        self.update_ui_tables()
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

    def on_sys_select(self, event):
        selected = self.sys_tree.selection()
        if not selected: return
        vals = self.sys_tree.item(selected)['values']
        if vals and len(vals) >= 3:
            raw_val = str(vals[2]).replace("순정 한계 (-1)", "-1").replace(",", "")
            self.sys_val_entry.delete(0, tk.END)
            self.sys_val_entry.insert(0, raw_val)

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
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.current_config, f, ensure_ascii=False, indent=2)
            self.update_ui_tables()
            messagebox.showinfo("성공", f"[{info['name']}]의 상한치가 {val:,}으로 저장되었습니다.")
        except ValueError: messagebox.showerror("에러", "수치는 오직 숫자로만 입력해 주세요.")

    def reset_sys_limits(self):
        if not messagebox.askyesno("전체 초기화", "모든 전역 수치를 기본값(-1 / 세이브 15)으로 되돌리시겠습니까?"): return
        for key, info in self.current_config["system_limits"].items():
            if key == "easyrpg_max_savefiles": self.current_config["system_limits"][key]["value"] = 15
            elif key == "easyrpg_max_item_count": continue
            else: self.current_config["system_limits"][key]["value"] = -1
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.current_config, f, ensure_ascii=False, indent=2)
        self.update_ui_tables()
        messagebox.showinfo("초기화 완료", "모든 시스템 상한 제한이 순정 기본값 상태로 복구되었습니다.")

    def refresh_from_edb(self):
        self.decompile_and_parse_edb_directly(); self.update_ui_tables()
        messagebox.showinfo("완료", "순정 edb에서 개체 이름들을 실시간 동기화했습니다!")

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
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.current_config, f, ensure_ascii=False, indent=2)
            self.update_ui_tables()
        except ValueError: messagebox.showerror("에러", "ID와 수치는 정수 숫자로 입력해 주세요.")

    def delete_item_rule(self):
        sel = self.item_tree.selection()
        if not sel: return
        item_vals = self.item_tree.item(sel)['values']
        iid = int(item_vals[0])
        self.current_config["items"] = [i for i in self.current_config["items"] if i["id"] != iid]
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.current_config, f, ensure_ascii=False, indent=2)
        self.update_ui_tables()

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
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.current_config, f, ensure_ascii=False, indent=2)
            self.update_ui_tables()
        except ValueError: messagebox.showerror("에러", "ID와 수치들은 숫자로 입력해 주세요.")

    def delete_skill_rule(self):
        sel = self.skill_tree.selection()
        if not sel: return
        skill_vals = self.skill_tree.item(sel)['values']
        sid = int(skill_vals[0])
        self.current_config["skills"] = [s for s in self.current_config["skills"] if s["id"] != sid]
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.current_config, f, ensure_ascii=False, indent=2)
        self.update_ui_tables()

    def apply_final_patch(self):
        if not os.path.exists(EDB_FILE): subprocess.run([LCF2XML_BIN, LDB_FILE], check=True, shell=True)
        tree = ET.parse(EDB_FILE); root = tree.getroot()
        system_container = root.find(".//system") or root.find(".//System")
        if system_container is not None:
            actual_system_node = system_container.find("System") or system_container.find("system")
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
        subprocess.run([LCF2XML_BIN, EDB_FILE], check=True, shell=True)
        messagebox.showinfo("대성공", "전역 한계 해제 및 스킬/아이템 개조 패치가 완료되었습니다!")

if __name__ == "__main__":
    root = tk.Tk()
    app = PureEdbEasyRpgPatcher(root)
    root.mainloop()
