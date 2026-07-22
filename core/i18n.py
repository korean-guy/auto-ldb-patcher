"""
core/i18n.py
다국어 지원을 위한 최소한의 문자열 리소스 시스템.

지금 당장 한국어 외 언어를 지원하지는 않지만(요청사항: "이번 작업에서 다국어
기능을 구현할 필요는 없음"), 앞으로 언어 리소스 파일만 추가하면 되도록
"문자열을 코드에 직접 쓰지 않고 t(키)로 조회" 하는 구조만 미리 만들어 둡니다.

사용법:
    from core.i18n import t
    ttk.Button(parent, text=t("common.btn_add"))
    messagebox.showinfo(t("common.title_done"), t("item_tab.msg_batch_done", count=3, value=99))

리소스 파일: core/locales/<lang>.json (지금은 ko.json만 존재)
새 언어를 추가하려면
  1) core/locales/en.json, core/locales/ja.json 처럼 같은 키 구조로 파일을 추가하고
  2) set_language("en") 을 호출하면 됩니다 (예: 공통 설정의 settings.language 값을 사용).
현재 UI 코드는 전혀 수정할 필요가 없습니다.
"""
import os
import json

LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")
DEFAULT_LANG = "ko"

_cache = {}
_current_lang = DEFAULT_LANG


def set_language(lang):
    """UI에 표시할 언어를 바꿉니다. 지금은 ko.json만 존재하므로 사실상 항상 한국어입니다."""
    global _current_lang
    _current_lang = lang


def get_language():
    return _current_lang


def _load(lang):
    if lang in _cache:
        return _cache[lang]
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[i18n] '{path}' 로드 실패: {e}")
    _cache[lang] = data
    return data


def t(key, **kwargs):
    """키에 해당하는 문자열을 현재 언어로 반환합니다.
    현재 언어에 없으면 기본 언어(ko), 그래도 없으면 키 문자열 자체를 그대로 반환합니다
    (번역이 통째로 누락돼도 프로그램이 죽지 않고 키가 그대로 보이는 정도로만 동작합니다).
    kwargs를 주면 {name} 형태의 자리표시자를 채워 넣습니다."""
    value = _load(_current_lang).get(key)
    if value is None and _current_lang != DEFAULT_LANG:
        value = _load(DEFAULT_LANG).get(key)
    if value is None:
        value = key
    if kwargs:
        try:
            return value.format(**kwargs)
        except Exception:
            return value
    return value


def t_field(namespace, field_key, attr, fallback):
    """옵션 정의(system_limits/스킬·아이템 필드)의 이름/설명처럼, 지금은 JSON/스키마에
    직접 한국어 텍스트가 저장되어 있는 값을 위한 조회 함수입니다.
    '{namespace}.{field_key}.{attr}' 키의 번역이 리소스 파일에 있으면 그것을 쓰고,
    없으면 지금까지 해오던 대로 스키마/설정에 저장된 실제 값(fallback)을 그대로 씁니다.
    나중에 옵션 이름/설명까지 다국어로 옮기고 싶을 때, 코드를 고칠 필요 없이
    리소스 파일에 이 키들만 채워 넣으면 자동으로 우선 적용됩니다."""
    key = f"{namespace}.{field_key}.{attr}"
    value = _load(_current_lang).get(key)
    if value is None and _current_lang != DEFAULT_LANG:
        value = _load(DEFAULT_LANG).get(key)
    return value if value is not None else fallback
