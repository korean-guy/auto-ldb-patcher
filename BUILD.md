# 빌드 안내 (개발 → 단일 exe 배포)

## 폴더 구조
```
auto ldb patcher.py
core/
    __init__.py
    utils.py     # 경로/문자열/ini파싱/스키마 변환 등 순수 유틸
    theme.py     # 다크 테마 색상 + 위젯 생성 헬퍼
    config.py    # JSON 읽기/쓰기, 공통·프로젝트 config 관리, 게임 폴더 선택
    lcf.py       # lcf2xml 실행, edb 파싱, 최종 패치(edb→ldb)
tabs/
    __init__.py
    item_tab.py
    skill_tab.py
    system_tab.py
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
- `--windowed` : 실행 시 콘솔 창이 뜨지 않습니다.
- 빌드 결과물은 `dist/EasyRPG DB Editor.exe` 에 생성됩니다.

## 배포 시 폴더 구성
exe만 배포하지 않고, **exe와 같은 폴더에 lcf2xml.exe를 함께 넣어야 합니다** (프로그램이
런타임에 `lcf2xml.exe`를 실행 파일과 같은 폴더에서 찾습니다 - `core/utils.py`의
`get_program_dir()`가 PyInstaller onefile 실행 시 `sys.executable`의 위치를 반환합니다).
```
배포 폴더/
    EasyRPG DB Editor.exe
    lcf2xml.exe
```
`config.json`과 `projects/` 폴더는 최초 실행 시 exe 폴더에 자동으로 생성되므로 미리
준비할 필요가 없습니다.

## 새 탭 추가 방법
1. `tabs/새탭.py` 파일을 만들고, `build(self, notebook)`와 `refresh(self)`를 구현하는
   클래스를 작성합니다 (`tabs/item_tab.py`를 참고하면 가장 빠릅니다).
2. `auto ldb patcher.py` 상단의 `TAB_CLASSES` 목록에 새 클래스를 한 줄 추가합니다.
   ```python
   from tabs.monster_tab import MonsterTab
   TAB_CLASSES = [ItemTab, SkillTab, SystemTab, MonsterTab]
   ```
메인 파일은 이 두 줄 외에는 수정할 필요가 없습니다.
