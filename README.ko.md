# mosaic-headless

데이터 모델에 직접 기록해 Mosaic Pro(Nextend) WordPress 사이트를 만들고 수정합니다. 비주얼 에디터도 DOM 조작도 쓰지 않으며, 모든 조회에 실제 사이트에서 측정한 결과로 답합니다.

[![npm](https://img.shields.io/npm/v/mosaic-headless?style=flat-square)](https://www.npmjs.com/package/mosaic-headless)
[![License: MIT](https://img.shields.io/github/license/Moksa1123/mosaic-headless?style=flat-square)](LICENSE)

[English](README.md) · [正體中文](README.zh-TW.md) · [日本語](README.ja.md)

> 비공식 커뮤니티 프로젝트입니다. Mosaic Pro 개발사 Nextend가 만들거나 보증한 것이 아니며 Nextend와 관련이 없습니다. Mosaic Pro는 라이선스가 필요한 서드파티 소프트웨어로, 이 프로젝트에 포함되어 있지 않습니다.

## 기능

Mosaic는 페이지를 자체 데이터베이스 테이블에 요소 하나당 한 행으로 저장합니다(`post_content`가 아닙니다). 이 skill은 그 데이터 모델의 측정된 지도와, 그것을 통해 기록하는 도구입니다.

- **추측하지 말고 조회**: `tools/mo.py`가 node type, 속성, 스타일 키, 상태의 이름, 값의 형태, 놓을 수 있는 위치, 안전 여부를 알려 줍니다. 데이터는 134개 node type, 120개 node 속성, 101개 스타일 속성, 60개 스타일 상태를 다루며, Mosaic Pro 1.0.13에서 추출해 실제 사이트에서 하나씩 측정했습니다.
- **중국어와 구어도 조회 가능**: `mo.py css 內距`로 padding을 찾습니다. 용어는 Mosaic 자체의 정체 중국어(zh_TW) 표기를 따릅니다.
- **페이지와 사이트 구축**: `build_page.py`와 `build_site.py`는 Mosaic REST 쓰기 절차로 페이지 사양을 커밋하며, 페이지를 망가뜨리는 것으로 측정된 작성 방식은 거부합니다.
- **실제로 전달된 페이지 확인**: 검증 도구가 공개 페이지를 Chromium으로 읽습니다(반응형 규칙, 계산된 스타일, 메뉴, 대화상자, 슬라이더, 폼). 커밋 성공만 믿지 않습니다.
- **이전과 변환**: 테마 전체 내보내기/가져오기, Mosaic 데이터 업그레이드 실행, Elementor 페이지를 Mosaic로 변환.

## 사용 시점

사이트가 Mosaic Pro로 운영되고, 에디터를 열지 않고 페이지, 템플릿, 컴포넌트, 디자인 토큰, 팝업, 메뉴, 인터랙션을 만들거나 바꾸고 싶을 때, 또는 Mosaic 설정이 실제로 무엇을 하는지 정확히 알고 싶을 때 사용합니다.

다른 빌더에는 쓰지 않습니다. Elementor 페이지는 `elementor-headless`, 블록 에디터 페이지는 `gutenberg-headless`, SEO 글은 `rankmath-seo-wp`로. WordPress 사이트 상태 점검, 플러그인 업데이트, 보안 작업은 다루지 않습니다.

## 설치

Claude plugin(Claude Code. Claude 공식 디렉터리에 등록된 뒤에는 거기서도):

```
/plugin install mosaic-headless --marketplace Moksa1123/mosaic-headless
```

npx(Claude Code와 다른 AI 코딩 도구: Cursor, Codex CLI, Gemini CLI, Copilot, Continue, Windsurf, Claude.ai 업로드용 zip):

```bash
npx mosaic-headless@latest claude-code --global --force
npx mosaic-headless --list
```

수동 복사:

```bash
git clone https://github.com/Moksa1123/mosaic-headless.git
cp -r mosaic-headless ~/.claude/skills/mosaic-headless
```

요구 사항: Python 3(조회, 구축, 자체 테스트는 표준 라이브러리만 사용). 브라우저 검증 도구에는 Playwright(`requirements.txt`). `.php` 도구에는 서버의 WP-CLI. Node.js는 npx 설치 프로그램에만 필요합니다. Windows, macOS, Linux에서 동작합니다. npm 새 버전은 `--force`로 설치 프로그램을 다시 실행해야 반영됩니다.

## 빠른 시작

어시스턴트에게 이렇게 요청해 보세요:

- "내 Mosaic 사이트에 랜딩 섹션을 만들어 줘: H1, 문단, /contact/로 가는 버튼."
- "Mosaic의 accordion-content를 div 안에 바로 넣어도 돼?"
- "각 단계를 닫으면 다음으로 넘어가는 3단계 팝오버 투어를 추가해 줘."

직접 데이터를 조회할 수도 있습니다:

```bash
python tools/mo.py check div text accordion-content
```

```
type               outcome     why
-----------------  ----------  -----------------------------------------------
accordion-content  BROKE_PAGE  AccordionItemElementMResource instance required
```

종료 코드는 1입니다. 이 type을 단독으로 두면 커밋은 성공하지만 공개 페이지 전체가 오류 문자열로 바뀝니다. 어디에 넣어야 하는지는 `python tools/mo.py type accordion-content`가 알려 줍니다.

## 트리거 문구

English: Mosaic Pro, Nextend, build a Mosaic page without the editor, Mosaic padding / hover / breakpoint, Mosaic popup, popover, modal, Mosaic interaction, move a Mosaic theme, Mosaic upgrade, Elementor to Mosaic.

中文：Mosaic、Nextend、不開編輯器做頁面、內距、外距、圓角、懸停、斷點、RWD、彈出視窗、浮動框、摺疊面板、頁籤、輪播、互動、動畫、搬佈景、Mosaic 升級、Elementor 轉 Mosaic。

## 실행 및 연결 대상

- **스스로 실행되는 것은 없습니다.** hook, MCP 서버, 백그라운드 프로세스가 없습니다. Claude가 `SKILL.md`에 따라 명령을 제안하고 사용자가 승인할 때만 실행됩니다.
- **로컬 전용, 네트워크 없음**: `tools/mo.py`는 `data/`의 CSV를 읽어 답을 출력합니다. `tools/test_mosaic.py`와 `tools/check_numbers.py`는 이 저장소를 읽습니다. 아무것도 쓰거나 연결하지 않습니다.
- **REST API로 사용자의 WordPress 사이트에**: `build_page.py`, `build_site.py`, `data_upgrade.py`, `theme_zip.py`, `sweep_*.py`, `probe*.py`는 설정한 단 하나의 사이트의 Mosaic REST 경로를 호출해 페이지, 컴포넌트, 템플릿, 테마를 읽고 씁니다. 그 사이트에만 연결합니다.
- **WP-CLI로 사용자의 사이트에서 실행**: `tools/*.php`는 `wp eval-file`로 서버(보통 사용자 자신의 SSH)의 WordPress 안에서 실행되어 그 사이트의 Mosaic 테이블과 테마 데이터를 읽고 씁니다. `theme_delete.php`와 `prune_unbound.php`는 데이터를 삭제하므로 `--apply` 없이는 시험 실행만 합니다.
- **공개 페이지 읽기**: `tools/verify_*.py`와 `audit_mobile.py`는 같은 사이트의 페이지를 Playwright(Chromium) 또는 `urllib`로 열어, 전달된 결과와 기록한 내용을 비교합니다.
- **자격 증명**: 사이트 URL, WordPress 로그인 cookie, 그에 맞는 `wp_rest` nonce(사용자 자신의 사이트 관리자). `tools/mint_session.php`가 서버에서 이 값들을 출력합니다. plugin으로 설치하면 Claude Code가 `userConfig`로 물어보며, cookie와 nonce는 민감 정보로 표시되어 플랫폼의 자격 증명 저장소에 보관됩니다. 환경 변수(`MOSAIC_SITE_URL`, `MOSAIC_REST_COOKIE`, `MOSAIC_REST_NONCE`)나 `--config`로 넘기는 자신의 JSON 파일도 쓸 수 있습니다. **어떤 도구도 사용자의 컴퓨터에서 자격 증명을 찾지 않습니다.**
- **제3자**: `sites/`의 예제는 Google Fonts를 불러오므로, 그것으로 만든 페이지에서는 방문자의 브라우저가 Google에서 글꼴을 받아 옵니다.
- 설치할 때 아무것도 내려받지 않으며, 작성자나 다른 누구에게도 데이터를 보내지 않습니다.

## 검증 방법

- node type, node 속성, 스타일 속성, 스타일 상태는 플러그인 소스에서 추출하고(`tools/check_tables.py`가 다시 추출해 비교), 실제 사이트에 하나씩 기록해 전달된 HTML과 컴파일된 CSS로 확인합니다.
- 데모 페이지를 Chromium으로 다시 읽어, 733개 반응형 선언을 실제 전달된 스타일시트와 대조하고 세 가지 화면 폭에서 4,132개의 계산된 스타일을 확인했습니다. 자세한 내용: [verification-record.md](references/verification-record.md).
- 자체 테스트: `python tools/test_mosaic.py`, 오프라인 테스트 42개(조회, 중국어 용어, 구축 결과의 형태와 거부 규칙, 공개된 구축 인터페이스, 이 저장소의 숫자와 개인정보).
- evals: Mosaic 1.0.10~1.0.12 동작에 관한 16문항. skill 사용 시 16/16, 미사용 시 0/16. 결과: [evals/RESULTS.md](evals/RESULTS.md).
- `SKILL.md`와 이 README들의 숫자는 `tools/check_numbers.py`가 데이터와 대조합니다.

## 제한 사항

- Mosaic Pro 1.0.13까지 측정했습니다. 1.0.13 에디터에만 있는 기능(새 스타일 변수 유형, List 클래스, pageLoad 지연 등)은 아직 측정하지 않았고 도구도 기록하지 않습니다.
- 그리드 자식 배치 속성은 headless로 기록하면 출력되지 않습니다. 일부 인터랙션 형태는 아직 측정하지 않았습니다.
- 브라우저 검증 도구에는 Playwright와 기록 가능한 사이트가 필요하며, 오프라인 자체 테스트에는 포함되지 않습니다.
- 미해결 항목: [data/pending.csv](data/pending.csv). 상세 가이드(실패 모드, 토큰 비용, Elementor 변환기, 예제): [docs/guide.md](docs/guide.md)(영어).

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
