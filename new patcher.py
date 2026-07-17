import os
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, messagebox


LCF2XML_BIN = "lcf2xml.exe"
LDB_FILE = "RPG_RT.ldb"
EDB_FILE = "RPG_RT.edb"

CONFIG_FILE = os.path.join(
    "data",
    "json",
    "easyrpg_config.json"
)

os.makedirs(
    os.path.dirname(CONFIG_FILE),
    exist_ok=True
)


class PureEdbEasyRpgPatcher:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "EasyRPG DB Editor v1.3"
        )

        self.root.geometry(
            "1000x720"
        )


        self.edb_master_items = {}
        self.edb_master_skills = {}


        self.current_config = {
            "system_limits": {},
            "items": [],
            "skills": []
        }


        self.setup_dark_theme()

        self.load_config_json()

        self.convert_ldb_to_edb()

        self.load_edb_database()

        self.create_widgets()



    # ---------------------------------
    # 다크 테마
    # ---------------------------------

    def setup_dark_theme(self):

        style = ttk.Style()

        style.theme_use("clam")


        style.configure(
            ".",
            background="#202020",
            foreground="white"
        )


        style.configure(
            "TFrame",
            background="#202020"
        )


        style.configure(
            "TLabel",
            background="#202020",
            foreground="white"
        )


        style.configure(
            "TButton",
            background="#303030",
            foreground="white"
        )


        style.configure(
            "Treeview",
            background="#303030",
            foreground="white",
            fieldbackground="#303030"
        )


        style.map(
            "Treeview",
            background=[
                ("selected", "#505050")
            ]
        )


        self.root.configure(
            background="#202020"
        )



    # ---------------------------------
    # JSON 로드
    # ---------------------------------

    def load_config_json(self):

        if not os.path.exists(CONFIG_FILE):

            self.current_config = {
                "system_limits": {},
                "items": [],
                "skills": []
            }

            return


        try:

            with open(
                CONFIG_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                self.current_config = json.load(f)


        except Exception:

            self.current_config = {
                "system_limits": {},
                "items": [],
                "skills": []
            }



        if "system_limits" not in self.current_config:
            self.current_config["system_limits"] = {}


        if "items" not in self.current_config:
            self.current_config["items"] = []


        if "skills" not in self.current_config:
            self.current_config["skills"] = []



    # ---------------------------------
    # ldb -> edb
    # ---------------------------------

    def convert_ldb_to_edb(self):

        if not os.path.exists(LDB_FILE):

            return False


        try:

            subprocess.run(
                [
                    LCF2XML_BIN,
                    LDB_FILE
                ],
                shell=True,
                check=True
            )


            return os.path.exists(
                EDB_FILE
            )


        except Exception as e:

            print(
                "변환 실패:",
                e
            )

            return False



    # ---------------------------------
    # edb 읽기
    # ---------------------------------

    def load_edb_database(self):

        if not os.path.exists(EDB_FILE):

            return


        try:

            with open(
                EDB_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                xml = f.read()



            self.edb_master_items.clear()
            self.edb_master_skills.clear()



            items = re.findall(
                r'<Item\s+id="(\d+)">.*?<name>(.*?)</name>',
                xml,
                re.DOTALL
            )


            for iid, name in items:

                self.edb_master_items[
                    int(iid)
                ] = name or "이름 없음"



            skills = re.findall(
                r'<Skill\s+id="(\d+)">.*?<name>(.*?)</name>',
                xml,
                re.DOTALL
            )


            for sid, name in skills:

                self.edb_master_skills[
                    int(sid)
                ] = name or "이름 없음"



        except Exception as e:

            print(
                "EDB 읽기 오류",
                e
            )
            
    # ---------------------------------
    # GUI 생성
    # ---------------------------------

    def create_widgets(self):

        top = ttk.Frame(
            self.root,
            padding=10
        )

        top.pack(
            fill="x"
        )


        ttk.Button(
            top,
            text="📂 edb로드",
            command=self.load_edb_database
        ).pack(
            side="left",
            padx=5
        )


        ttk.Button(
            top,
            text="💾 저장(ldb전환)",
            command=self.apply_final_patch
        ).pack(
            side="right",
            padx=5
        )


        notebook = ttk.Notebook(
            self.root
        )

        notebook.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )


        # =============================
        # 아이템 탭
        # =============================

        item_frame = ttk.Frame(
            notebook,
            padding=10
        )

        notebook.add(
            item_frame,
            text="📦 아이템"
        )


        self.item_tree = ttk.Treeview(
            item_frame,
            columns=(
                "id",
                "name",
                "count"
            ),
            show="headings"
        )


        self.item_tree.heading(
            "id",
            text="ID"
        )

        self.item_tree.heading(
            "name",
            text="아이템 이름"
        )

        self.item_tree.heading(
            "count",
            text="최대 수량"
        )


        self.item_tree.pack(
            side="left",
            fill="both",
            expand=True
        )


        self.item_tree.bind(
            "<<TreeviewSelect>>",
            self.select_item_list
        )



        item_side = ttk.Frame(
            item_frame,
            padding=10
        )

        item_side.pack(
            side="right",
            fill="y"
        )



        ttk.Label(
            item_side,
            text="아이템 검색"
        ).pack(
            anchor="w"
        )


        self.item_search = ttk.Combobox(
            item_side,
            width=25
        )

        self.item_search.pack(
            pady=5
        )


        self.item_search.bind(
            "<<ComboboxSelected>>",
            self.search_item_select
        )



        ttk.Label(
            item_side,
            text="아이템 ID"
        ).pack(
            anchor="w"
        )


        self.item_id_entry = ttk.Entry(
            item_side,
            width=25
        )

        self.item_id_entry.pack(
            pady=5
        )



        ttk.Label(
            item_side,
            text="최대 수량"
        ).pack(
            anchor="w"
        )


        self.item_value_entry = ttk.Entry(
            item_side,
            width=25
        )

        self.item_value_entry.pack(
            pady=5
        )



        ttk.Button(
            item_side,
            text="➕ 추가/수정",
            command=self.add_item_rule
        ).pack(
            fill="x",
            pady=3
        )


        ttk.Button(
            item_side,
            text="❌ 삭제",
            command=self.delete_item_rule
        ).pack(
            fill="x",
            pady=3
        )



        ttk.Separator(
            item_side
        ).pack(
            fill="x",
            pady=10
        )



        ttk.Button(
            item_side,
            text="전체 삭제",
            command=self.bulk_item_clear
        ).pack(
            fill="x",
            pady=3
        )


        ttk.Button(
            item_side,
            text="기본값 99",
            command=self.bulk_item_99
        ).pack(
            fill="x",
            pady=3
        )


        ttk.Button(
            item_side,
            text="최대값 255",
            command=self.bulk_item_255
        ).pack(
            fill="x",
            pady=3
        )

        # =============================
        # 스킬 탭
        # =============================

        skill_frame = ttk.Frame(
            notebook,
            padding=10
        )

        notebook.add(
            skill_frame,
            text="⚡ 스킬"
        )


        self.skill_tree = ttk.Treeview(
            skill_frame,
            columns=(
                "id",
                "name",
                "critical",
                "power"
            ),
            show="headings"
        )


        self.skill_tree.heading(
            "id",
            text="ID"
        )

        self.skill_tree.heading(
            "name",
            text="스킬 이름"
        )

        self.skill_tree.heading(
            "critical",
            text="크리티컬"
        )

        self.skill_tree.heading(
            "power",
            text="위력"
        )


        self.skill_tree.pack(
            side="left",
            fill="both",
            expand=True
        )


        self.skill_tree.bind(
            "<<TreeviewSelect>>",
            self.select_skill_list
        )



        skill_side = ttk.Frame(
            skill_frame,
            padding=10
        )

        skill_side.pack(
            side="right",
            fill="y"
        )



        ttk.Label(
            skill_side,
            text="스킬 검색"
        ).pack(
            anchor="w"
        )


        self.skill_search = ttk.Combobox(
            skill_side,
            width=25
        )

        self.skill_search.pack(
            pady=5
        )


        self.skill_search.bind(
            "<<ComboboxSelected>>",
            self.search_skill_select
        )



        ttk.Label(
            skill_side,
            text="스킬 ID"
        ).pack(
            anchor="w"
        )


        self.skill_id_entry = ttk.Entry(
            skill_side,
            width=25
        )

        self.skill_id_entry.pack(
            pady=5
        )



        ttk.Label(
            skill_side,
            text="크리티컬"
        ).pack(
            anchor="w"
        )


        self.skill_critical_entry = ttk.Entry(
            skill_side,
            width=25
        )

        self.skill_critical_entry.pack(
            pady=5
        )



        ttk.Label(
            skill_side,
            text="위력"
        ).pack(
            anchor="w"
        )


        self.skill_power_entry = ttk.Entry(
            skill_side,
            width=25
        )

        self.skill_power_entry.pack(
            pady=5
        )



        ttk.Button(
            skill_side,
            text="➕ 추가/수정",
            command=self.add_skill_rule
        ).pack(
            fill="x",
            pady=3
        )


        ttk.Button(
            skill_side,
            text="❌ 삭제",
            command=self.delete_skill_rule
        ).pack(
            fill="x",
            pady=3
        )



        ttk.Separator(
            skill_side
        ).pack(
            fill="x",
            pady=10
        )



        ttk.Button(
            skill_side,
            text="전체 삭제",
            command=self.bulk_skill_clear
        ).pack(
            fill="x",
            pady=3
        )


        ttk.Button(
            skill_side,
            text="크리티컬 초기화 (0)",
            command=self.reset_skill_critical
        ).pack(
            fill="x",
            pady=3
        )



        # =============================
        # 시스템 탭
        # =============================

        sys_frame = ttk.Frame(
            notebook,
            padding=10
        )

        notebook.add(
            sys_frame,
            text="⚙ 시스템"
        )


        self.sys_tree = ttk.Treeview(
            sys_frame,
            columns=(
                "key",
                "name",
                "value"
            ),
            show="headings"
        )


        self.sys_tree.heading(
            "key",
            text="옵션"
        )

        self.sys_tree.heading(
            "name",
            text="이름"
        )

        self.sys_tree.heading(
            "value",
            text="값"
        )


        self.sys_tree.pack(
            side="left",
            fill="both",
            expand=True
        )


        sys_side = ttk.Frame(
            sys_frame,
            padding=10
        )

        sys_side.pack(
            side="right",
            fill="y"
        )


        ttk.Label(
            sys_side,
            text="변경 값"
        ).pack(
            anchor="w"
        )


        self.sys_value_entry = ttk.Entry(
            sys_side,
            width=25
        )

        self.sys_value_entry.pack(
            pady=5
        )


        ttk.Button(
            sys_side,
            text="수정",
            command=self.modify_sys_limit
        ).pack(
            fill="x"
        )


        ttk.Button(
            sys_side,
            text="전체 초기화",
            command=self.reset_sys_limits
        ).pack(
            fill="x",
            pady=5
        )



        self.update_ui_tables()
        
    # ---------------------------------
    # 검색 목록 갱신
    # ---------------------------------

    def update_search_lists(self):

        if hasattr(self, "item_search"):

            self.item_search["values"] = [
                f"{i} : {name}"
                for i, name in self.edb_master_items.items()
            ]


        if hasattr(self, "skill_search"):

            self.skill_search["values"] = [
                f"{i} : {name}"
                for i, name in self.edb_master_skills.items()
            ]



    # ---------------------------------
    # 아이템 검색 선택
    # ---------------------------------

    def search_item_select(self, event=None):

        value = self.item_search.get()

        if not value:
            return


        iid = int(
            value.split(":")[0]
        )


        self.item_id_entry.delete(
            0,
            tk.END
        )

        self.item_id_entry.insert(
            0,
            str(iid)
        )



    # ---------------------------------
    # 스킬 검색 선택
    # ---------------------------------

    def search_skill_select(self, event=None):

        value = self.skill_search.get()

        if not value:
            return


        sid = int(
            value.split(":")[0]
        )


        self.skill_id_entry.delete(
            0,
            tk.END
        )


        self.skill_id_entry.insert(
            0,
            str(sid)
        )



    # ---------------------------------
    # 아이템 리스트 선택
    # ---------------------------------

    def select_item_list(self, event=None):

        selected = self.item_tree.selection()

        if not selected:
            return


        data = self.item_tree.item(
            selected[0]
        )["values"]


        self.item_id_entry.delete(
            0,
            tk.END
        )


        self.item_id_entry.insert(
            0,
            str(data[0])
        )


        self.item_value_entry.delete(
            0,
            tk.END
        )


        self.item_value_entry.insert(
            0,
            str(data[2])
        )



    # ---------------------------------
    # 스킬 리스트 선택
    # ---------------------------------

    def select_skill_list(self, event=None):

        selected = self.skill_tree.selection()

        if not selected:
            return


        data = self.skill_tree.item(
            selected[0]
        )["values"]


        self.skill_id_entry.delete(
            0,
            tk.END
        )

        self.skill_id_entry.insert(
            0,
            str(data[0])
        )



        self.skill_critical_entry.delete(
            0,
            tk.END
        )

        self.skill_critical_entry.insert(
            0,
            str(data[2])
        )



        self.skill_power_entry.delete(
            0,
            tk.END
        )

        self.skill_power_entry.insert(
            0,
            str(data[3])
        )



    # ---------------------------------
    # 아이템 전체 삭제
    # ---------------------------------

    def bulk_item_clear(self):

        if not messagebox.askyesno(
            "확인",
            "등록된 아이템 설정을 모두 삭제합니까?"
        ):
            return


        self.current_config["items"] = []

        self.save_config()

        self.update_ui_tables()



    # ---------------------------------
    # 아이템 99 적용
    # ---------------------------------

    def bulk_item_99(self):

        for item in self.current_config["items"]:

            item["easyrpg_max_count"] = 99


        self.save_config()

        self.update_ui_tables()



    # ---------------------------------
    # 아이템 255 적용
    # ---------------------------------

    def bulk_item_255(self):

        for item in self.current_config["items"]:

            item["easyrpg_max_count"] = 255


        self.save_config()

        self.update_ui_tables()



    # ---------------------------------
    # 스킬 전체 삭제
    # ---------------------------------

    def bulk_skill_clear(self):

        if not messagebox.askyesno(
            "확인",
            "등록된 스킬 설정을 모두 삭제합니까?"
        ):
            return


        self.current_config["skills"] = []

        self.save_config()

        self.update_ui_tables()



    # ---------------------------------
    # 스킬 크리티컬 초기화
    # ---------------------------------

    def reset_skill_critical(self):

        for skill in self.current_config["skills"]:

            skill[
                "easyrpg_critical_hit_chance"
            ] = 0


        self.save_config()

        self.update_ui_tables()



    # ---------------------------------
    # JSON 저장
    # ---------------------------------

    def save_config(self):

        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.current_config,
                f,
                ensure_ascii=False,
                indent=2
            )
            
    # ---------------------------------
    # 최종 저장 (EDB -> LDB)
    # ---------------------------------

    def apply_final_patch(self):

        if not os.path.exists(EDB_FILE):

            messagebox.showwarning(
                "EDB 없음",
                "RPG_RT.edb 파일을 찾을 수 없습니다.\n\n"
                "edb로드 버튼을 눌러서 edb 파일로 전환하세요."
            )

            return



        try:

            tree = ET.parse(
                EDB_FILE
            )

            root = tree.getroot()



            # =================================
            # 시스템 옵션 적용
            # =================================

            system_container = (
                root.find(".//System")
                or root.find(".//system")
            )


            if system_container is not None:

                for key, info in self.current_config.get(
                    "system_limits",
                    {}
                ).items():


                    if isinstance(info, dict):

                        value = info.get(
                            "value",
                            -1
                        )

                    else:

                        value = info



                    tag = system_container.find(
                        key
                    )


                    if tag is not None:

                        tag.text = str(
                            value
                        )

                    else:

                        ET.SubElement(
                            system_container,
                            key
                        ).text = str(
                            value
                        )



            # =================================
            # 아이템 옵션 적용
            # =================================

            for container in root.iter():

                if container.tag.lower() not in (
                    "items",
                    "item_container"
                ):
                    continue



                for rule in self.current_config.get(
                    "items",
                    []
                ):


                    for item_node in (
                        container.findall("Item")
                        +
                        container.findall("item")
                    ):


                        node_id = item_node.get(
                            "id"
                        )


                        if node_id is None:

                            id_node = item_node.find(
                                "id"
                            )

                            if id_node is not None:

                                node_id = id_node.text



                        if node_id is not None and int(node_id) == rule["id"]:


                            value_node = item_node.find(
                                "easyrpg_max_count"
                            )


                            if value_node is None:

                                value_node = ET.SubElement(
                                    item_node,
                                    "easyrpg_max_count"
                                )


                            value_node.text = str(
                                rule["easyrpg_max_count"]
                            )



            # =================================
            # 스킬 옵션 적용
            # =================================

            for container in root.iter():

                if container.tag.lower() not in (
                    "skills",
                    "skill_container",
                    "skills_container"
                ):
                    continue



                for rule in self.current_config.get(
                    "skills",
                    []
                ):


                    for skill_node in (
                        container.findall("Skill")
                        +
                        container.findall("skill")
                    ):


                        node_id = skill_node.get(
                            "id"
                        )


                        if node_id is None:

                            id_node = skill_node.find(
                                "id"
                            )

                            if id_node is not None:

                                node_id = id_node.text



                        if node_id is None:
                            continue



                        if int(node_id) != rule["id"]:
                            continue



                        # 크리티컬

                        if rule.get(
                            "easyrpg_critical_hit_chance"
                        ) != "keep":


                            crit_node = skill_node.find(
                                "easyrpg_critical_hit_chance"
                            )


                            if crit_node is None:

                                crit_node = ET.SubElement(
                                    skill_node,
                                    "easyrpg_critical_hit_chance"
                                )


                            crit_node.text = str(
                                rule[
                                    "easyrpg_critical_hit_chance"
                                ]
                            )



                        # 위력

                        if rule.get(
                            "rating"
                        ) != "keep":


                            rating_node = skill_node.find(
                                "rating"
                            )


                            if rating_node is None:

                                rating_node = ET.SubElement(
                                    skill_node,
                                    "rating"
                                )


                            rating_node.text = str(
                                rule["rating"]
                            )



            # =================================
            # EDB 저장
            # =================================

            tree.write(
                EDB_FILE,
                encoding="utf-8",
                xml_declaration=True
            )



            # =================================
            # EDB -> LDB 변환
            # =================================

            subprocess.run(
                [
                    LCF2XML_BIN,
                    EDB_FILE
                ],
                shell=True,
                check=True
            )



            # =================================
            # EDB 삭제
            # =================================

            if os.path.exists(
                EDB_FILE
            ):

                os.remove(
                    EDB_FILE
                )



            messagebox.showinfo(
                "완료",
                "저장(ldb전환)이 완료되었습니다.\n\n"
                "RPG_RT.edb 파일은 삭제되었습니다."
            )



        except Exception as e:


             messagebox.showerror(
                "패치 오류",
                str(e)
            )


if __name__ == "__main__":

    root = tk.Tk()

    app = PureEdbEasyRpgPatcher(
        root
    )

    root.mainloop()