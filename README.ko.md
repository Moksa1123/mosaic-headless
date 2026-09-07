# mosaic-headless

[Mosaic Pro](https://mosaicbuilder.com)(Nextend) 사이트를 데이터 모델에 직접 써서
구축하고 수정한다 — 비주얼 에디터도, DOM도 쓰지 않는다.

*다른 언어: [English](README.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md)*

---

Mosaic은 페이지를 **23개의 커스텀 테이블**에 보관한다. `post_content`도 아니고
`postmeta`도 아니다. 요소 하나당 한 행, 트리 구조는 `parentID` 컬럼, 형제 순서는
fractional-index 문자열이다. 에디터는 이 모델의 한 클라이언트일 뿐이다.
포맷 그 자체가 아니며, 반드시 쓸 필요도 없다.

이 skill은 그 모델의 지도이며, **소스를 읽은 것이 아니라 실제 설치본을 상대로
측정한 것**이다.

## 모든 것에 우선하는 단 하나의 규칙

**노드 타입, 속성 이름, 열거값, 스타일 키, Free/Pro 판단을 기억으로 쓰지 말 것.
`data/`에서 찾아볼 것.**

그리고 grep이 아니라 `mo.py`로 찾을 것. grep은 입력한 질문에 답할 뿐, 실제로 품고 있는
질문에는 답하지 않는다. `accordion-content`를 grep하면 그 타입이 존재한다는 것은 알 수
있지만, 그것을 배치하면 commit은 깨끗하게 통과하고 그다음 공개 페이지 전체가 54바이트
에러 문자열이 된다는 사실은 알려주지 않는다.

```bash
python tools/mo.py type accordion-content   # 타입 하나를 모든 라이브 스윕과 연결해 출력
python tools/mo.py check div text button    # 위험하거나 존재하지 않는 타입이면 exit 1
python tools/mo.py style --grouped          # 단독으로 설정하면 반드시 무효인 20개
python tools/mo.py states --verified        # 실측으로 컴파일이 확인된 상태만
```

그리고 페이지를 확인한다. Mosaic의 실패 방식은 네 가지이고,
**그중 HTTP 상태 코드가 바뀌는 것은 하나뿐이다**:

```
검증기의 정상적인 거부      HTTP 200  + body에 exceptions 배열
commit 중 PHP fatal         HTTP 500  (122개 타입 중 15개, 맨 div 안에서도 발생)
구조적으로 잘못된 노드      HTTP 200, 커밋됨, DB에 행도 있음. 그리고
                            공개 페이지 전체가 54바이트 에러 문자열이 된다
값의 "모양"이 틀림          HTTP 200, 저장됨. 다만 CSS 규칙이 존재하지 않는다
규칙은 맞는데 결과가 다름   HTTP 200, 스타일시트에 있고 내용도 맞다. 그런데 브라우저가
                            계산해내는 값은 다른 것이다
URL에 맞는 템플릿 없음      HTTP 406, 로그인하지 않은 사용자에게는 빈 body
```

**commit 성공도, 올바른 스타일시트도 페이지가 동작한다는 증거가 아니다.**

## 무엇을, 어떻게 검증했는가

전부 실제 설치본에서 실행 — WordPress 7.1, WooCommerce 11.1, Mosaic Pro 1.0.7,
**라이선스 없음**: 라이선스가 제한하는 것은 테마 라이브러리와 업데이트이지
노드 팩토리가 아니므로 Pro 타입도 등록되고 렌더링된다.

| 항목 | 결과 |
|---|---|
| **노드 타입** | 122 / 122. 문서 하나당 타입 하나로 commit → 렌더 → 단언 → 삭제. 70 RENDERED, 30 COMMITTED, 15 COMMIT_5xx, 7 BROKE_PAGE |
| **스타일 속성** | 98 / 98을 실제 페이지에 쓰고 컴파일된 CSS와 대조: 58 COMPILED, 18 ABSENT, 21 SKIPPED |
| **노드 속성** | 181 / 181을 각 속성 자신의 validator chain에서 도출한 값으로 재측정: 35 APPLIED, 42 NO_EFFECT, 55 NO_HOST, 47 SKIPPED |
| **반응형** | 두 사이트 합쳐 667개의 `_t`/`_m` 선언을, 사이트가 실제로 내보낸 스타일시트에 대해 하나씩 단언 — 전부 검증됨 |
| **스타일 상태** | 53개 상태 중 52개를 실제 페이지에 쓰고 표가 약속한 셀렉터와 대조: **36개가 정확히 일치**, 12개 NO_HOST, 3개 SKIPPED, 1개 BROKE_PAGE. 어떤 요소에나 쓸 수 있는 전역 7개 상태는 전부 검증됨 |
| **인터랙션** | JS 애니메이션 경로를 음성 대조군과 함께, 저장된 행을 되읽으며 검증: `propertyMetas`는 **수용되고 저장된다**. 속성 값은 여전히 바인딩되지 않지만 그 경계는 이제 정확하다 |
| **인트로 애니메이션** | 페이지 로드 후 10개 시점을 샘플링해 7가지를 단언 — 재생될 것, 애니메이션되는 `@property` 카운터가 100에 도달할 것, 베일이 히트 테스트에서 빠질 것, 뷰포트 안에 opacity 0으로 갇힌 요소가 없을 것, 실제 클릭이 문서에 닿을 것, 그리고 `prefers-reduced-motion`에서는 베일이 아예 존재하지 않을 것 |
| **브라우저** | 전달된 페이지를 Chromium의 세 가지 뷰포트에서 계산 스타일 3,277건 판독: 2,551건 일치, 726건은 비교 불가로 명시, **덮어쓰기 0건** |
| **디자인 감사** | 명암비, 폰트 폴백, CJK 자간, 가로 넘침, 텍스트 잘림, 한 줄 글자 수 — 브라우저에서 실행, **지적 0건** |
| **테마 내보내기/가져오기** | 왕복 검증: 테마 전체를 내보내 사본으로 가져왔고, 사본이 바이트 단위로 동일한 페이지를 제공 |
| **실측** | REST 라우트 114개, element class 151개, 조건 주체 59개, 23개 테이블 / 206개 컬럼 |

`SKIPPED`, `NO_HOST`, `INCONCLUSIVE`를 합격률에 섞는 일은 결코 없다.
**자신의 사각지대를 성공으로 세는 스윕이야말로 이 skill이 반대하는 것이다.**

### 쓰기 시작하기 전에 알아둘 가치가 있는 두 가지 결과

**`group`을 가진 속성은 단독으로 설정하면 동작하지 않는다.** 양방향 모두 정확하다:
group이 없는 78개는 58 COMPILED / 0 ABSENT, group이 있는 20개는 전부 0 COMPILED.
즉 `borderLeftWidth`, `outlineColor`, `gridColumnStart`는 서로 다른 세 개의 기벽이
아니라 **하나의 규칙의 세 가지 사례**다. 그룹 형태를 쓰거나(`border`는
`{width, style, color}`를 받는다) `customStyles`로 내려간다.

**브레이크포인트 오버라이드는 속성을 "바꿀" 수는 있어도 "없앨" 수는 없다.**
좁은 화면의 `customStyles`가 단지 테두리를 쓰지 않았을 뿐이라면 넓은 화면의 테두리는
살아남아, 한 칼럼으로 접힌 레이아웃 한가운데에 선을 긋는다.
**`border-left:0`이라고 명시적으로 말해야 한다.**

## 도구

```bash
wp eval-file tools/bootstrap_probe_theme.php          # 라이선스 없이 쓰는 작업용 테마
python tools/build_site.py   --config c.json --site sites/moksa.json
python tools/verify_rwd.py   --config c.json --site sites/moksa.json --csv rwd.csv
python tools/copy_styles.py  --config c.json --from a --to-prefix b- --only "&._m"
wp eval-file tools/theme_export.php active > theme.json
wp eval-file tools/theme_import.php theme.json "이름" rebind activate
```

`sites/_moksa.py`가 완전한 예제다. 실재하는 스튜디오의 홈페이지 — 머리기사, 사양 블록,
서비스, 9행짜리 작업 테이블, 프로세스, 기술 스택, 제품, 고객 추천사, 연락처 —
**618개의 노드를 전부 테이블을 통해 commit**했고, 이름 붙인 view timeline으로 만든
스크롤 추적 조항 인덱스까지 JavaScript는 한 줄도 쓰지 않았다.

## 어디부터 읽을 것인가

1. `references/data-model.md` — 페이지가 실제로 어디에 있는가.
2. `references/write-protocol.md` — checkout / check / commit.
3. `references/failure-modes.md` — Mosaic이 깨지는 방식, 전부 실측. **쓰기 전에 읽을 것.**
4. `references/responsive.md` — state / breakpoint / property 축.
5. `references/styling.md` — 스타일 값이 CSS가 되기까지.
6. `references/design-system.md` — element class와 디자인 토큰.

## 라이선스

MIT. Mosaic Pro 자체는 라이선스가 있는 서드파티 소프트웨어이며 이 repo에
**포함되어 있지 않다**.
