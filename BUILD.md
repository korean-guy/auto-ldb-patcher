# 빌드 안내 (개발 → 단일 exe 배포)

## 폴더 구조
```
auto ldb patcher.py
core/
    __init__.py
    utils.py            # 경로/문자열/ini파싱/스키마 변환 등 순수 유틸
    theme.py             # 다크 테마 색상 + 위젯 헬퍼 + 트리뷰 정렬/컬럼폭 저장 헬퍼
    tab_bar.py             # 여러 줄로 자동 개행되는 상단 탭 바 (ttk.Notebook 대체)
    i18n.py               # 다국어 문자열 리소스 조회(t()/t_field()) - 아래 "다국어 지원" 항목 참고
    context_menu.py        # 좌측 리스트 공통 우클릭 메뉴(위로/아래로 이동, 삭제)
    config.py            # JSON 읽기/쓰기, 공통·프로젝트 config 관리, 프로젝트(ldb) 선택, 설정 불러오기
    logger.py            # 콘솔 대신 GUI 로그 패널로 출력하는 전역 로거
    property_panel.py    # 모든 "속성 편집기" 탭이 공유하는 공통 컴포넌트 (번역 조회 포함)
    skill_schema.py       # 스킬별 EasyRPG 옵션 정의 + 예전 버전 마이그레이션
    item_schema.py         # 아이템별 EasyRPG 옵션 정의 + 예전 버전 마이그레이션
    actor_schema.py         # 액터별 EasyRPG 옵션/경험치/능력치 성장 정의
    class_schema.py          # 클래스별 경험치/능력치 성장 정의
    enemy_schema.py          # 적별 기본 스테이터스 + EasyRPG 옵션 정의
    terrain_schema.py        # 지형별 EasyRPG 데미지 옵션 정의
    stat_editor_popup.py      # Actor/Class 탭이 공유하는 "레벨별 능력치 편집" 팝업
    lcf.py                # lcf2xml 실행(변환 중 안내창 포함), edb 파싱, 최종 패치(edb→ldb)
    locales/
        ko.json            # 한국어 UI 문자열 리소스 (기본 언어)
        en.json            # 영어
        ja.json            # 일본어
tabs/
    __init__.py
    actor_tab.py
    class_tab.py
    skill_tab.py
    item_tab.py
    enemy_tab.py
    terrain_tab.py
    system_tab.py
lcf2xml.exe        # (직접 준비, exe와 같은 폴더에 배치)
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

# Windows (cmd/PowerShell) - --add-data 구분자는 세미콜론(;)
pyinstaller --onefile --windowed --name "EasyRPG DB Editor" ^
  --add-data "core/locales;core/locales" ^
  "auto ldb patcher.py"

# macOS/Linux - --add-data 구분자는 콜론(:)
pyinstaller --onefile --windowed --name "EasyRPG DB Editor" \
  --add-data "core/locales:core/locales" \
  "auto ldb patcher.py"
```
- `--onefile` : core/, tabs/ 안의 **.py 파일들**은 import 구문을 통해 자동으로 정적
  분석되어 exe 하나에 전부 포함됩니다.
- **`--add-data "core/locales;core/locales"` (⚠️ 필수)** : `core/locales/*.json`은
  .py 파일이 아니라 순수 데이터 파일이라, PyInstaller가 import 분석만으로는 절대
  자동으로 포함시켜주지 않습니다. **이 옵션을 빠뜨리면 앱이 실행은 되지만 번역
  리소스를 하나도 못 찾아서, 모든 화면 문자열이 "actor_tab.title"처럼 번역되지
  않은 키 이름 그대로 표시됩니다** (한국어 포함 - ko.json도 똑같이 못 찾으므로
  기본 언어도 깨집니다). `core/i18n.py`가 로케일 파일을 하나도 못 찾으면 로그
  패널에 `[i18n] locale 파일을 찾을 수 없습니다: ...` 경고를 남기니, 빌드 후 이
  경고가 보이면 `--add-data` 옵션을 빠뜨렸다는 뜻입니다.
  - `--add-data "원본;대상"` 형식이고, 대상(오른쪽) 경로는 exe 안에서
    `sys._MEIPASS/core/locales`가 되어야 하므로 반드시 `core/locales`로
    맞춰야 합니다(왼쪽 원본 경로는 실제 소스 폴더 기준 상대/절대 경로면 됩니다).
  - **Windows는 구분자가 세미콜론(`;`)**, **macOS/Linux는 콜론(`:`)**입니다 -
    운영체제에 맞는 쪽을 써야 합니다.
- `--windowed` : 실행 시 콘솔 창이 뜨지 않습니다. (모든 진행 상황/오류는 이제 프로그램
  하단의 로그 패널에 표시되므로, 콘솔 창이 없어도 사용에 지장이 없습니다.)
- 빌드 결과물은 `dist/EasyRPG DB Editor.exe` 에 생성됩니다.

## 언어 변경 시 재시작 관련 (PyInstaller onefile 주의사항)
언어를 바꾸면 프로그램이 스스로를 재시작합니다(`subprocess.Popen`으로 새 인스턴스를
띄운 뒤 현재 프로세스를 종료). onefile 빌드에서 자기 자신의 새 인스턴스를 띄울 때
아래 두 가지를 지키지 않으면 오류가 납니다 (`auto ldb patcher.py`의
`App.restart_app()`이 이미 둘 다 처리하고 있습니다 - 새로 손댈 필요는 없지만,
비슷한 걸 직접 구현할 일이 있으면 참고하세요):
- `os.execv()`로 자기 자신을 대체 실행하면 안 됩니다 - onefile 부트로더의 임시
  압축해제 폴더 정리 로직과 충돌해 `Security validation failure: failed to
  obtain executable path for parent process!` 오류가 납니다. 반드시
  `subprocess.Popen`으로 완전히 새 프로세스를 띄운 뒤, 지금 프로세스는
  `sys.exit()`로 정상 종료해야 합니다.
- 새 프로세스를 띄울 때 현재 환경변수를 그대로 물려주면 안 됩니다 - PyInstaller
  onefile 부트로더가 내부적으로 심어두는 `_MEIPASS2` 등의 환경변수를 자식이
  그대로 물려받으면, 자식이 (곧 정리될 수도 있는) 부모의 임시 폴더를 자기 것으로
  착각해 `Failed to start embedded python interpreter. Failed to import
  encodings module` 오류로 죽습니다. `_MEIPASS`/`_PYI_`로 시작하는 환경변수를
  지운 사본을 만들어서 `subprocess.Popen(..., env=정리된_환경변수)`로 넘겨야
  합니다.

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

## 다국어 지원 (한국어/영어/일본어 완비, 상단 툴바에서 전환 가능)
화면에 보이는 모든 문자열(버튼/탭/메뉴/메시지박스/로그 메시지)은 코드에 직접
적혀있지 않고 `core/i18n.py`의 `t("키")`를 통해 `core/locales/{ko,en,ja}.json`에서
가져옵니다. 상단 툴바의 언어 콤보박스에서 고르면 `common_config`의
`settings.language`에 저장되고, 프로그램을 재시작하면 그 언어로 켜집니다
(재시작은 `App.restart_app()`이 자동으로 처리합니다).

**새 문자열을 추가할 때 반드시 지킬 것**: `TITLE = t("...")`처럼 클래스/모듈
레벨(즉 그 파일이 처음 import될 때 단 한 번만 실행되는 위치)에서 t()/t_field()
결과를 상수로 저장하면 안 됩니다 - import는 항상 `set_language()`보다 먼저
일어나므로, 그렇게 하면 언어를 아무리 바꾸고 재시작해도 그 값은 영원히 첫
언어(ko)로 고정됩니다. 항상 함수/메서드/`@property` 안에서, 실제로 쓰이는
시점에 평가하세요 (`tabs/*.py`의 `TITLE` property, `tabs/system_tab.py`의
`_type_label_map()` 참고).

새 언어를 추가하고 싶으면:
1. `core/locales/xx.json`을 기존 언어 파일과 **완전히 같은 키 구조**로 만들고
   번역문만 채웁니다. 코드는 건드릴 필요 없습니다.
2. 상단 툴바의 `LANGUAGE_OPTIONS` 목록(`auto ldb patcher.py`)에 `("xx", "표시이름")`을
   추가하면 콤보박스에 나타납니다.
3. 번역이 아직 없는 키는 자동으로 한국어(기본 언어)로, 그마저 없으면 키
   문자열 그대로 표시되므로 번역이 일부만 되어 있어도 프로그램이 깨지지
   않습니다.

⚠️ **`--add-data`로 `core/locales`를 반드시 exe에 포함시켜야 합니다** - 위
"배포용 단일 exe 빌드" 항목을 참고하세요. 빠뜨리면 모든 언어(한국어 포함)가
깨집니다.

옵션 이름/설명(System/Skill/Item/Actor/Class/Enemy/Terrain 탭의 필드 label·
description, 그리고 그룹명·enum 옵션 값)은 `core/config.py`,
`core/*_schema.py`에 한국어 텍스트로 직접 저장되어 있습니다(프로젝트
config.json에도 그대로 저장되는 값이라 키 체계로 완전히 바꾸는 건 호환성
위험이 있어 보류했습니다). 대신 표시하는 코드가 전부 번역 우선 조회를
거치도록 되어 있어서, 지금은 세 언어 모두 실제로 번역되어 있습니다:
- 필드 label/description: `core/property_panel.py`의 `render_field_row(...,
  namespace="item"/"skill"/"actor"/"class"/"enemy"/"terrain")` →
  `"<namespace>.<필드명>.label"` / `".description"` 키 조회
- 그룹명: `render_group_header()` → `"group.<원문>.label"` 키 조회 (여러
  스키마가 같은 그룹 이름을 재사용하므로 공유)
- enum 옵션 값: `"option.<원문>.label"` 키 조회 (역시 공유)
- 시스템 옵션(System 탭): `t_field("sys", 필드명, "name"/"description", ...)`

새 필드/옵션을 스키마에 추가하면 일단 한국어 원문 그대로는 모든 언어에서
동작하고(폴백), en/ja로도 보이게 하려면 위 규칙에 맞는 키를 `en.json`/
`ja.json`에 추가하기만 하면 됩니다 - 코드 수정은 필요 없습니다.


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
