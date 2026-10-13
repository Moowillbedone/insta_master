# 실사 이미지 제작 매뉴얼

- 기준일: 2026-10-13 (KST)
- 한 줄 요약: **프롬프트는 키트가 만들고, 생성은 ChatGPT 앱(기본) 또는 API로, 승인은 사람이 한다. 얼굴은 기준 사진에서, 글자는 렌더러에서.**
- 이 문서는 제작 순서, 승인 기준, 파일·상태, 비용, 기록을 다룬다. 프롬프트 쓰는 법과 고치는 문장은 [brand/prompt-guide.md](../brand/prompt-guide.md)에 있다.

**신뢰도 표시**: [확인] 공식 출처 · [보도] 언론 · [주장] 업체·블로그 · [미확인] 확인 못 함 · (해석) 리서치의 판단 · (운영 규칙) 우리가 정한 규칙 · (가정) 계산용 가정 · (확인 필요) 리서치에 없음, 맨 아래 목록

**근거 문서**: [research/ig-platform.md](research/ig-platform.md) · [research/kr-compliance.md](research/kr-compliance.md) · [research/sponsorship-kr.md](research/sponsorship-kr.md) · [00-master-plan.md](00-master-plan.md) §3, §4 · [brand/doha.yaml](../brand/doha.yaml) · [brand/prompt-guide.md](../brand/prompt-guide.md) · [brand/reference/README.md](../brand/reference/README.md) · [config.yaml](../config.yaml) · [content/SCHEMA.md](../content/SCHEMA.md)

---

## 0. 한눈에 보기

```text
post.yaml  images.sNN (outfit · prompt · framing)
   │
   │  python doha.py prompts <게시물>              → out/prompts.md
   ├─ (기본) ChatGPT 앱 + 얼굴 기준 사진 첨부      → images/sNN.png   status: generated (손으로)
   └─ (선택) python doha.py generate <게시물> …    → images/sNN.png   status: generated (자동) + costs.csv
   │
   사람 QA (§3) ── 통과 → approved
   │            └─ 실패 → 고치기 / rejected (§4)
   │
   python doha.py check → render → reel → preview    (한 번에: build)
   │
   휴대폰 미리보기 → review.approved_by → 앱에서 게시 (AI 정보 라벨 · 음원 · 대체 텍스트)
```

**원칙** (근거: 00-master-plan.md §3, §4)

- 사진에 글자를 그리지 않는다. 제목·라벨·광고 표시·'AI 가상인물' 배지는 렌더러가 얹는다.
- 자동으로 공개하지 않는다. 사람이 승인한 파일만 게시한다.
- "멋져 보이는가"와 "사진처럼 설득력 있는가"는 따로 검수한다.

---

## 1. 게시물 1건 제작 순서

| # | 단계 | 할 일 | 명령 | 결과 | 게시물 `status` |
|---|---|---|---|---|---|
| 0 | 준비 | 얼굴 기준 사진이 `face_reference`에 있는지 확인. 없으면 §2-1 먼저 | — | — | — |
| 1 | 기획 | 뼈대를 만들고 hook·slides·reel 채우기 | `python doha.py new "주제" --date YYYY-MM-DD --series "…"` | `post.yaml`, `images/` | draft |
| 2 | 사진 묘사 | `images.<키>`에 `outfit`(소재·색·핏·여밈), `prompt`(영어, 장면만), `framing` | 편집기 | — | draft |
| 3 | 프롬프트 | 붙여넣을 프롬프트 만들기 | `python doha.py prompts <게시물>` (`--only s01,s02`) | `out/prompts.md` | — |
| 4a | 생성 (기본) | ChatGPT 앱: 이미지마다 새 채팅, 기준 사진 첨부, 블록 붙여넣기, 원본 파일 저장 | — | `images/sNN.png` | 사진별 `generated` (직접) |
| 4b | 생성 (선택) | API: 미리보기 → 한 장씩 → `y` 확인 | `python doha.py generate <게시물> --only s01 --dry-run` → `--dry-run` 빼고 실행 | `images/sNN.png`, `tracking/costs.csv` 한 줄 | 사진별 `generated` (자동) |
| 5 | QA | §3 체크리스트. 원본 크기로 확대 | — | — | 사진별 `approved` / `rejected` (사람) |
| 6 | 사진 완료 | 쓰는 사진이 모두 `approved` | — | — | images |
| 7 | 검수 | 오류 0이 될 때까지 | `python doha.py check <게시물>` | 터미널 리포트 | — |
| 8 | 렌더 | 카드뉴스·릴스 만들기 | `render`, `reel` (또는 `build`) | `out/slides/NN.png`, `out/reel/reel.mp4`, `cover.png` | rendered |
| 9 | 미리보기 | 휴대폰 크기로 확인 | `python doha.py preview <게시물>` | `contact-sheet.png`, `preview.html`, `caption.txt` | reviewed |
| 10 | 승인 | `review.approved_by`, `approved_at` 기록 | — | — | approved |
| 11 | 게시 | 앱에서. 'AI 정보' 라벨, 릴스 음원, 대체 텍스트, (협찬) 유료 파트너십 라벨 | — | `posted.url`, `posted_at` | posted |

- 사진이 아직 없어도 `render`는 자리표시 이미지로 배치를 보여 준다. 글자 자리를 먼저 확인할 수 있다.
- `build --force`는 검수 오류가 있어도 시안을 만든다. **게시 금지.**
- 게시물마다 제작 시간과 후보 수를 `review.notes`에 적는다 (예: `제작 3.0h · 후보 14장`). 견적 변수 `H`, `n_img`의 근거가 된다. (근거: 01-monetization-playbook.md §6)
- 게시 상태 단계(`images`·`rendered`·`reviewed`)를 언제 바꾸는지는 이 문서의 기준이다. (운영 규칙, 상태 이름: content/SCHEMA.md)

---

## 2. 얼굴 일관성

### 2-1. 처음 한 번: 얼굴 기준 사진 승인

순서는 brand/reference/README.md를 따른다.

1. `python doha.py prompts --reference` → 기준 사진용 프롬프트 3개 (정면 01, 3/4 02, 상반신 03).
2. ChatGPT 앱 새 채팅에 **정면(01)**을 붙여넣고, 3~5번 다시 만들어 후보를 모은다.
3. brand/reference/README.md의 체크리스트를 통과한 한 장을 `brand/reference/doha-face-01.png`로 저장한다.
4. **3/4(02)**, **상반신(03)**은 01을 첨부하고 프롬프트 앞에 `Same person as the attached photo.`를 붙여 만든다.
5. **역이미지 검색**으로 닮은 실존 인물이 없는지 본다. 날짜·도구·결과 화면을 보관한다. (해석) (근거: research/kr-compliance.md §5-1, 04-compliance-checklist.md §8-2)
6. `brand/doha.yaml`의 `visual.face_reference`에 경로를 넣는다. brand/reference/README.md 승인 기록 표를 채운다.
7. 연결 확인: `python doha.py prompts <게시물>`의 '첨부' 항목에 파일이 나오고, `python doha.py generate <게시물> --dry-run`에 `edit + 기준 3장`이 보이면 된다.

**지킬 것**

- 기준 사진은 **AI로 만든 도하 이미지만** 쓴다. 연예인·모델·지인·본인 사진, 얼굴 합성, 실존 인물로 학습한 모델(LoRA 등)은 쓰지 않는다. (해석) (근거: research/kr-compliance.md §5-1)
- 2~3장이면 충분하다. 많을수록 API 입력 비용이 는다 (키트는 1장당 $0.01을 예상치에 더함).
- 한번 정한 세트는 바꾸지 않는다. 꼭 바꿔야 하면 새 번호로 추가하고, 이전 파일은 지우지 않고 목록에서만 뺀다.
- 게시물용 사진을 승인 절차 없이 기준 사진으로 올리지 않는다.
- 역이미지 검색은 승인할 때 한 번, 그 뒤 매달 한 번. (근거: 04-compliance-checklist.md §8-2)

### 2-2. 매 이미지: 기준 사진에서 편집 (edit-from-reference)

| 길 | 얼굴을 맞추는 방법 |
|---|---|
| API (`generate`) | `face_reference`가 있으면 인물 사진을 기준 사진과 함께 편집(edit) 요청으로 보낸다. flatlay처럼 인물이 없는 사진은 기준 없이 생성한다. (키트 동작) |
| ChatGPT 앱 | 새 채팅마다 기준 사진 2~3장을 첨부하고 `prompts.md`의 블록을 붙여넣는다. 고칠 때는 같은 채팅에서 한 번에 한 가지만 |

- `brand/doha.yaml`의 `visual.identity` 문장은 고치지 않는다. 줄이면 다른 사람이 된다. (근거: brand/prompt-guide.md §2)
- 같은 옷이 여러 장에 나오면 `outfit`에 "the same …" 문장을 그대로 복사한다.

### 2-3. 얼굴이 흔들릴 때

| 증상 | 할 일 |
|---|---|
| 기준 사진과 다른 사람 같음 | 같은 채팅에서 기준 사진을 다시 첨부하고 얼굴만 고친다 (1회). 안 되면 새 채팅 |
| 왼쪽 눈 아래 점이 반대쪽 | 좌우 반전이나 거울 장면인지 본다. 거울 장면은 피한다 |
| 어려 보이거나 인형 같음 | 고치지 말고 반려한 뒤 새로 만든다 |
| 게시물마다 조금씩 달라짐 | 매주 한 번, 그 주 승인 사진을 `doha-face-01.png` 옆에 놓고 비교한다 |

---

## 3. 실사 QA 체크리스트

**보는 순서**: ① 원본 크기 100%로 확대 ② 휴대폰 크기(`out/contact-sheet.png`, `out/preview.html`).
**판정**: 하나라도 걸리면 `approved`로 바꾸지 않는다. 고치거나 `rejected`. (근거: brand/prompt-guide.md §4)

| # | 항목 | 통과 기준 | 자주 나는 실패 | 고치는 방향 |
|---|---|---|---|---|
| 1 | **얼굴 일관성** | 기준 사진과 같은 사람: 아몬드형 눈, 일자 눈썹, 부드러운 턱선, 어깨 길이 C컬·옆가르마, 도하의 왼쪽 눈 아래 점(보는 사람 기준 오른쪽). 28세 정도 성인. 유명인을 닮지 않음 | 눈·턱 모양이 바뀜, 점이 사라짐 | 기준 사진 첨부 후 얼굴만 수정 |
| 2 | **손가락** | 다섯 개, 관절 방향 자연스러움. 컵·단추·가방끈과 맞물린 부분이 녹아 있지 않음 | 여섯 개, 손이 물건과 붙음 | 손만 수정 / 손 동작을 단순하게 |
| 3 | **옷 봉제선·단추** | 솔기·단추·주머니·벨트 고리 위치가 말이 됨. 단추 수가 맞음. 여밈·넣어 입은 정도가 `outfit`과 같음 | 단추 줄이 어긋남, 두 옷이 섞임 | `outfit`에 여밈·단추 수 명시 |
| 4 | **소재 질감** | 울·니트·코튼 결이 보임. 플라스틱처럼 번들거리지 않음 | 니트가 매끈함 | 소재와 결을 `outfit`에 명시 |
| 5 | **그림자 방향** | 얼굴·옷·배경의 빛 방향이 같음. 발밑 접지 그림자. 거울·유리 반사가 맞음 | 그림자 없음, 빛이 두 방향 | 빛 방향 한 개만 적기 |
| 6 | **배경 글자·로고** | 간판, 가방·신발·컵 로고, 깨진 가짜 글자가 없음 (작은 것까지 확대) | 깨진 글자, 실제 브랜드처럼 보이는 로고 | 로고만 지우는 수정 / 간판 없는 장소 |
| 7 | **피부 과보정** | 모공·잔결이 보임. 도자기 피부·필터 느낌 없음. 화장은 가볍게 | 지나치게 매끈함 | 피부결만 자연스럽게 수정 |
| 8 | **비율 왜곡** | 다리 길이·머리 크기·신발 크기가 과장되지 않음. 바닥선이 기울지 않음 | 다리가 길게 늘어남, 머리가 작음 | `framing`을 full-body → three-quarter |
| 9 | 시그니처·의상 일치 | 시계는 왼손목, 작은 금 귀걸이. 슬라이드 `items`와 사진 속 옷이 같음 | 시계가 오른손 | 해당 부분만 수정 |
| 10 | 글자 자리·크롭 | 커버는 위 1/3이 비어 있음. `render` 뒤 3:4·9:16 크롭에서 머리·신발이 안 잘림 | 얼굴이 제목 밑에 깔림 | 슬라이드 `focus` 조정 / 다시 생성 |
| 11 | (협찬) 제품 | 실물 사진·실측과 색·패턴·핏이 맞고, 브랜드가 승인함 | 색이 다름 | 실물 사진 기준으로 다시. 승인 전 게시 금지 |

- **바로 반려하는 것**: 1(다른 사람·미성년처럼 보임), 2(눈에 띄는 손가락 오류), 6(실제 브랜드로 보이는 로고), 11(브랜드 미승인). 나머지는 고쳐 본다. (운영 규칙)
- 6번 근거: 협찬받지 않은 브랜드 로고를 AI로 재현해 제휴한 것처럼 보이게 하지 않는다 (해석). (근거: research/kr-compliance.md §5-3)
- 11번 근거: 협찬 의류는 실물 사진·실측 기준으로 만들고 브랜드 승인 뒤 게시한다 (해석). AI 이미지가 소비자를 오인하게 하면 허위광고로 볼 수 있다 [보도]. (근거: research/kr-compliance.md §4-1)
- 고치는 문장 예시는 brand/prompt-guide.md §5에 있다.

---

## 4. 반려·반복 규칙 (운영 규칙)

- **시도 1회 = 후보 1장.** 새로 만들기 1번이나 수정 요청 1번이 1회다. `--n 2`는 2회로 센다.
- **이미지(키) 하나에 최대 3회.** 3회 안에 §3을 통과하지 못하면 멈춘다.
- 멈추면 `post.yaml`의 `prompt`·`outfit`·`framing`을 다시 쓴다(아래 표). `prompts`나 `generate --dry-run`으로 확인하고 **새 채팅**에서 다시 최대 3회.
- 두 번째 3회도 실패하면 **장면을 바꾼다**: 손이 덜 보이는 자세, 더 단순한 배경, `detail`·`flatlay`로 대체. 또는 그 슬라이드를 뺀다.
- 한 번에 한 가지만 고친다. 수정이 쌓이면 화질이 떨어지고 얼굴이 바뀐다. 그때는 새 채팅에서 처음부터. (근거: brand/prompt-guide.md §5)
- 반려하면 `status: rejected`로 바꾸고 `review.notes`에 이유를 적는다 (예: `s03 반려: 손가락 6개, 3회`).
- 같은 원인이 게시물 2개 이상에서 반복되면 brand/prompt-guide.md나 `brand/doha.yaml`의 `negative`를 고칠지 사람이 정한다.

| 반복 원인 | 프롬프트를 다시 쓰는 방향 |
|---|---|
| 손 | 동작을 하나로, 단순하게: "both hands relaxed at her sides", "one hand holding the bag strap" |
| 배경 글자·로고 | `brand/doha.yaml` `settings`의 간판 없는 장소로 바꾸고 "no readable signage" |
| 옷 구조 | `outfit`에 여밈·단추 수·기장을 적고, 같은 옷은 같은 문장을 복사 |
| 얼굴 흔들림 | `three-quarter`·`waist-up`으로 얼굴을 크게. 기준 사진 첨부 확인 |
| 비율 왜곡 | `full-body` 대신 `three-quarter` |
| 그림자·조명 | 빛 방향 한 개: "soft daylight from the left" |

---

## 5. 파일 이름과 상태 필드

### 5-1. 파일

| 무엇 | 위치·이름 | 규칙 |
|---|---|---|
| 게시물 사진 | `content/posts/<id>/images/sNN.png` | 키는 `s01`, `s02` … 두 자리. `images.<키>.file`과 같게 |
| 이전 후보 | `images/sNN.vN.png` (예: `s03.v1.png`) | `generate`는 자동 보관. ChatGPT 앱 경로는 새 파일을 저장하기 전에 기존 파일 이름을 직접 바꾼다. **덮어쓰지 않는다** |
| 얼굴 기준 | `brand/reference/doha-face-NN.png` | 덮어쓰지 않음. git에 올라감 |
| 렌더 결과 | `out/slides/NN.png`, `out/reel/reel.mp4`, `out/reel/cover.png` | `out/`은 git에 안 올라감. 다시 만들 수 있음 |
| 프롬프트 | `post.yaml`의 `images.<키>.prompt`·`outfit` | 확정 프롬프트가 곧 기록. `out/prompts.md`는 git 밖 |
| ChatGPT 대화 기록 | 대화 링크·캡처 | `review.notes`에 링크 (근거: 04-compliance-checklist.md §10) |

- `images/`는 git에 올라간다. AI로 만든 도하 이미지만 넣는다. 브랜드가 준 실물 사진 같은 자료는 git 밖에 둔다. (운영 규칙)
- `--mock`으로 만든 MOCK 자리표시 파일('게시 금지' 표시)을 실제 게시물 폴더에 만들었다면 지운다.

### 5-2. 사진 상태 (`images.<키>.status`)

| 값 | 뜻 | 누가 바꾸나 | 키트 반응 |
|---|---|---|---|
| `todo` | 아직 없음 | `new` 뼈대 | `render`는 자리표시 이미지 |
| `generated` | 만들어짐, 검수 전 | `generate`는 자동. ChatGPT 앱 경로는 사람 | — |
| `approved` | §3 통과 | **사람만** | `generate`가 건너뜀 (`--only`로 지정할 때만 다시 만듦) |
| `rejected` | 반려 | 사람 | 슬라이드·장면에서 쓰고 있으면 `check` 주의 |

- 게시물 `status`가 `approved`·`posted`인데 승인 안 된 사진이 있으면 `check`가 주의를 낸다.
- 게시물 상태 흐름: `idea → draft → images → rendered → reviewed → approved → posted` (근거: content/SCHEMA.md)

---

## 6. 비용 관리

### 6-1. 두 길

| | ChatGPT 앱 | API (`generate`) |
|---|---|---|
| 비용 | API 비용 없음. ChatGPT 구독료와 API 요금은 따로다 | 사용량에 따라 과금. 장당 금액은 키트 추정치 |
| 언제 | 지금 기본값 | 얼굴 기준이 고정되고 장수가 많을 때 |
| 기록 | 구독료를 `tracking/costs.csv`에 손으로 (`category: subscription`) | `tracking/costs.csv`에 자동 (`category: image_api`) |

(근거: 00-master-plan.md §4, 07-automation.md §3)

### 6-2. 키트 설정 (`config.yaml` `image_generation`)

| 설정 | 값 | 운영 |
|---|---|---|
| `quality` | `medium` | 시안은 medium. high는 확정 컷에만 |
| `est_cost_usd` | low 0.02 / medium 0.05 / high 0.17 | **키트 예상치.** 실제 단가가 아님 |
| `max_cost_per_run_usd` | 1.00 | 한 번 실행 상한. 넘으면 실행하지 않음. 우선순위: `--max-cost` > `.env`의 `DOHA_MAX_COST_USD` > config |
| `require_confirmation` | true | 비용이 나기 전에 터미널에서 `y` |

- 상한 $1.00이면 한 번에 medium 약 12장, high 약 5장이다 (기준 사진 3장 포함, 키트 예상치 기준). 넘으면 `--only`로 나눈다.
- **high는 업스케일이 아니다.** `generate`는 매번 새로 만든다. medium 시안을 high로 다시 만들면 다른 사진이 나오고 QA를 다시 해야 한다. 그래서 high는 처음부터 확정 컷(커버, 협찬 납품)으로 쓸 때만 쓴다. medium이 휴대폰 미리보기에서 충분하면 그대로 승인한다. (운영 규칙)
- **주간 예상** (가정, 키트 예상치 기준, 모두 API로 만들 때): 주 20장 × 평균 1.5회 = 후보 30장, 모두 medium(기준 사진 포함 장당 약 $0.08) → 약 $2.40/주, 약 ₩3,360 (`fx.usd_krw` 1400). 4주 약 $9.60. 모두 high면 약 2.5배. 실제 단가가 확인되면 다시 계산한다.

### 6-3. 처음 돈을 쓰기 전에

- [ ] `.env`에 `OPENAI_API_KEY`. 키는 채팅·문서·커밋에 넣지 않는다. (근거: 00-master-plan.md §4, .env.example)
- [ ] 선불 결제: 기록상 최소 충전액 $5, 자동 충전이 기본으로 켜질 수 있다. 원치 않으면 끈다. (근거: 00-master-plan.md §4)
- [ ] 첫 실행은 `--dry-run`, 그다음 한 장만 생성해 실제 사용량을 본다. (근거: 00-master-plan.md §9)
- [ ] 조직 인증·한도 오류 대응은 brand/prompt-guide.md §6.

### 6-4. 기록과 대조

- `generate`는 생성할 때마다 `tracking/costs.csv`에 한 줄을 쓴다. 메모에 `estimate` 또는 `usage-based`가 남는다.
- 공식 토큰 단가를 `config.yaml` `image_generation.token_prices_usd_per_1m`에 넣으면 응답 사용량으로 계산한다. 없으면 예상치로 적는다. (근거: brand/prompt-guide.md §6)
- 매달 한 번 OpenAI 사용량 화면과 `costs.csv`의 `image_api` 합계를 비교한다. 차이가 크면 `est_cost_usd`를 고친다. (운영 규칙)
- 비용은 월 순수익에서 빠진다. `python doha.py metrics` 리포트에 비용 합계가 나온다. (근거: 00-master-plan.md §2)

### 6-5. 아직 모르는 숫자

- 00-master-plan.md §4는 OpenAI 공식 비용표 기준으로 GPT Image 2 세로 1024×1536 고화질 1장을 약 $0.165로 적었다. 사용자의 원 계획에 있던 기록이다. 다시 확인이 필요하다.
- low·medium 실제 단가, 입력 토큰 단가, ChatGPT 플랜별 생성 한도, 다른 생성 툴 비교는 추가 조사 예정: docs/research/image-gen-tech.md

---

## 7. 스틸 사진으로 릴스 만들기

### 7-1. 지금: 켄 번스 (`python doha.py reel <게시물>`)

- 장면은 `post.yaml`의 `reel.scenes`에서 온다 (`image`, `layout`, `text`, `seconds`, `motion`).
- `motion`: `zoom-in` · `zoom-out` · `pan-left` · `pan-right` · `still`. 최대 1.08배로 느리게 움직이고, 장면 사이 0.3초 크로스페이드. 1080×1920, 30fps. (키트 값)
- 2:3 사진을 9:16에 꽉 채우므로 좌우가 잘린다. 인물을 가운데 두라는 문장은 프롬프트에 자동으로 들어간다.
- 인물 장면에는 'AI 가상인물' 배지가 자동으로 붙는다.
- 총 길이는 5~90초여야 `check`를 통과한다. 출근 15초는 12~15초. (02-content-strategy.md §7-2)
- **음원**: `reel.audio: null`이면 무음 MP4가 나온다. 무음 영상은 추천에서 덜 노출된다 [확인]. 게시할 때 앱에서 라이브러리 음원을 넣는다. 라이브러리 음악은 아티스트·곡명이 표시되게 쓴다 [확인]. 협찬 릴스는 상업 이용이 허가된 음원만 (해석). (근거: research/ig-platform.md §4-2, research/kr-compliance.md §5-4)
- **검수**: 화면 떨림, 글자가 세이프존 안에 있는지, 첫·끝 장면 표시, 커버(`cover.png`)의 그리드 3:4 크롭.
- 문제를 찾을 때는 `--keep-frames`로 프레임 PNG를 남긴다.

### 7-2. 나중: 이미지→영상 도구

- 아직 쓰지 않는다. 도구·가격·약관은 추가 조사 예정: docs/research/image-gen-tech.md
- 쓰게 되면:
  - 사실적인 영상은 AI 라벨 공개가 의무다 [확인]. (근거: research/ig-platform.md §3-1)
  - 프레임마다 얼굴·손이 이어지는지 §3 기준으로 본다. 시도 3회 규칙도 같다.
  - 비용은 `tracking/costs.csv`에 적는다.

---

## 8. 권리와 표시

### 8-1. 메타데이터·워터마크

- Meta는 C2PA·IPTC 같은 업계 AI 신호를 감지하거나 게시자가 밝히면 'AI 정보' 라벨을 붙인다 [확인]. 생성 도구가 넣은 메타데이터로 자동 라벨이 붙는 것은 정상이다. (근거: research/ig-platform.md §3-1, §3-3)
- **원본은 받은 그대로 둔다.** `images/`의 원본을 다른 앱에서 다시 저장·압축하거나 화면 캡처로 대신하지 않는다. AI 툴이 넣은 워터마크·메타데이터를 지우지 않는다 (해석). 정부가 이용자의 AI 표시 제거·변조 금지를 정보통신망법 개정으로 추진 중이지만 아직 법이 아니고 시행일도 없다 [보도]. (근거: research/kr-compliance.md §2, §3)
- 키트의 렌더 결과(`out/slides`, `reel.mp4`)는 브라우저·ffmpeg로 새로 만든 파일이다. 원본 메타데이터가 이어진다고 보지 않는다 (확인 필요). 자동 라벨에 기대지 말고 **앱에서 직접 'AI 정보' 라벨을 켠다.** (근거: research/ig-platform.md §3-1 "자동 라벨이 없다고 공개 의무가 사라지지 않음", 운영 결론)

### 8-2. 게시할 때 표시 (모든 게시물)

| 어디 | 무엇 | 근거 |
|---|---|---|
| 프로필 | 'AI 생성 프로필' 라벨, 소개 첫 줄 `bio_line` | research/ig-platform.md §3-2 [보도], 운영 결론 |
| 게시물 | 'AI 정보' 라벨. 릴스는 반드시 [확인], 카드뉴스도 기본값 | research/ig-platform.md §3-1, 운영 결론 |
| 이미지 안 | 'AI 가상인물' 배지를 도하 가까이 (렌더러 자동). 협찬 게시물은 의무 [확인], 일반 게시물은 기본값 (해석) | research/kr-compliance.md §1-5 |
| 캡션 | `caption_footer` (`preview` 자동) | brand/doha.yaml `disclosure` |
| 대체 텍스트 | "AI로 만든 가상 스타일리스트 도하가 …" | `check` 주의 항목 |
| 협찬·제휴 | 3중 표시 + 가상인물 고지 + AI 합성 제품 안내(`product_image_note`) | 04-compliance-checklist.md §3~5 |

- 렌더러는 `framing`이 `flatlay`·`detail`인 사진에는 배지를 붙이지 않는다 (키트 동작). 도하의 몸이 크게 보이는 `detail` 컷에도 표시가 필요한지는 근거가 없다 (확인 필요). 그때까지 협찬 게시물의 `detail` 컷은 옷·소품 위주로 찍고 몸이 거의 안 보이게 한다. (운영 규칙)

### 8-3. 얼굴·저작권·약관

- **얼굴**: §2-1 규칙. 생성 과정 기록(프롬프트, 편집 이력, 대화 링크)은 분쟁 때 독자적으로 만들었다는 증거가 된다 (해석). (근거: research/kr-compliance.md §5-1)
- **저작권**: AI가 기계적으로 만든 결과물은 저작물로 등록할 수 없다. 사람의 창작적 기여가 있어야 하고, 작업 기록이 심사에 중요하다 [보도]. 기획·문구·편집·배열은 사람이 하고 `post.yaml`·`review.notes`·대화 링크로 남긴다. (근거: research/kr-compliance.md §5-2)
- **툴 약관**: 상업적 이용 조건과 산출물 권리 귀속은 툴마다 다르다 [미확인]. 추가 조사 예정: docs/research/image-gen-tech.md
- **실존 브랜드·인물**: 프롬프트에 브랜드명·실존 인물 이름을 쓰지 않는다. 협찬 제품도 이름 대신 색·소재·실루엣으로 묘사한다. (근거: brand/prompt-guide.md §3)
- **협찬 결과물 권리**: 원본 파일과 캐릭터(도하) 권리는 운영자에게 두고, 브랜드에는 이용 허락만 준다 (해석). (근거: research/sponsorship-kr.md §5-2)

---

## 확인 필요

1. 이미지 모델의 실제 단가(low·medium·high, 입력 토큰)와 `est_cost_usd` 값. 추가 조사 예정: docs/research/image-gen-tech.md
2. ChatGPT 플랜별 이미지 생성 한도. 추가 조사 예정: docs/research/image-gen-tech.md
3. ChatGPT 앱·API로 만든 이미지에 C2PA 메타데이터가 들어가는지, 내려받은 뒤에도 남는지.
4. 키트 렌더 결과(`out/slides/*.png`, `reel.mp4`)에 원본 메타데이터가 남는지. 실제 파일로 확인.
5. 이미지·영상 생성 툴의 상업 이용 약관과 산출물 권리. 추가 조사 예정: docs/research/image-gen-tech.md
6. 이미지→영상 도구 후보와 가격. 추가 조사 예정: docs/research/image-gen-tech.md
7. 앱 게시 화면에서 'AI 정보' 라벨 토글 위치 (04-compliance-checklist.md와 같은 항목).
8. 역이미지 검색에 쓸 도구.
9. 얼굴은 안 보이고 몸·손만 크게 나오는 `detail` 컷에도 '가상인물' 표시가 필요한지 (공정위 지침 원문의 '인물과 가까운 위치' 해석, research/kr-compliance.md 남은 확인 사항).
