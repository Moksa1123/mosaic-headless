<h1 align="center">Mosaic Headless</h1>

<h3 align="center">Mosaic Pro 無編輯器建站工具</h3>

<p align="center">
  <strong>측정된 데이터 모델 · 보호 장치가 있는 페이지 빌더 · 전달된 페이지 검증</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3">
  <img src="https://img.shields.io/badge/node-18_or_later-green?style=flat-square&logo=node.js&logoColor=white" alt="Node.js 18 이상">
  <img src="https://img.shields.io/badge/playwright-browser_verifiers-blueviolet?style=flat-square" alt="브라우저 검증에 Playwright">
  <img src="https://img.shields.io/badge/WP--CLI-server_scripts-blue?style=flat-square&logo=wordpress&logoColor=white" alt="서버 스크립트에 WP-CLI">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/node_types-134-success?style=flat-square" alt="134개 node type">
  <img src="https://img.shields.io/badge/node_properties-120-success?style=flat-square" alt="120개 node 속성">
  <img src="https://img.shields.io/badge/style_properties-101-success?style=flat-square" alt="101개 스타일 속성">
  <img src="https://img.shields.io/badge/responsive_checks-733-blueviolet?style=flat-square" alt="733개 반응형 검사">
  <img src="https://img.shields.io/badge/self--tests-55-blueviolet?style=flat-square" alt="55개 자체 테스트">
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/mosaic-headless"><img src="https://img.shields.io/npm/v/mosaic-headless?style=flat-square&logo=npm" alt="npm 버전"></a>
  <a href="https://www.npmjs.com/package/mosaic-headless"><img src="https://img.shields.io/npm/dt/mosaic-headless?style=flat-square&label=downloads&color=cb3837" alt="npm 다운로드 수"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Moksa1123/mosaic-headless?style=flat-square" alt="License"></a>
</p>

<p align="center"><a href="README.md">English</a> · <a href="README.zh-TW.md">正體中文</a> · <a href="README.ja.md">日本語</a> · <strong>한국어</strong></p>

> 비공식 커뮤니티 프로젝트입니다. Mosaic Pro 개발사 Nextend가 만들거나 보증한 것이 아니며 Nextend와 관련이 없습니다. Mosaic Pro는 라이선스가 필요한 서드파티 소프트웨어로, 이 프로젝트에 포함되어 있지 않습니다.

## 기능

Mosaic는 페이지를 자체 데이터베이스 테이블에 요소 하나당 한 행으로 저장합니다(`post_content`가 아닙니다). 이 skill은 그 데이터 모델의 측정된 지도와, 그것을 통해 기록하는 도구입니다. 데이터는 Mosaic Pro 1.0.13에서 추출해 실제 사이트에서 하나씩 측정했습니다.

| 분야 | 내용 |
|---|---|
| 조회 | `tools/mo.py`: 134개 node type, 120개 node 속성, 101개 스타일 속성, 60개 스타일 상태. 각각 측정 결과와 함께 답합니다. 중국어와 구어로도 조회할 수 있습니다(`mo.py css 內距`) |
| 구축 | `build_page.py`/`build_site.py`는 Mosaic REST 쓰기 절차로 페이지 사양을 커밋하며, 페이지를 망가뜨리는 것으로 측정된 작성 방식은 거부합니다 |
| 검증 | 전달된 페이지를 Chromium으로 읽습니다: 반응형 규칙, 계산된 스타일, 메뉴, 대화상자, 슬라이더, 폼 |
| 이전 | 테마 전체 내보내기/가져오기, wp-admin 밖에서 Mosaic 데이터 업그레이드 실행 |
| 변환 | Elementor 페이지를 Mosaic 사양으로 변환하고, 변환하지 못한 요소는 모두 이름을 밝힙니다 |

### 쓰기 전에 조회

```bash
python tools/mo.py type accordion-content   # one type, joined to every live sweep
python tools/mo.py css 內距                  # Chinese works: padding-top/right/bottom/left
python tools/mo.py facts section padding     # measured front-end behaviour
```

### 보호 장치를 거쳐 구축

```bash
python tools/mo.py skeleton > page.json
python tools/build_page.py --spec page.json   # refuses unsafe types, bad placement, out-of-enum values
```

### 방문자가 받는 페이지 확인

```bash
python tools/verify_rwd.py --site page.json       # every _t/_m declaration in the served stylesheet
python tools/verify_browser.py --site page.json   # what Chromium computes, plus a design audit
```

## 사용 시점

사이트가 Mosaic Pro로 운영되고, 에디터를 열지 않고 페이지, 템플릿, 컴포넌트, 디자인 토큰, 팝업, 메뉴, 인터랙션을 만들거나 바꾸고 싶을 때, 또는 Mosaic 설정이 실제로 무엇을 하는지 정확히 알고 싶을 때 사용합니다.

| 요청 | 담당 |
|---|---|
| Elementor 페이지 | `elementor-headless` |
| 블록 에디터(Gutenberg) 페이지 | `gutenberg-headless` |
| SEO 글, Rank Math 점수 | `rankmath-seo-wp` |
| 사이트 상태 점검, 플러그인 업데이트, 보안 | 범위 밖 |

## 설치

### Step 1: 설치 방법 선택

Claude plugin(Claude Code. Claude 공식 디렉터리에 등록된 뒤에는 거기서도):

```
/plugin install mosaic-headless --marketplace Moksa1123/mosaic-headless
```

npx(Claude Code와 다른 AI 코딩 도구):

```bash
npx mosaic-headless@latest claude-code --global --force
npx mosaic-headless --list
```

수동 복사:

```bash
git clone https://github.com/Moksa1123/mosaic-headless.git
cp -r mosaic-headless ~/.claude/skills/mosaic-headless
```

| 플랫폼 | 설치 내용 | 위치 |
|---|---|---|
| Claude Code | skill 전체: SKILL.md, references, tools, data, sites, evals, scripts | `~/.claude/skills/` 또는 `./.claude/skills/` |
| Codex CLI | skill 전체 | `~/.codex/skills/` |
| Gemini CLI | skill 전체 | `~/.gemini/skills/` |
| GitHub Copilot | skill 전체 | `./.github/skills/` |
| Cursor | references를 포함한 `.mdc` 규칙 1개 | `~/.cursor/rules/` |
| Windsurf | references를 포함한 규칙 파일 1개 | `./.devin/rules/` |
| Continue | references를 포함한 규칙 파일 1개 | `~/.continue/rules/` |
| Claude.ai | 업로드용 zip(SKILL.md, references, data, sites. 도구 없음) | 저장한 위치 |

요구 사항: Python 3(조회, 구축, 자체 테스트는 표준 라이브러리만 사용). 브라우저 검증 도구에는 Playwright(`requirements.txt`). `.php` 도구에는 서버의 WP-CLI. npx 설치 프로그램에만 Node.js 18 이상이 필요합니다. Windows, macOS, Linux에서 동작합니다. npm 새 버전은 `--force`로 설치 프로그램을 다시 실행해야 반영됩니다.

## 빠른 시작

### Step 2: 데이터 조회

```bash
python tools/mo.py check div text accordion-content
```

```
type               outcome     why
-----------------  ----------  -----------------------------------------------
accordion-content  BROKE_PAGE  AccordionItemElementMResource instance required
```

종료 코드는 1입니다. 이 type을 단독으로 두면 커밋은 성공하지만 공개 페이지 전체가 오류 문자열로 바뀝니다. 어디에 넣어야 하는지는 `python tools/mo.py type accordion-content`가 알려 줍니다.

### Step 3: 어시스턴트에게 요청

- "내 Mosaic 사이트에 랜딩 섹션을 만들어 줘: H1, 문단, /contact/로 가는 버튼."
- "Mosaic의 accordion-content를 div 안에 바로 넣어도 돼?"
- "각 단계를 닫으면 다음으로 넘어가는 3단계 팝오버 투어를 추가해 줘."

## 트리거 문구

English: Mosaic Pro, Nextend, build a Mosaic page without the editor, Mosaic padding / hover / breakpoint, Mosaic popup, popover, modal, Mosaic interaction, move a Mosaic theme, Mosaic upgrade, Elementor to Mosaic.

中文：Mosaic、Nextend、不開編輯器做頁面、內距、外距、圓角、懸停、斷點、RWD、彈出視窗、浮動框、摺疊面板、頁籤、輪播、互動、動畫、搬佈景、Mosaic 升級、Elementor 轉 Mosaic。

## 실행 및 연결 대상

- **스스로 실행되는 것은 없습니다.** hook, MCP 서버, 백그라운드 프로세스가 없습니다. Claude가 `SKILL.md`에 따라 명령을 제안하고 사용자가 승인할 때만 실행됩니다.
- **로컬 전용, 네트워크 없음**: `tools/mo.py`는 `data/`의 CSV를 읽어 답을 출력합니다. `tools/test_mosaic.py`와 `tools/check_numbers.py`는 이 저장소를 읽습니다. 아무것도 쓰거나 연결하지 않습니다.
- **REST API로 사용자의 WordPress 사이트에**: `build_page.py`, `build_site.py`, `data_upgrade.py`, `theme_zip.py`, `sweep_*.py`, `probe*.py`는 설정한 단 하나의 사이트의 Mosaic REST 경로를 호출해 페이지, 컴포넌트, 템플릿, 테마를 읽고 씁니다. 그 사이트에만 연결합니다.
- **WP-CLI로 사용자의 사이트에서 실행**: `tools/*.php`는 `wp eval-file`로 서버(보통 사용자 자신의 SSH)의 WordPress 안에서 실행되어 그 사이트의 Mosaic 테이블과 테마 데이터를 읽고 씁니다. `prune_unbound.php`는 데이터를 삭제하므로 `apply`라는 단어(`--apply`가 아님) 없이는 시험 실행만 합니다. `theme_delete.php`는 지정한 테마를 삭제하며, 사용 중인 테마는 삭제하지 않습니다.
- **공개 페이지 읽기**: `tools/verify_*.py`와 `audit_mobile.py`는 같은 사이트의 페이지를 Playwright(Chromium) 또는 `urllib`로 열어, 전달된 결과와 기록한 내용을 비교합니다.
- **자격 증명**: 사이트 URL, WordPress 로그인 cookie, 그에 맞는 `wp_rest` nonce(사용자 자신의 사이트 관리자). `tools/mint_session.php`가 서버에서 이 값들을 출력합니다. plugin으로 설치하면 Claude Code가 `userConfig`로 물어보며, cookie와 nonce는 민감 정보로 표시되어 플랫폼의 자격 증명 저장소에 보관됩니다. 환경 변수(`MOSAIC_SITE_URL`, `MOSAIC_REST_COOKIE`, `MOSAIC_REST_NONCE`)나 `--config`로 넘기는 자신의 JSON 파일도 쓸 수 있습니다. **어떤 도구도 사용자의 컴퓨터에서 자격 증명을 찾지 않습니다.**
- **제3자**: `sites/`의 예제는 Google Fonts를 불러오므로, 그것으로 만든 페이지에서는 방문자의 브라우저가 Google에서 글꼴을 받아 옵니다.
- 설치할 때 아무것도 내려받지 않으며, 작성자나 다른 누구에게도 데이터를 보내지 않습니다.

| 도구 | 하는 일 | 접근 대상 |
|---|---|---|
| `mo.py` | 측정 데이터 조회, 진입점 | 로컬 `data/`만 |
| `build_page.py` / `build_site.py` | 보호 장치가 있는 쓰기 절차로 사양 커밋 | 사용자의 사이트(REST) |
| `from_elementor.py` / `verify_conversion.py` | Elementor를 Mosaic로 변환하고 내용이 옮겨졌는지 확인 | 로컬 파일/사용자의 사이트 |
| `verify_rwd.py`, `verify_browser.py`, `verify_*.py` | 전달된 페이지를 Chromium으로 읽기 | 사용자의 사이트(읽기) |
| `theme_zip.py`, `theme_export.php` / `theme_import.php` | 테마 전체 이전 | 사용자의 사이트(REST/WP-CLI) |
| `sync_nodes.py` + `list_bindings.php` | 구축된 사이트를 제자리에서 갱신: 바뀐 노드만 기존 master 그대로 수정. `--apply` 없이는 미리보기만 | 사용자의 사이트(REST. 연결 관계는 WP-CLI로 읽기) |
| `data_upgrade.py` | 플러그인 업데이트 후 Mosaic 데이터 마이그레이션 실행 | 사용자의 사이트(REST) |
| `scan_inline_tags.py` / `fix_inline_tags.py` | 1.0.11+에서 HTML 태그가 그대로 보이는 텍스트를 찾아 수정 | 사용자의 사이트(REST) |
| `test_mosaic.py`, `check_numbers.py` | 자체 테스트와 숫자 검사 | 이 저장소 |

## 검증 방법

node type, node 속성, 스타일 속성, 스타일 상태는 플러그인 소스에서 추출하고(`tools/check_tables.py`가 다시 추출해 비교), 실제 사이트에 하나씩 기록해 전달된 HTML과 컴파일된 CSS로 확인합니다. 아래 표는 모두 `data/`에 있으며, 행 수는 `tools/check_numbers.py`가 대조합니다.

| 테이블 | 행 수 | 확인한 내용 |
|---|---:|---|
| `data/node-verification.csv` | 134 | 모든 node type을 단독으로 커밋하고 공개 페이지에서 다시 읽기 |
| `data/style-verification.csv` | 101 | 모든 스타일 속성을 컴파일된 CSS와 대조 |
| `data/node-property-verification.csv` | 191 | 각 node 속성을 해당 검증기가 받아들이는 값으로 검사 |
| `data/style-state-verification.csv` | 59 | 각 상태를 생성해야 할 선택자와 대조 |
| `data/rwd-verification.csv` | 733 | 모든 `_t` / `_m` 선언을 실제 전달된 스타일시트와 대조 |
| `data/browser-verification/` | 4,132 | 세 가지 화면 폭에서 Chromium이 계산한 스타일 |
| `data/popover-verification.csv` | 37 | 팝오버: 배치, 닫기, 뒤집기, 연결된 투어 |
| `data/menu-verification.csv` | 34 | 호버 드롭다운과 모바일 메뉴를 마우스, 키보드, 터치로 조작 |
| `data/form-surface-verification.csv` | 23 | 모든 폼 필드(조립식 Select 포함) |
| `data/custom-fields-verification.csv` | 62 | ACF와 Meta Box 필드를 `@VAR` / `@LOOP`로 읽기 |
| `data/theme-zip-verification.csv` | 22 | Mosaic 자체 테마 ZIP을 왕복시켜 비교 |
| `data/conversion-batch.csv` | 19 | 한 사이트의 모든 Elementor 페이지를 변환, 구축, 검사 |

- 자체 테스트: `python tools/test_mosaic.py`, 오프라인 테스트 55개(조회, 중국어 용어, 구축 결과의 형태와 거부 규칙, 공개된 구축 인터페이스, 이 저장소의 숫자와 개인정보).
- evals: Mosaic 1.0.10~1.0.12 동작에 관한 16문항. skill 사용 시 16/16, 미사용 시 0/16. 결과: [evals/RESULTS.md](evals/RESULTS.md).
- `SKILL.md`, 이 README들, 배지의 숫자는 `tools/check_numbers.py`가 데이터와 대조합니다. 자세한 내용: [verification-record.md](references/verification-record.md).

조회 1회에 드는 토큰: 같은 6가지 작업을 tiktoken으로 계산(`data/token-benchmark.csv`, 테이블을 만들 때 측정. `tools/benchmark_tokens.py`로 재현 가능). 테이블을 통째로 읽지 말고 조회하세요.

| `mo.py` 명령 | 소스 읽기 | 전체 테이블 읽기 | 조회 |
|---|---:|---:|---:|
| `params text ; params button ; prop url` | 10,005 | 259,539 | **961** |
| `style --grouped ; css border-left-width ; css border-radius` | 3,490 | 259,539 | **396** |
| `type accordion-content ; placement accordion-item` | 15,615 | 259,539 | **397** |
| `states --verified` | 3,619 | 259,539 | **1,054** |
| `css grid-column` | 1,862 | 259,539 | **51** |
| `stats ; check div text button accordion-content` | 63,172 | 259,539 | **288** |

## 제한 사항

- Mosaic Pro 1.0.13까지 측정했습니다. 1.0.13 에디터에만 있는 기능(새 스타일 변수 유형, List 클래스, pageLoad 지연 등)은 아직 측정하지 않았고 도구도 기록하지 않습니다.
- 그리드 자식 배치 속성은 headless로 기록하면 출력되지 않습니다. 일부 인터랙션 형태는 아직 측정하지 않았습니다.
- 브라우저 검증 도구에는 Playwright와 기록 가능한 사이트가 필요하며, 오프라인 자체 테스트에는 포함되지 않습니다.
- 미해결 항목: [data/pending.csv](data/pending.csv). 상세 가이드(실패 모드, Elementor 변환기, 예제): [docs/guide.md](docs/guide.md)(영어).

## 저장소 구조

```
SKILL.md          어시스턴트가 불러오는 내용: 출처, 라우팅, 작업, 검증
data/             측정된 테이블(CSV), 중국어 용어, 미해결 목록
references/       주제별 가이드: 데이터 모델, 스타일, 대화상자, 업그레이드…
tools/            mo.py, 구축·검증 도구, WP-CLI 스크립트, 자체 테스트
sites/            예제(읽을 수 있는 Python 모듈)
evals/            채점 문항과 결과
scripts/          설치 프로그램과 릴리스 게이트
assets/           플랫폼별 설치 템플릿
docs/             상세 가이드
.claude-plugin/   plugin과 marketplace 매니페스트
```

## 라이선스와 작성자

MIT License. 작성자 Moksa([moksaweb.com](https://moksaweb.com)). 문의: [GitHub](https://github.com/Moksa1123/mosaic-headless/issues).
