# 빌드 안내 (개발 → 단일 exe 배포)

## 폴더 구조
```
auto ldb patcher.py
core/
    __init__.py
    utils.py            # 경로/문자열/ini파싱/스키마 변환 등 순수 유틸
    theme.py             # 다크 테마 색상 + 위젯 헬퍼 + 트리뷰 정렬/컬럼폭 저장 헬퍼
    i18n.py               # 다국어 문자열 리소스 조회(t()) - 아래 "다국어 지원" 항목 참고
    context_menu.py        # 좌측 리스트 공통 우클릭 메뉴(위로/아래로 이동, 삭제)
    config.py            # JSON 읽기/쓰기, 공통·프로젝트 config 관리, 프로젝트(ldb) 선택
    logger.py            # 콘솔 대신 GUI 로그 패널로 출력하는 전역 로거
    property_panel.py    # System/Skill/Item/Actor 탭이 공유하는 "속성 편집기" 공통 컴포넌트
    skill_schema.py       # 스킬별 EasyRPG 옵션 정의 + 예전 버전 마이그레이션
    item_schema.py         # 아이템별 EasyRPG 옵션 정의 + 예전 버전 마이그레이션
    actor_schema.py         # 액터별 EasyRPG 옵션/경험치/능력치 성장 정의
    lcf.py                # lcf2xml 실행, edb 파싱, 최종 패치(edb→ldb)
    locales/
        ko.json            # 한국어 UI 문자열 리소스 (현재 유일한 언어)
tabs/
    __init__.py
    item_tab.py
    skill_tab.py
    system_tab.py
    actor_tab.py
lcf2xml.exe        # (직접 준비)
config.json         # 최초 실행 시 자동 생성됨 (미리 안 넣어도 됨)
projects/            # 최초 실행 시 자동 생성됨
```

## 개발 중 실행
```
python "auto ldb patcher.py"
```
core/, tabs/ 아래 파일들을 그대로 import해서 실행됩니다. 별도 설정 필요 없습니다.

## 배포용 단일 exe 빌드 (PyInstaller)
```
pip install pyinstaller
pyinstaller --onefile --windowed --name "EasyRPG DB Editor" "auto ldb patcher.py"
```
- `--onefile` : core/, tabs/ 안의 .py 파일들은 import 구문을 통해 자동으로 정적 분석되어
  exe 하나에 전부 포함됩니다. 별도 `--hidden-import`나 `--add-data` 옵션이 필요 없습니다.
- `--windowed` : 실행 시 콘솔 창이 뜨지 않습니다. (모든 진행 상황/오류는 이제 프로그램
  하단의 로그 패널에 표시되므로, 콘솔 창이 없어도 사용에 지장이 없습니다.)
- 빌드 결과물은 `dist/EasyRPG DB Editor.exe` 에 생성됩니다.

## 배포 시 폴더 구성
exe만 배포하지 않고, **exe와 같은 폴더에 lcf2xml.exe를 함께 넣어야 합니다** (프로그램이
런타임에 `lcf2xml.exe`를 실행 파일과 같은 폴더에서 찾습니다).
```
배포 폴더/
    EasyRPG DB Editor.exe
    lcf2xml.exe
```
`config.json`과 `projects/` 폴더는 최초 실행 시 exe 폴더에 자동으로 생성되므로 미리
준비할 필요가 없습니다.

## 프로젝트 선택 방식
프로그램 시작 시 폴더가 아니라 **RPG_RT.ldb 파일**을 직접 선택합니다. 선택한 파일이
"RPG_RT.ldb"가 아니면 다시 선택하라는 안내가 뜨고, 올바른 파일을 고르면 그 파일이
있는 폴더가 자동으로 게임 폴더로 인식됩니다.

## 다국어 지원 (구조만 준비된 상태)
화면에 보이는 모든 문자열(버튼/탭/메뉴/메시지박스/로그 메시지)은 코드에 직접
적혀있지 않고 `core/i18n.py`의 `t("키")`를 통해 `core/locales/ko.json`에서
가져옵니다. 지금은 한국어(ko)만 존재하고 실제로 언어를 전환하는 기능은
아직 없지만, 나중에 영어/일본어를 추가하고 싶을 때는:

1. `core/locales/en.json`, `core/locales/ja.json`을 `ko.json`과 **같은 키
   구조**로 만들고 번역문만 채웁니다. 코드는 전혀 건드릴 필요가 없습니다.
2. 어딘가에서 `core.i18n.set_language("en")`을 호출하면 그 시점부터 `t()`가
   영어 문자열을 반환합니다 (예: 공통 설정의 `settings.language` 값을 읽어서
   프로그램 시작 시 한 번 호출해주는 식으로 연결하면 됩니다).
3. 번역이 아직 없는 키는 자동으로 한국어(기본 언어)로, 그마저 없으면 키
   문자열 그대로 표시되므로 번역이 일부만 되어 있어도 프로그램이 깨지지
   않습니다.

옵션 이름/설명(System/Skill/Item 탭의 필드 label·description)은 현재
`core/config.py`, `core/skill_schema.py`, `core/item_schema.py`에 한국어
텍스트로 직접 저장되어 있습니다(프로젝트 config.json에도 그대로 저장되는
값이라 지금 당장 키 체계로 바꾸는 건 호환성 위험이 있어 보류했습니다).
다만 표시하는 코드(`system_tab.py`의 `t_field("sys", 필드명, "name", ...)`
등)는 이미 "리소스에 `sys.<필드명>.name` 같은 키가 있으면 그것을 우선 사용하고,
없으면 지금처럼 저장된 값을 그대로 쓰는" 방식으로 되어 있습니다. 나중에
옵션 이름/설명까지 번역하고 싶으면 리소스 파일에 그 키들만 추가하면 되고,
코드 수정은 필요 없습니다.


1. `tabs/새탭.py` 파일을 만들고, `build(self, notebook)`와 `refresh(self)`를 구현하는
   클래스를 작성합니다 (`tabs/item_tab.py`를 참고하면 가장 빠릅니다).
   - 좌측 목록 + 우측 "속성 편집기" 형태로 만들고 싶다면 `tabs/system_tab.py` 또는
     `tabs/skill_tab.py`를 참고해 `core/property_panel.py`의
     `make_fixed_scroll_panel()` / `render_field_row()` / `render_group_header()`를
     재사용하면 됩니다. 이 컴포넌트는 항목이 몇 개가 되든 우측 패널 크기가
     고정되어 있어 레이아웃이 흔들리지 않습니다.
   - 프로젝트를 불러올 때마다 예전 버전 데이터를 새 형식으로 옮기고 싶다면
     `on_project_loaded(self)` 메서드를 추가로 구현하세요. main 파일이 프로젝트를
     불러올 때마다 자동으로 호출해 줍니다 (`tabs/skill_tab.py` 참고).
2. `auto ldb patcher.py` 상단의 `TAB_CLASSES` 목록에 새 클래스를 한 줄 추가합니다.
   ```python
   from tabs.monster_tab import MonsterTab
   TAB_CLASSES = [ItemTab, SkillTab, SystemTab, MonsterTab]
   ```
메인 파일은 이 두 줄 외에는 수정할 필요가 없습니다.

## 새 EasyRPG 옵션 추가 방법
- **시스템 옵션**: `core/config.py`의 `DEFAULT_SYSTEM_DEFS`에 항목 하나만 추가하면
  System 탭에 자동으로 나타납니다 (`group` 키로 분류, `type`으로 int/bool/enum/list
  중 알맞은 UI가 자동 생성됩니다).
- **스킬 옵션**: `core/skill_schema.py`의 `SKILL_FIELD_DEFS`에 항목 하나만 추가하면
  Skill 탭 속성 편집기와 최종 패치(edb 기록) 양쪽에 자동으로 반영됩니다. 다른 필드
  값에 따라 활성/비활성이 갈리는 옵션은 `"enabled_when": {"field": "필드명",
  "equals": 값}`을 추가하면 됩니다 (`easyrpg_hp_type`/`easyrpg_hp_cost`/
  `easyrpg_hp_percent` 참고).
