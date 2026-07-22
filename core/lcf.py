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

from core.logger import log
from core.i18n import t
from core.skill_schema import SKILL_FIELD_DEFS
from core.item_schema import ITEM_FIELD_DEFS


def run_lcf2xml(cfg, target_file):
    """lcf2xml.exe를 target_file에 대해 실행합니다. 실패 시 사용자 메시지를 띄우고 False를 반환합니다."""
    try:
        subprocess.run([cfg.lcf2xml_bin, target_file], check=True, shell=True, cwd=cfg.game_dir)
        return True
    except FileNotFoundError:
        messagebox.showerror(t("common.title_fail"), t("lcf.msg_exe_not_found"))
        return False
    except subprocess.CalledProcessError as e:
        messagebox.showerror(t("common.title_fail"), t("lcf.msg_convert_error", code=e.returncode))
        return False
    except Exception as e:
        log.error(t("lcf.log_error_detail_hint")); traceback.print_exc()
        messagebox.showerror(t("common.title_fail"), t("lcf.msg_unknown_error", reason=e))
        return False


def decompile_and_parse_edb_directly(cfg):
    """RPG_RT.ldb -> RPG_RT.edb 로 역변환하고, 아이템/스킬 마스터 정보를 파싱합니다.
    반환값: (edb_master_items, edb_master_item_types, edb_master_skills, edb_master_skill_stats)
    실패 시 (None, None, None, None)"""
    if not os.path.exists(cfg.ldb_file):
        return None, None, None, None

    log.info(t("lcf.log_converting"))
    if not run_lcf2xml(cfg, cfg.ldb_file):
        return None, None, None, None
    if not os.path.exists(cfg.edb_file):
        messagebox.showerror(
            t("common.title_fail"),
            t("lcf.msg_edb_not_created")
        )
        return None, None, None, None

    log.info(t("lcf.log_parsing"))
    edb_master_items, edb_master_item_types, edb_master_skills, edb_master_skill_stats = {}, {}, {}, {}
    try:
        with open(cfg.edb_file, "r", encoding="utf-8") as f:
            xml_text = f.read()

        item_block_pattern = re.compile(r'<Item\s+id="(\d+)">(.*?)</Item>', re.DOTALL | re.IGNORECASE)
        for match in item_block_pattern.finditer(xml_text):
            iid, block = int(match.group(1)), match.group(2)
            name_m = re.search(r'<name>(.*?)</name>', block, re.DOTALL | re.IGNORECASE)
            type_m = re.search(r'<type>(.*?)</type>', block, re.DOTALL | re.IGNORECASE)
            edb_master_items[iid] = name_m.group(1) if name_m and name_m.group(1) else t("common.name_unknown")
            if type_m and type_m.group(1).strip().lstrip("-").isdigit():
                edb_master_item_types[iid] = int(type_m.group(1).strip())

        skill_block_pattern = re.compile(r'<Skill\s+id="(\d+)">(.*?)</Skill>', re.DOTALL | re.IGNORECASE)
        for match in skill_block_pattern.finditer(xml_text):
            sid, block = int(match.group(1)), match.group(2)
            name_m = re.search(r'<name>(.*?)</name>', block, re.DOTALL | re.IGNORECASE)
            edb_master_skills[sid] = name_m.group(1) if name_m and name_m.group(1) else t("common.name_unknown")

            stats = {}
            for tag in ("rating", "physical_rate", "magical_rate"):
                m = re.search(rf'<{tag}>(.*?)</{tag}>', block, re.DOTALL | re.IGNORECASE)
                if m and m.group(1).strip().lstrip("-").isdigit():
                    stats[tag] = int(m.group(1).strip())
            edb_master_skill_stats[sid] = stats

        log.info(t("lcf.log_sync_done", item_count=len(edb_master_items), skill_count=len(edb_master_skills)))
        return edb_master_items, edb_master_item_types, edb_master_skills, edb_master_skill_stats
    except Exception as e:
        log.error(t("lcf.log_error_detail_hint")); traceback.print_exc()
        messagebox.showerror(t("common.title_fail"), t("lcf.msg_parse_error", reason=e))
        return None, None, None, None


def apply_final_patch(cfg):
    """현재 프로젝트 설정(system_limits/items/skills)을 edb에 반영하고
    다시 ldb로 컴파일한 뒤, edb를 정리합니다. 성공하면 True를 반환합니다."""
    if not os.path.exists(cfg.edb_file):
        messagebox.showerror(t("common.title_fail"), t("lcf.msg_no_edb"))
        return False

    try:
        tree = ET.parse(cfg.edb_file)
        root = tree.getroot()
    except Exception as e:
        log.error(t("lcf.log_error_detail_hint")); traceback.print_exc()
        messagebox.showerror(t("common.title_fail"), t("lcf.msg_edb_read_error", reason=e))
        return False

    _container = root.find(".//system")
    system_container = _container if _container is not None else root.find(".//System")
    if system_container is not None:
        _node = system_container.find("System")
        actual_system_node = _node if _node is not None else system_container.find("system")
        if actual_system_node is not None:
            for key, defn in cfg.current_config.get("system_limits", {}).items():
                field_type = defn.get("type", "int")
                val = defn.get("value")
                if field_type == "bool":
                    text_val = "1" if val else "0"
                elif field_type == "list":
                    text_val = ",".join(str(v) for v in (val or []))
                else:
                    text_val = str(val)
                tag = actual_system_node.find(key)
                if tag is not None: tag.text = text_val
                else: ET.SubElement(actual_system_node, key).text = text_val
            log.info(t("lcf.log_system_applied"))

    try:
        for el in root.iter():
            t_low = el.tag.lower()
            if t_low == "items" or t_low == "item_container":
                for it in cfg.current_config.get("items", []):
                    for item_node in el.findall("Item") + el.findall("item"):
                        nid = item_node.get("id") or (item_node.find("id").text if item_node.find("id") is not None else None)
                        if nid and int(nid) == it["id"]:
                            fields = it.get("fields", {})
                            for fd in ITEM_FIELD_DEFS:
                                name = fd["name"]
                                if name not in fields:
                                    continue
                                val = fields[name]
                                text_val = "T" if (fd.get("type") == "bool" and val) else ("F" if fd.get("type") == "bool" else str(val))
                                tag = item_node.find(name)
                                if tag is not None: tag.text = text_val
                                else: ET.SubElement(item_node, name).text = text_val
            if t_low == "skills" or t_low == "skills_container" or t_low == "skill_container":
                for sk in cfg.current_config.get("skills", []):
                    for skill_node in el.findall("Skill") + el.findall("skill"):
                        nid = skill_node.get("id") or (skill_node.find("id").text if skill_node.find("id") is not None else None)
                        if nid and int(nid) == sk["id"]:
                            fields = sk.get("fields", {})
                            for fd in SKILL_FIELD_DEFS:
                                name = fd["name"]
                                if name not in fields:
                                    continue
                                val = fields[name]
                                if fd.get("type") == "bool":
                                    text_val = "T" if val else "F"
                                else:
                                    text_val = str(val)
                                tag = skill_node.find(name)
                                if tag is not None: tag.text = text_val
                                else: ET.SubElement(skill_node, name).text = text_val
    except Exception as e:
        log.error(t("lcf.log_error_detail_hint")); traceback.print_exc()
        messagebox.showerror(t("common.title_fail"), t("lcf.msg_apply_error", reason=e))
        return False

    try:
        tree.write(cfg.edb_file, encoding="utf-8", xml_declaration=True)
    except Exception as e:
        log.error(t("lcf.log_error_detail_hint")); traceback.print_exc()
        messagebox.showerror(t("common.title_fail"), t("lcf.msg_edb_write_error", reason=e))
        return False

    if not run_lcf2xml(cfg, cfg.edb_file):
        return False

    if not os.path.exists(cfg.ldb_file):
        messagebox.showerror(t("common.title_fail"), t("lcf.msg_ldb_not_created"))
        return False

    if os.path.exists(cfg.edb_file):
        try:
            os.remove(cfg.edb_file)
        except Exception as e:
            log.warning(t("lcf.log_edb_delete_fail", reason=e))
            messagebox.showwarning(t("common.title_notice"), t("lcf.msg_edb_delete_fail", reason=e))

    messagebox.showinfo(t("lcf.title_success"), t("lcf.msg_patch_success"))
    log.info(t("lcf.log_patch_done"))
    return True
