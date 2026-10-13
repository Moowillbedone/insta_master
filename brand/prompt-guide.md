# 이미지 프롬프트 가이드

도하 이미지를 만드는 방법, 프롬프트를 쓰는 법, 결과를 검수하고 고치는 법을 정리했어요.
코드는 `doha/imagegen.py`, 인물·스타일 기준은 `brand/doha.yaml`, 얼굴 기준 사진은 `brand/reference/README.md` 에 있어요.

## 1. 전체 흐름

```
post.yaml images.<키>  ─┐
  (outfit · prompt ·    ├─ compose_prompt ─┬─ prompts  → out/prompts.md → ChatGPT 앱 (0원)
   framing)             │                  └─ generate → OpenAI API (유료, 확인 후)
brand/doha.yaml visual ─┘                                      │
                                         images/<키>.png  ◀────┘
                                               │
                     사람 검수 (4장 체크리스트) → status: approved → render · reel · preview
```

- 사진에는 **글자를 넣지 않아요**. 제목·라벨·광고 표시·`AI 가상인물` 배지는 렌더러가 얹어요.
- 상태: `todo` → `generated` (만들어짐, 검수 전) → `approved` / `rejected`. `approved` 는 사람만 바꿔요.

```
python doha.py prompts black-slacks              # 0원 경로: out/prompts.md
python doha.py prompts --reference               # 얼굴 기준 사진용 프롬프트
python doha.py generate black-slacks --only s01 --dry-run   # 프롬프트·예상 비용만
python doha.py generate black-slacks --only s01             # 실제 생성 (확인 질문)
python doha.py generate black-slacks --mock                 # 오프라인 자리표시 PNG
```

## 2. 프롬프트가 만들어지는 방식

`compose_prompt(post, key, persona)` 가 아래 순서로 줄을 이어 붙여요. 같은 입력이면 항상 같은 결과예요.

| 줄 | 가져오는 곳 | 메모 |
|---|---|---|
| `Style:` | `visual.photography` | 카메라·렌즈·빛·색감 |
| `Model:` | `visual.identity` | 얼굴·머리·체형. **그대로** 넣어요 (줄이면 다른 사람이 돼요) |
| `Signature details:` | `visual.signature_details` | 은색 시계(왼손목), 작은 금 귀걸이 |
| 기준 사진 안내 | `visual.face_reference` 에 파일이 있을 때 | "얼굴은 첨부 사진, 옷·포즈·장소는 프롬프트" |
| `Outfit:` / `Items:` | `images.<키>.outfit` | 인물 없는 사진이면 `Items:` |
| `Scene:` | `images.<키>.prompt` | 이 문서 3장 참고 |
| `Framing:` | `images.<키>.framing` | full-body · three-quarter · waist-up · detail · flatlay 고정 문장 |
| `Composition:` | 슬라이드·릴스에서 쓰이는 곳 | 글자 자리, 좌우 여백 |
| `Constraints:` | `visual.negative` + `visual.avoid_identity` | flatlay 는 손·피부 관련 문구를 빼요 |

- `framing: flatlay` 는 인물 없는 사진으로 보고 `Model`·시그니처·기준 사진을 빼요. 다른 프레이밍에서 인물을 빼려면 `person: false`.
- **글자 자리**: 사진 위에 글자가 얹히는 곳만 비우라고 넣어요 (`templates/` 기준).
  커버 → 위 1/3 (슬라이드에 `text_position: bottom` 이면 아래), 릴스 첫 장면(`reel-hook`) → 위, 릴스 코디 장면(`reel-look`) → 아래 자막 카드.
  `look`·`checklist`·`product`·`cta`·`compare` 슬라이드는 글자를 사진 밖 패널에 둬서 비울 필요가 없어요.
  직접 정하려면 `images.<키>.text_space: upper | lower | both | none`. 템플릿이 바뀌면 `doha/imagegen.py` 의 `OVERLAY_ZONE` 을 맞춰요.
- **크롭**: 생성 크기는 2:3(1024x1536)이에요. 릴스(9:16)와 비교 슬라이드 반쪽 칸은 좌우가, `look`(약 1.1:1)·`checklist`(약 1.9:1) 같은
  슬라이드 사진 칸은 위아래가 많이 잘려요. 그래서 인물은 가운데, 얼굴·핵심 옷은 세로 가운데 띠 안에 두라고 넣어요.
  잘리는 위치는 슬라이드의 `focus` 로 렌더러에서 조정해요.
- 길이: 인물 사진 약 2,000자, flatlay 약 1,100자. 인물 묘사만 1,200자가 넘어서 더 줄이지 않았어요 (모델 입력 한도보다 훨씬 짧아요).
- ChatGPT 앱용 블록에는 맨 앞에 비율을 지정하는 한 줄이 더 붙어요. API는 크기를 따로 보내요.

## 3. 장면 프롬프트(`images.<키>.prompt`) 쓰는 법

**영어로, 장면만** 써요. 외모·촬영 스타일은 자동으로 붙으니 다시 쓰면 충돌해요.

1. **어디서 · 무엇을 · 어떤 빛** 순서로: "on a quiet Seongsu-dong street at 8am, red-brick wall behind her, soft overcast light, she adjusts the cardigan on her shoulder".
2. **한 장면에 동작 하나.** 손 동작은 단순하게 (컵 들기, 단추 잠그기, 가방끈 잡기). 손가락이 많이 보이는 동작일수록 오류가 늘어요.
3. **빛 방향**을 적어요 ("soft daylight from the left"). 그림자가 일관돼 사진처럼 보여요.
4. **글자가 생길 만한 배경을 피해요**: 간판, 지하철 노선도, 책 표지, 모니터 화면, 커피컵 로고 → "no readable signage" 를 덧붙여요.
5. **브랜드·실존 인물 이름을 쓰지 않아요.** 협찬 제품도 이름 대신 색·소재·실루엣으로 묘사하고, 실물과 다를 수 있다는 안내(`disclosure.product_image_note`)를 렌더러가 붙이게 해요.
6. **의상(`outfit`)은 소재·색·핏·여밈까지** 구체적으로. 같은 옷을 여러 장에 쓰면 "the same …" 와 같은 표현을 그대로 복사해요.
   슬라이드의 `items` 목록과 사진 속 옷이 같아야 해요.
7. 체형·신체를 강조하는 표현, 과한 다이어트 연상 표현은 쓰지 않아요 (브랜드 원칙 · 안전 정책 거절 원인).

| 나쁜 예 | 좋은 예 |
|---|---|
| "beautiful Korean girl in a stylish office outfit, perfect body" | "three-quarter shot standing by a large window in a bright office lounge, one hand lightly holding a coffee cup, natural window light" |
| "she wears a ZARA blazer in front of a Starbucks" | "charcoal single-breasted wool blazer; quiet cafe window seat, no readable signage" |
| "walking, waving, holding phone and coffee, looking back" | "walking out through the glass door, looking ahead with a calm half-smile" |

## 4. 검수 체크리스트 (실사 이미지)

게시 전에 **사람이** 원본 크기로 확대해서 봐요. 하나라도 걸리면 `rejected` 로 두고 고치거나 다시 만들어요.

**얼굴 일관성**
- [ ] 기준 사진과 같은 사람인가요? 눈 모양, 일자 눈썹, 턱선, 머리 길이·컬·가르마.
- [ ] 그녀의 **왼쪽 눈 아래 점**(보는 사람 기준 오른쪽). 거울 장면은 반전돼 보일 수 있어요.
- [ ] 28세 정도 성인으로 보이고, 유명인을 닮지 않았어요.

**손**
- [ ] 손가락 다섯 개, 관절 방향이 자연스러워요. 컵·단추·가방끈과 맞물리는 부분이 녹아 있지 않아요.
- [ ] 시계는 왼손목, 귀걸이는 작은 금색.

**옷 구조 · 원단 솔기**
- [ ] 솔기·단추·주머니·벨트 고리 위치가 말이 되고, 좌우 단추 수가 맞아요.
- [ ] 바지 주름선, 소매 접힘 횟수, 넣어 입은 정도가 `outfit` 과 같아요.
- [ ] 원단 경계가 번지거나 두 옷이 섞여 보이지 않아요. 울·니트·코튼 질감이 보이고 플라스틱처럼 번들거리지 않아요.

**글자 · 로고 흔적**
- [ ] 배경 간판, 가방·신발·컵의 로고, 깨진 가짜 글자가 없어요 (작은 것도 확대해서 확인).

**피부 결**
- [ ] 모공·잔결이 보이고, 도자기처럼 매끈하거나 필터를 씌운 느낌이 없어요. 화장은 가볍게.

**조명의 사실감**
- [ ] 얼굴·옷·배경의 빛 방향이 같아요. 발밑에 접지 그림자가 있어요.
- [ ] 유리·거울 반사가 물리적으로 맞아요 (거울 속 인물이 따로 놀지 않아요).

**비율 · 구도**
- [ ] 다리 길이·머리 크기·신발 크기가 과장되지 않았어요. 바닥선이 기울지 않았어요.
- [ ] 글자 자리가 비어 있고, `render` 후 3:4·9:16 크롭에서 머리·신발이 잘리지 않아요 (`out/contact-sheet.png` 로 확인).

## 5. 고치는 법 (반복)

**ChatGPT 앱 (0원)**
- 같은 채팅에서 **한 번에 한 가지만** 고쳐요. 예:
  - "Keep her face, outfit, pose and lighting exactly the same. Only fix her right hand so it holds the cup with five natural fingers."
  - "Keep everything the same. Remove the logo on the bag and the sign in the background."
  - "Keep everything the same. Make the skin texture more natural, less smooth."
  - "Same person as the attached reference photo. Keep the outfit and setting, fix the face to match the reference."
- 영역 선택 편집이 보이면 고칠 부분만 칠해서 요청해요.
- 2~3번 고쳐도 안 되면 새 채팅에서 처음부터 만들어요 (수정이 쌓이면 화질이 떨어지고 얼굴이 바뀌어요).

**API (`generate`)**
- 지금 `generate` 는 새로 만들기만 해요. 부분 수정은 ChatGPT 앱에서 해요.
- 같은 문제가 반복되면 `post.yaml` 의 `prompt`·`outfit` 을 고치고 `--dry-run` 으로 프롬프트를 확인한 뒤 다시 만들어요
  (예: 손 오류 → "both hands relaxed at her sides").
- 후보 여러 장: `--n 2` (비용 2배). 후보 1이 `<키>.png`, 나머지와 이전 이미지는 `<키>.vN.png` 로 보관돼요.
  다른 후보가 낫다면 파일 이름을 직접 바꿔요. 기존 파일은 절대 그냥 덮어쓰지 않아요.
- 품질: 시안은 `low`/`medium`, 확정컷만 `high`.

## 6. 비용 · 오류 메모

- **ChatGPT 앱**: 유료 플랜에 이미지 생성이 포함돼 있어 한도 안에서는 추가 비용이 없어요. API 결제와는 별개예요.
- **API 예상 비용** = 장수 × `config.image_generation.est_cost_usd[품질]` (+ edit 때 기준 사진 1장당 $0.01 여유분). 모두 **추정치**예요.
- **한도**: `--max-cost` > 환경변수 `DOHA_MAX_COST_USD` > `config.image_generation.max_cost_per_run_usd` 순서. 넘으면 실행하지 않아요.
  `require_confirmation: true` 면 터미널에서 `y` 를 입력해야 하고, 터미널이 아니면 `--yes` 가 필요해요.
- **기록**: 생성할 때마다 `tracking/costs.csv` 에 한 줄 (`category=image_api`). 메모에 `estimate` 또는 `usage-based` 와 토큰 수가 남아요.
  공식 가격표의 토큰 단가를 `config.yaml` 에 넣으면 응답 사용량으로 계산해요 (없으면 추정치로 기록):

  ```yaml
  image_generation:
    token_prices_usd_per_1m: { text_input: 0, image_input: 0, image_output: 0 }   # 공식 가격표 값으로 채우기
  ```

- 자주 나는 오류
  - `403 … must be verified` → **조직 인증(Organization verification)** 필요: platform.openai.com → Settings → Organization → General → Verify Organization. 반영까지 15분 정도.
  - `429 insufficient_quota` → Billing 에서 크레딧·월 한도 확인. 그냥 `429` 는 1~2분 뒤 `--only` 로 남은 것만.
  - 모델 없음 → `config.yaml` 의 `image_generation.model` 을 `gpt-image-1.5` 나 `gpt-image-1` 로.
  - 안전 정책 거절 → 3장 7번, 5번을 보고 표현을 바꿔요.
- 키는 `.env` 에만 둬요 (`.env.example` 참고). 채팅·문서·커밋에 붙여넣지 않아요.

### 테스트용

- `--dry-run`: 프롬프트·예상 비용만 출력, API 호출 없음.
- `--mock`: API 없이 'MOCK · 게시 금지' 자리표시 PNG를 저장해요 (글자 자리·크롭 선 표시). 비용 기록·`post.yaml` 상태 변경은 하지 않아요.
  실제 게시물 폴더에서 썼다면 `images/` 의 목업 파일을 지워 주세요.
- `DOHA_TRACKING_DIR=/임시/폴더`: `costs.csv` 를 다른 폴더에 쓰게 해요. 테스트 전용이고, 운영에서는 비워 둬요.
