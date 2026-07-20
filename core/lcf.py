"""
core/lcf.py
lcf2xml.exe 실행, RPG_RT.ldb <-> RPG_RT.edb 변환, edb(XML) 파싱,
그리고 최종 패치(설정값을 edb에 반영하고 다시 ldb로 컴파일)를 담당합니다.
UI(탭)와 독립적으로, ConfigManager(cfg)와 아이템/스킬 마스터 데이터만으로 동작합니다.
"""
import os
import re
import traceback
import subprocess
import xml.etree.ElementTree as ET
from tkinter import messagebox


def run_lcf2xml(cfg, target_file):
    """lcf2xml.exe를 target_file에 대해 실행합니다. 실패 시 사용자 메시지를 띄우고 False를 반환합니다."""
    try:
        subprocess.run([cfg.lcf2xml_bin, target_file], check=True, shell=True, cwd=cfg.game_dir)
        return True
    except FileNotFoundError:
        messagebox.showerror("실패", "lcf2xml.exe 실행 파일을 찾을 수 없습니다.\n프로그램 폴더를 확인해 주세요.")
        return False
    except subprocess.CalledProcessError as e:
        messagebox.showerror("실패", f"lcf2xml 변환 중 오류가 발생했습니다. (종료 코드: {e.returncode})")
        return False
    except Exception as e:
        print("---- 상세 오류 ----"); traceback.print_exc()
        messagebox.showerror("실패", f"lcf2xml 실행 중 알 수 없는 오류가 발생했습니다.\n{e}")
        return False


def decompile_and_parse_edb_directly(cfg):
    """RPG_RT.ldb -> RPG_RT.edb 로 역변환하고, 아이템/스킬 마스터 정보를 파싱합니다.
    반환값: (edb_master_items, edb_master_item_types, edb_master_skills) - 실패 시 (None, None, None)"""
    if not os.path.exists(cfg.ldb_file):
        return None, None, None

    print("[동기화] 최신 RPG_RT.edb 역변환 확보 중...")
    if not run_lcf2xml(cfg, cfg.ldb_file):
        return None, None, None
    if not os.path.exists(cfg.edb_file):
        messagebox.showerror(
            "실패",
            "RPG_RT.edb 파일이 생성되지 않았습니다.\nlcf2xml 변환이 정상적으로 끝나지 않은 것 같습니다."
        )
        return None, None, None

    print("[파싱] edb(XML) 내부에서 실시간으로 정보 색출 중...")
    edb_master_items, edb_master_item_types, edb_master_skills = {}, {}, {}
    try:
        with open(cfg.edb_file, "r", encoding="utf-8") as f:
            xml_text = f.read()

        item_block_pattern = re.compile(r'<Item\s+id="(\d+)">(.*?)</Item>', re.DOTALL | re.IGNORECASE)
        for match in item_block_pattern.finditer(xml_text):
            iid, block = int(match.group(1)), match.group(2)
            name_m = re.search(r'<name>(.*?)</name>', block, re.DOTALL | re.IGNORECASE)
            type_m = re.search(r'<type>(.*?)</type>', block, re.DOTALL | re.IGNORECASE)
            edb_master_items[iid] = name_m.group(1) if name_m and name_m.group(1) else "이름 없음"
            if type_m and type_m.group(1).strip().lstrip("-").isdigit():
                edb_master_item_types[iid] = int(type_m.group(1).strip())

        skill_block_pattern = re.compile(r'<Skill\s+id="(\d+)">(.*?)</Skill>', re.DOTALL | re.IGNORECASE)
        for match in skill_block_pattern.finditer(xml_text):
            sid, block = int(match.group(1)), match.group(2)
            name_m = re.search(r'<name>(.*?)</name>', block, re.DOTALL | re.IGNORECASE)
            edb_master_skills[sid] = name_m.group(1) if name_m and name_m.group(1) else "이름 없음"

        print(f"[동기화 완료] 아이템: {len(edb_master_items)}개, 스킬: {len(edb_master_skills)}개 매칭 성공.")
        return edb_master_items, edb_master_item_types, edb_master_skills
    except Exception as e:
        print("---- 상세 오류 ----"); traceback.print_exc()
        messagebox.showerror("실패", f"RPG_RT.edb 파일을 분석하는 중 오류가 발생했습니다.\n{e}")
        return None, None, None


def apply_final_patch(cfg):
    """현재 프로젝트 설정(system_limits/items/skills)을 edb에 반영하고
    다시 ldb로 컴파일한 뒤, edb를 정리합니다. 성공하면 True를 반환합니다."""
    if not os.path.exists(cfg.edb_file):
        messagebox.showerror("실패", "RPG_RT.edb 파일이 없습니다. 먼저 'edb로드' 버튼을 눌러주세요.")
        return False

    try:
        tree = ET.parse(cfg.edb_file)
        root = tree.getroot()
    except Exception as e:
        print("---- 상세 오류 ----"); traceback.print_exc()
        messagebox.showerror("실패", f"RPG_RT.edb 파일을 읽는 중 오류가 발생했습니다.\n파일이 손상되었을 수 있습니다.\n{e}")
        return False

    _container = root.find(".//system")
    system_container = _container if _container is not None else root.find(".//System")
    if system_container is not None:
        _node = system_container.find("System")
        actual_system_node = _node if _node is not None else system_container.find("system")
        if actual_system_node is not None:
            for key, defn in cfg.current_config.get("system_limits", {}).items():
                t = defn.get("type", "int")
                val = defn.get("value")
                if t == "bool":
                    text_val = "1" if val else "0"
                elif t == "list":
                    text_val = ",".join(str(v) for v in (val or []))
                else:
                    text_val = str(val)
                tag = actual_system_node.find(key)
                if tag is not None: tag.text = text_val
                else: ET.SubElement(actual_system_node, key).text = text_val
            print(" -> 시스템 옵션 한계 해제 완료.")

    try:
        for el in root.iter():
            t_low = el.tag.lower()
            if t_low == "items" or t_low == "item_container":
                for it in cfg.current_config.get("items", []):
                    for item_node in el.findall("Item") + el.findall("item"):
                        nid = item_node.get("id") or (item_node.find("id").text if item_node.find("id") is not None else None)
                        if nid and int(nid) == it["id"]:
                            tag = item_node.find("easyrpg_max_count")
                            if tag is not None: tag.text = str(it["easyrpg_max_count"])
                            else: ET.SubElement(item_node, "easyrpg_max_count").text = str(it["easyrpg_max_count"])
            if t_low == "skills" or t_low == "skills_container" or t_low == "skill_container":
                for sk in cfg.current_config.get("skills", []):
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
                            if sk.get("physical_rate", "keep") != "keep":
                                p_tag = skill_node.find("physical_rate")
                                if p_tag is not None: p_tag.text = str(sk["physical_rate"])
                                else: ET.SubElement(skill_node, "physical_rate").text = str(sk["physical_rate"])
                            if sk.get("magical_rate", "keep") != "keep":
                                m_tag = skill_node.find("magical_rate")
                                if m_tag is not None: m_tag.text = str(sk["magical_rate"])
                                else: ET.SubElement(skill_node, "magical_rate").text = str(sk["magical_rate"])
    except Exception as e:
        print("---- 상세 오류 ----"); traceback.print_exc()
        messagebox.showerror("실패", f"아이템/스킬 값을 적용하는 중 오류가 발생했습니다.\n{e}")
        return False

    try:
        tree.write(cfg.edb_file, encoding="utf-8", xml_declaration=True)
    except Exception as e:
        print("---- 상세 오류 ----"); traceback.print_exc()
        messagebox.showerror("실패", f"RPG_RT.edb 파일 저장 중 오류가 발생했습니다.\n{e}")
        return False

    if not run_lcf2xml(cfg, cfg.edb_file):
        return False

    if not os.path.exists(cfg.ldb_file):
        messagebox.showerror("실패", "RPG_RT.ldb 파일이 생성되지 않았습니다. lcf2xml 변환을 다시 확인해 주세요.")
        return False

    if os.path.exists(cfg.edb_file):
        try:
            os.remove(cfg.edb_file)
        except Exception as e:
            print(f"edb 삭제 실패: {e}")
            messagebox.showwarning("알림", f"패치는 완료되었지만 RPG_RT.edb 삭제에는 실패했습니다.\n(사유: {e})\n다음 'edb로드' 시 자동으로 새로 갱신됩니다.")

    messagebox.showinfo("대성공", "전역 한계 해제 및 스킬/아이템 개조 패치가 완료되었습니다!\nRPG_RT.edb는 정리되었습니다. 다시 수정하려면 'edb로드'를 눌러주세요.")
    return True
