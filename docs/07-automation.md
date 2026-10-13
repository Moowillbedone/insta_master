# 자동화 범위

- 기준일: 2026-10-13 (KST)
- 한 줄 요약: **만들기와 검수는 키트가 돕고, 게시와 사람 사이의 일은 사람이 합니다.**
- 원칙 (근거: 00-master-plan.md §1, §4, §7)
  - 모든 게시물은 게시 전에 사람이 검수합니다.
  - 자동 게시, 자동 DM, 스크래핑, 참여 자동화(팔로우·좋아요·댓글)는 하지 않습니다. 댓글 키워드 DM만 조건부 예외로 두고, 지금은 쓰지 않습니다 (§6-1).
  - API는 내 계정에만 씁니다.

**신뢰도 표시**: [확인] 공식 출처 · [보도] 언론 · [주장] 업체·블로그 · [미확인] 확인 못 함 · (해석) 리서치 판단 · (운영 규칙) 우리가 정한 규칙 · (키트 동작) 코드 기준 · (확인 필요) 리서치에 없음, 맨 아래 목록

**근거 문서**: [research/ig-platform.md](research/ig-platform.md) · [research/kr-compliance.md](research/kr-compliance.md) · [research/sponsorship-kr.md](research/sponsorship-kr.md) · [research/image-gen-tech.md](research/image-gen-tech.md) · [research/affiliate-kr.md](research/affiliate-kr.md) · [research/content-trends.md](research/content-trends.md) · [00-master-plan.md](00-master-plan.md) · [config.yaml](../config.yaml) · [content/SCHEMA.md](../content/SCHEMA.md)

---

## 1. 키트가 자동화하는 것

게시물 상태 흐름: `idea → draft → images → rendered → reviewed → approved → posted` (근거: content/SCHEMA.md)

| 단계 | 명령 | 키트가 하는 일 | 사람 확인 지점 |
|---|---|---|---|
| 기획 | `python doha.py new "제목(hook)" --date YYYY-MM-DD` | `content/posts/<날짜>-<슬러그>/post.yaml` 뼈대 생성 | hook, pillar, goal, `disclosure` 플래그를 직접 채움 |
| 얼굴 기준 | `python doha.py prompts --reference` | 얼굴 기준 이미지용 프롬프트 출력 | 얼굴 승인, 역이미지 검색, `brand/doha.yaml` `face_reference` 등록 |
| 프롬프트 | `python doha.py prompts <게시물>` | `out/prompts.md` 생성. 인물·촬영 스타일은 페르소나 파일에서 자동 조합 | ChatGPT 앱에 붙여넣어 생성, `images/sNN.png` 저장 |
| 이미지 (API: 확정·협찬 컷) | `python doha.py generate <게시물> --only s01 --dry-run` → `--dry-run` 빼고 실행 | 예상 비용 계산, 한도 초과 시 거절, 실행 전 y 확인, 응답 토큰 수로 실제 금액을 `tracking/costs.csv`에 기록 | 비용 승인, 결과 검수 후 `images.<키>.status: approved` |
| 검수 | `python doha.py check <게시물>` (`--all`) | 광고·AI 표시, 체험 표현, 효능 표현, 상품 출처·확인일, 글자 수, 필수 항목 검사. 오류가 있으면 `build`가 멈춤 | 주의(warn) 항목 판단 |
| 카드뉴스 | `python doha.py render <게시물>` | `out/slides/NN.png` (1080×1440, `--size 4x5`면 1080×1350). 인물 슬라이드에 `AI 가상인물` 배지, 커버에 광고 표시 자동 | 글자 겹침, 배지 위치, 얼굴·손·옷 |
| 릴스 | `python doha.py reel <게시물>` | `out/reel/reel.mp4` (1080×1920), `cover.png` | 첫·끝 장면 표시, 세이프존, 음원 |
| 미리보기 | `python doha.py preview <게시물>` | `contact-sheet.png`, 휴대폰 비율 `preview.html`, 붙여넣기용 `caption.txt`, 앱 게시 체크리스트 | 휴대폰에서 최종 확인, `review.approved_by` 기록 |
| 한 번에 | `python doha.py build <게시물>` | check → render → reel → preview. 검수 오류가 있으면 멈춤(`--force`는 시안 확인용, 게시 금지) | 위와 같음 |
| 게시 | 없음 | **자동 게시 안 함** | 앱에서 직접 게시, 라벨 켜기 (docs/04-compliance-checklist.md) |
| 지표 가져오기 (선택) | `python doha.py insights` | API로 내 게시물 지표를 읽어 `tracking/metrics.csv`에 추가 (§5) | 앱 인사이트와 비교, 빈 칸 채우기 |
| 성과 | `python doha.py metrics` (`--month YYYY-MM`) | `tracking/*.csv`로 성과·수익·비용 리포트 (`out/reports/`) | 24시간·7일 지표 입력 |
| 미디어킷 | `python doha.py media-kit` | 브랜드 제안용 HTML·PDF·한 장 요약 (`out/media-kit/`). 숫자는 `tracking/` 실제 기록에서만 계산 | 실제 지표만, 가상 협업 시안 넣지 않기 |
| 운영 보드 | `python doha.py board` | `index.html`이 읽는 `board-data.js` 갱신 | 보드에서 고친 값은 그 브라우저(localStorage)에만 남음. 계정과 연결 안 됨 |

- `out/` 폴더는 git에 올라가지 않습니다. 다시 만들 수 있는 결과물이기 때문입니다. `out/prompts.md`처럼 기록으로 남길 파일은 따로 보관합니다. (근거: .gitignore, docs/04-compliance-checklist.md §10)
- 미디어킷 원칙: 완성된 협업 사례가 없으면 '가상 협업 시안'은 넣지 않습니다. (근거: research/ig-platform.md 운영 결론)
- 운영 보드는 게시·DM을 자동화하지 않고 계정·API에 연결돼 있지 않습니다. (근거: 00-master-plan.md §6)

---

## 2. 주간 배치 작업 (권장)

비슷한 작업을 묶어서 하면 전환 비용이 줄어듭니다. 게시 빈도는 콘텐츠 계획을 따르고, 품질이 떨어지면 빈도를 낮춥니다. (근거: 00-master-plan.md §3, §7)

현재 게시 일정은 `content/posts/`의 `date`·`time` 기준으로 **월·수·금 07:40, 일 20:30(주간 플랜)**입니다. 아래 표는 다음 주 게시물을 이번 주 수요일까지 승인해 두는 흐름입니다. (해석)

| 요일 | 할 일 | 명령 | 사람 확인 |
|---|---|---|---|
| **월** | 07:40 게시 · 무신사 '급상승 일간 랭킹 아카이브' 확인 → 다음 주 게시물 기획, 프롬프트 내보내기, 시안(앱)·확정 컷(API) 생성 | `new` → `prompts` → (ChatGPT 앱) → `generate --dry-run` | 소재 선택, 의상·장면 묘사, 비용 승인 |
| **화** | 이미지 선별, 렌더링, 검수 | `check` → `build` | 얼굴 일관성, 손·옷 왜곡, 글자 배치, `check` 오류 0 |
| **수** | 07:40 게시 · 휴대폰 미리보기, 최종 승인 | `preview` | 표시 문구·배지·캡션 첫 줄, `review.approved_by` |
| **목** | 브랜드 아웃리치(이메일·개별 DM), 미디어킷 갱신 | `media-kit` | 한 곳씩 직접 작성 |
| **금** | 07:40 게시 · 주간 리포트, 다음 주 주제 결정 | `metrics` | 저장·공유·팔로우 기준으로 판단 |
| **토** | 쉼. 분기 첫 주에는 규정 점검 | 없음 | docs/04-compliance-checklist.md §12 |
| **일** | 20:30 주간 플랜 게시 | 없음 (앱) | 표시·라벨 (아래 게시일 체크) |

게시일마다 하는 일

- 정해진 시각에 앱에서 직접 게시합니다. 유료 파트너십 레이블, 'AI 정보' 라벨, 대체 텍스트를 확인합니다 (docs/04-compliance-checklist.md). 기본 시각 07:40은 가설이며 성과로 조정합니다. (근거: config.yaml `publishing.default_time`)
- 날씨 숫자가 들어간 편(주간 플랜, 날씨형 훅)은 **게시 전날 기상청 예보로 숫자를 다시 확인**합니다. (근거: research/content-trends.md 운영 결론 7, docs/02-content-strategy.md §11-2)
- 게시 24시간 뒤, 7일 뒤: 지표 기록. 도달, 조회, 저장, 공유, 댓글, 프로필 방문, 팔로우, 링크 클릭, 제작 시간·비용. (근거: 00-master-plan.md §8)

매주 하는 일

- 계정 상태에서 추천 가능 여부 확인, 'AI 생성 프로필' 라벨이 켜져 있는지 확인. (근거: docs/06-account-setup.md §3, §4)
- 월요일: 무신사 '급상승 일간 랭킹 아카이브'로 소재 점검. 손으로 봅니다. 랭킹 데이터를 긁어 오지 않습니다(§6 스크래핑). (근거: research/content-trends.md §1-1, 운영 결론 11)
- 판단 지표: 공유/도달, 저장/도달. 팔로워 수나 조회수 하나로 판단하지 않습니다. (근거: research/ig-platform.md §6-3, 00-master-plan.md §8)

---

## 3. 이미지 생성: 두 가지 길

**시안은 ChatGPT 앱, 확정 컷과 협찬 컷은 API**로 나눕니다. 앱은 장당 추가 비용이 0원이라 후보 뽑기에, API는 비용·토큰·파일 기록이 남아 견적·정산 근거가 필요한 컷에 씁니다. (해석) (근거: research/image-gen-tech.md §7-1, 운영 결론) 자세한 기준·단가·예상 비용은 [03-image-production.md](03-image-production.md) §6.

| 항목 | ChatGPT 앱 (수동) | OpenAI API (`generate`) |
|---|---|---|
| 쓰는 곳 | 얼굴 기준 사진 후보, 게시물 시안. API 준비 전에는 일반 게시물 확정 컷까지 | 확정 컷, 협찬 컷, 앱 한도에 걸렸을 때 |
| 명령 | `python doha.py prompts <게시물>` → 앱에 붙여넣기 | `python doha.py generate <게시물> --only s01` |
| 비용 | **장당 추가 비용 없음.** 구독료는 따로 (03 §6-1) | **장당 비용 발생** (사용량 과금, 03 §6-2) |
| 사람 손 | 붙여넣기, 고치기, 내려받기, 파일 저장 (요령: brand/prompt-guide.md) | 명령 한 번, 실행 전 비용 확인 |
| 기록 | 대화 링크·캡처를 직접 보관, 구독료는 `costs.csv`에 손으로 | `tracking/costs.csv` 자동 기록 (금액·토큰 수) |
| 키 | 필요 없음 | `.env`의 `OPENAI_API_KEY` |

(근거: 00-master-plan.md §4, doha.py 명령 설명, research/image-gen-tech.md §2)

**API 비용 안전장치** (키트 설정값, 근거: config.yaml `image_generation`, .env.example)

| 설정 | 값 | 뜻 |
|---|---|---|
| `model` | `gpt-image-2` | 키트 기본 모델. 2.5-sunburst 비교 시험은 03 §6-5 |
| `size` | `1024x1536` | 세로 2:3. 3:4(1152x1536) 시험은 03 §6-5 |
| `quality` | `medium` | 시안은 medium, 확정 컷만 high |
| `token_prices_usd_per_1m` | text_input 5 / image_input 8 / image_output 30 | 응답 토큰 수로 **실제 금액**을 계산해 기록 (`usage-based`). 2026-10 공개 자료 값 [보도], 결제 전 OpenAI 가격 페이지에서 확인 |
| `est_cost_usd` | low 0.02 / medium 0.05 / high 0.17 | 실행 전 상한 계산용 **장당 예상치**. 응답에 사용량이 없을 때만 이 값으로 기록 (`estimate`) |
| `max_cost_per_run_usd` | 1.00 | 한 번 실행 상한. 넘으면 실행 거절 |
| `require_confirmation` | true | 비용 발생 전 터미널에서 y 입력 |
| `DOHA_MAX_COST_USD` (.env) | 1.00 | 실행 상한을 .env에서 덮어씀. `--max-cost`로도 지정 |

- 처음에는 `--dry-run`으로 프롬프트와 예상 비용만 봅니다. 그다음 한 장만 생성해 `costs.csv`의 실제 금액·토큰 수를 확인합니다. (근거: 00-master-plan.md §9)
- `--mock`은 API 없이 자리표시 PNG만 만듭니다(비용 기록 없음). 렌더링 테스트용입니다.
- gpt-image-2에는 `input_fidelity`를 보내지 않습니다. 입력 이미지를 항상 고충실도로 처리합니다 [확인]. 키트는 gpt-image-1 계열에만 보냅니다 (키트 동작). (근거: research/image-gen-tech.md §1-3, 검증 메모 #4)
- 선불 결제는 $10만 넣고, 자동 충전(설정 과정에서 기본으로 켜짐 [확인])은 끄거나 월 한도 $20 이하로 둡니다 (해석). 키트 상한과 y 확인은 2차 안전장치입니다. 자세한 내용은 03 §6-4. (근거: research/image-gen-tech.md §1-5, 운영 결론)
- 키는 채팅·문서에 붙여넣지 않고 `.env`에만 둡니다. (근거: .env.example)
- 단가, ChatGPT 플랜별 한도, 대안 이미지 도구, 영상 도구는 03-image-production.md §2-4, §6, §7-2에 정리돼 있습니다.
- 어느 길이든 결과는 사람이 검수한 뒤에만 `approved`로 바꿉니다.

---

## 4. Instagram API: 어디까지 쓰나

### 4-1. 쓸 경로: Instagram API with Instagram Login

| 항목 | 내용 | 근거 |
|---|---|---|
| Facebook 페이지 | 필요 없음 | [확인] research/ig-platform.md §6-1 |
| 권한 | `instagram_business_basic` (+ 게시하려면 `instagram_business_content_publish`). 인사이트 읽기 권한 이름은 (확인 필요) | [확인] §6-1 |
| 대상 계정 | 비즈니스·크리에이터. 개인 계정 불가 → **먼저 크리에이터 전환** | [확인] §6-1 |
| 접근 수준 | 내가 소유·관리하는 계정에만 쓰면 **Standard Access**. 앱 리뷰 불필요. 토큰은 앱 대시보드에서 발급 | [확인] §6-4 |
| 다른 사람 계정 | Advanced Access, 앱 리뷰, 비즈니스 인증 필요 → 하지 않음 | [확인] §6-4 |
| 호스트 | graph.instagram.com | [주장] §6-1 |

- 계정 하나만 운영하면 Instagram Login이 가장 간단합니다. (근거: research/ig-platform.md §6-1)
- 유료 파트너십 라벨 API 부착, 광고 포함 합산 지표는 Facebook Login 경로에서 제공된다는 보도가 있습니다. [보도] Instagram Login에서는 [미확인]. (근거: research/ig-platform.md §1-4, §6-1, §6-3)

### 4-2. 인사이트 지표

도하 기본 지표 세트: **views, reach, saved, shares, total_interactions, follows**. 파생 지표: shares/reach, saved/reach. (근거: research/ig-platform.md §6-3)

| 사실 | 신뢰도 |
|---|---|
| `impressions`는 v22.0에서 폐지, 2025-04-21부터 모든 버전 적용. 2024-07-02 이후 미디어에 요청하면 오류 → **views 사용** | [확인] |
| 2025-01-08 계정 지표 `profile_views`, `website_clicks` 등과 미디어 지표 `video_views` 폐지 | [확인] |
| '프로필 방문'을 API로 받을 수 있는지 | [미확인] |
| 데이터는 최대 48시간 늦게 반영, 최대 2년 보관 | [확인] |
| likes, comments, views, total_interactions는 오가닉 수치만 | [확인] |
| 2026-04 미디어에 `reposts_count`, `saved_count`, `shares_count` 필드 추가 | [보도] |

(근거: research/ig-platform.md §6-3)

### 4-3. 게시 API: 지금은 쓰지 않음

사실 (근거: research/ig-platform.md §4-1, §6-2, §3-1)

| 항목 | 내용 | 신뢰도 |
|---|---|---|
| 지원 형식 | 단일 이미지, 영상, 릴스, 캐러셀 | [확인] |
| 미디어 | **공개 URL**이어야 함. 컨테이너 생성 → (영상은 처리 상태 FINISHED 확인) → `media_publish` | [확인] |
| 게시 한도 | 가이드는 24시간 100건, 레퍼런스는 50건. 숫자를 코드에 박지 말고 `GET /{ig-user-id}/content_publishing_limit`로 조회 | [확인]/[주장] |
| 예약 | `scheduled_publish_time` 같은 예약 파라미터 없음. 자체 작업 큐가 필요 | [주장] |
| 캐러셀 장수 | API는 10장 [주장]. 앱은 20장 [보도] | 혼재 |
| 비율 | API는 4:5~1.91:1(공식 문서 구버전 기준). 3:4(1080×1440)는 거부되거나 잘릴 수 있음 → API로 올린다면 1080×1350 | [확인] |
| AI 라벨 파라미터 | 있는지 확인 못 함 | [미확인] |
| 유료 파트너십 라벨 | 앱에서만 추가 [확인]. 2026-04부터 Facebook Login 게시 API로 가능하다는 보도 [보도] | 혼재 |

그래서 자동 게시를 하지 않는 이유

1. 게시 전 사람 검수가 운영 원칙입니다. (근거: 00-master-plan.md §4, §7)
2. 'AI 정보' 라벨을 API로 붙일 수 있는지 모릅니다. 릴스는 라벨이 의무입니다. (근거: research/ig-platform.md §3-1)
3. 협찬 게시물의 유료 파트너십 레이블은 앱에서 붙이는 것이 확실한 방법입니다. (근거: research/ig-platform.md §1-4)
4. 이미지를 공개 URL로 올려 둘 호스팅이 따로 필요합니다. (근거: research/ig-platform.md §6-2)
5. 키트 기본 캔버스(3:4)가 API 비율 범위 밖일 수 있습니다. (근거: research/ig-platform.md §4-1, config.yaml `canvas`)

**예약이 필요하면**: Meta Business Suite의 예약 기능으로 **손으로** 예약합니다. 수동 예약은 API와 별개 기능입니다. [주장] 협찬·광고·제휴 게시물은 레이블 지원을 확인하기 전까지 앱에서 직접 올립니다. (근거: research/ig-platform.md §6-2, docs/06-account-setup.md §10)

**나중에 다시 검토할 조건** (근거: 00-master-plan.md §7 5단계)

- 운영량이 안정되고, API에서 AI 라벨·유료 파트너십 라벨을 붙일 수 있다고 직접 확인했을 때.
- 그때도 승인(`status: approved`)된 게시물만, 사람이 정한 시각에 올리는 범위로 제한합니다.

---

## 5. 지표 가져오기 (`insights`, 선택 기능)

**상태**: `doha/insights.py`로 구현돼 있지만 선택 기능입니다. 없어도 운영에 문제없습니다. 앱 인사이트를 보고 `tracking/metrics.csv`에 직접 적어도 됩니다.

```
python doha.py insights --dry-run      # CSV에 쓰지 않고 가져온 값만 보기 (처음엔 이것부터)
python doha.py insights                # 최근 30개 게시물 기준으로 기록 (--limit 으로 조정)
python doha.py insights --followers    # 팔로워 수도 tracking/followers.csv 에 기록
python doha.py insights --checkpoint 7d  # 경과 시간과 상관없이 이 시점 이름으로 기록
```

**하는 일**

- 내 계정의 최근 게시물 지표를 **읽기만** 합니다. 게시·수정·댓글은 하지 않습니다.
- `post.yaml`의 `posted.url`(릴스는 `posted.reel_url`)과 맞는 게시물을 찾아 `tracking/metrics.csv`에 한 줄씩 추가합니다.
- 게시 후 경과 시간으로 기록 시점(`24h` / `7d` / `30d`)을 정하고, 이미 기록한 (`post_id`, `checkpoint`, `format`)은 건너뜁니다.
- `impressions`는 쓰지 않고 `views`를 씁니다. (근거: research/ig-platform.md §6-3)

**준비**

1. 크리에이터 계정 전환 (docs/06-account-setup.md §2)
2. Meta 개발자 앱에서 Instagram API with Instagram Login 설정, 본인 계정으로 토큰 발급. 본인 계정만 쓰면 Standard Access, 앱 리뷰 불필요. [확인] (근거: research/ig-platform.md §6-4) 인사이트 읽기에 필요한 권한 이름은 (확인 필요).
3. `.env`에 `IG_ACCESS_TOKEN` 입력. `IG_USER_ID`는 비워 두면 토큰의 계정(`/me`)으로 조회합니다. 두 값 모두 `.env.example`에 자리가 있고, `.env`는 git에 올라가지 않습니다.
4. 토큰 유효기간과 갱신 방법 (확인 필요).

**주의**

- 데이터가 최대 48시간 늦게 반영됩니다. [확인] 24시간 시점 값은 덜 잡힐 수 있으니 앱 화면과 비교합니다. (근거: research/ig-platform.md §6-3)
- 지표는 하나씩 요청하고, 받지 못한 값은 빈 칸으로 남습니다. 완료율·링크 클릭은 요청하지 않습니다. 프로필 방문·평균 시청 시간은 요청하지만 API로 받을 수 있는지 [미확인]입니다. 빈 칸은 앱 인사이트에서 직접 채웁니다. (근거: research/ig-platform.md §6-3)
- 토큰을 채팅·문서·커밋에 넣지 않습니다.

---

## 6. 절대 자동화하지 않는 것

| 하지 않음 | 이유 | 대신 |
|---|---|---|
| **콜드 DM** (브랜드·사용자에게 먼저 보내는 대량·자동 DM) | 메시징 API는 사용자가 먼저 보낸 메시지에 24시간 안에만 답할 수 있다는 설명 [주장]. 먼저 연락하는 대량 DM은 공식 API로 불가, 제재 위험 큼. 동의 없는 상업 목적 반복 연락은 커뮤니티 가이드라인 위반 [확인] | 브랜드 아웃리치는 이메일 또는 한 곳씩 수동 DM |
| **자동 팔로우·언팔로우·좋아요·댓글** | 좋아요·팔로워·공유를 인위적으로 모으기, 반복 댓글 금지 [확인]. 서드파티 앱 자동화도 위반으로 본다는 설명 [주장] | 직접 댓글에 답하기 |
| **스크래핑** (경쟁 계정·브랜드 데이터 수집) | 승인받지 않은 수집은 계정 제한 가능 [확인]. 서면 허가 없는 봇·크롤러 금지라는 해설 [주장] | 공개 정보를 손으로 조사, `outreach/prospects.csv`에 직접 기록 |
| **팔로워·좋아요 구매** | 인위적 참여 금지 [확인]. 광고주는 팔로워 대비 참여율·실제 도달을 의심하고 확인 [주장] → 미디어킷 신뢰 하락 | 저장·공유를 만드는 콘텐츠 |
| **검수 없는 자동 게시** | 사람 검수 원칙, AI 라벨 API 지원 [미확인] | §4-3 |
| **체험단 대량 신청·자동 가입** | 체험 후기형 캠페인은 도하와 맞지 않음. 플랫폼의 AI·가상 계정 허용 여부 [미확인] | 약관 확인 후 한 곳씩 판단 |
| **AI 표시 제거** (워터마크·메타데이터 삭제) | 정부 대책에 이용자의 AI 표시 제거·변조 금지 도입 계획이 있음 [보도]. 아직 법이 되지 않음 | 그대로 둠 |

근거: research/ig-platform.md §6-5, 운영 결론 / research/sponsorship-kr.md §1-2, §1-3 / research/kr-compliance.md §2, §3 / 00-master-plan.md §7

- 커뮤니티 가이드라인 근거 자료는 2019년 법원 제출본이라 현행 문구와 다를 수 있습니다. (근거: research/ig-platform.md §6-5)
- 신규 AI 계정은 신뢰 신호가 약해 한 번 제재를 받으면 회복하기 어렵습니다. (해석) (근거: research/ig-platform.md 운영 결론)

### 6-1. 댓글 키워드 → DM: 조건부 예외 (지금은 쓰지 않음)

제휴 링크를 전하는 경로로 "댓글에 키워드를 남기면 링크를 DM으로 받는" 방식이 거론됩니다. (근거: research/affiliate-kr.md §2-10, 운영 결론) 콜드 DM과 다르지만 자동 발송이므로, 아래 조건을 **모두** 지킬 때만 씁니다.

| 조건 | 내용 | 근거 |
|---|---|---|
| 사용자가 먼저 | 사용자가 **먼저 단 댓글**(또는 먼저 보낸 메시지)에 대한 답장만 보냅니다. 댓글을 달지 않은 사람, 팔로워 전체, 브랜드에게 먼저 보내지 않습니다 | research/ig-platform.md §6-5 |
| 공식 경로만 | Instagram 공식 메시징 API, 또는 그 API를 쓰는 승인된 도구만 씁니다. 서드파티 앱으로 DM을 자동화하는 것도 위반으로 본다는 설명이 있습니다 [주장] | research/ig-platform.md §6-5 |
| 플랫폼 한도 | 메시징 API는 사용자가 먼저 보낸 메시지에 24시간 안에만 답할 수 있고, 댓글에 대한 비공개 답장은 댓글 하나당 1회·7일 이내만 가능하다는 설명 [주장] | research/ig-platform.md §6-5 |
| 시작 시점 | **처음에는 쓰지 않습니다.** 제휴 게시를 시작한 뒤(08-affiliate-guide.md §2), 프로필 링크 실측이 3개월 쌓이면 선택합니다 | 08-affiliate-guide.md §5 |
| 도구 확인 | 인포크링크에 인스타그램 자동화 기능이 있습니다 [확인]. 무료인지, 공식 API를 쓰는지는 [미확인] → 확인 전에는 켜지 않습니다 | research/affiliate-kr.md §2-11, 남은 확인 사항 |
| 표시 | DM 답장에도 캡션과 같은 대가성 문구와 AI 가상인물 표시를 넣습니다 (운영 규칙) | 문구: 08-affiliate-guide.md §4 |

- "DM 자동화 클릭률 12~18% vs 프로필 링크 2~3%"는 DM 자동화를 파는 업체의 자료입니다 [주장]. 이해관계가 있어 도입 근거로 쓰지 않습니다. (해석) (근거: research/affiliate-kr.md §4-2)
- 키트는 DM을 보내는 기능을 만들지 않습니다. 쓰게 되면 외부 도구 설정이고, 유료면 `tracking/costs.csv`에 `category: subscription`으로 적습니다.

---

## 7. 비밀값과 비용 관리

- [ ] `.env`는 `.env.example`을 복사해 만들고, 키·토큰은 여기에만 넣습니다. (근거: .env.example, .gitignore)
- [ ] API 비용은 `tracking/costs.csv`에 자동 기록됩니다. AI 툴 구독료 같은 다른 비용도 같은 파일에 손으로 적습니다.
- [ ] 월 순수익 = 협찬 계약금 + 제작비·사용권 수입 + 제휴 수수료 − 이미지/API·제작·광고 등 운영비. Meta 광고는 비용입니다. (근거: 00-master-plan.md §2)
- [ ] 환율은 `config.yaml` `fx.usd_krw`(1400)로 환산합니다. 실제 결제 환율로 가끔 갱신합니다.

---

## 확인 필요

1. Instagram 로그인 방식 토큰의 유효기간과 갱신 절차.
2. 크리에이터 계정으로 Instagram Login 게시가 실제로 되는지 (자동 게시를 다시 검토할 때만).
3. `content_publishing_limit` 실제 `quota_total` 값 (50 또는 100).
4. API로 게시한 미디어에 'AI 정보' 라벨을 붙이는 방법이 있는지.
5. Instagram Login 경로에서 유료 파트너십 라벨 API, 광고 포함 합산 지표가 되는지.
6. Meta Business Suite 예약 화면에서 AI 라벨·유료 파트너십 레이블 지원 여부 (docs/06-account-setup.md §10).
7. 최신 Instagram Platform changelog의 현재 API 버전과 `profile_views` 대체 지표.
8. `insights`에 필요한 Instagram Login 권한 범위(인사이트 읽기 포함)와 `profile_visits`·`ig_reels_avg_watch_time` 지표가 실제로 반환되는지.
9. 댓글 키워드 DM을 검토할 때: 인포크링크 등 도구의 인스타그램 자동화가 공식 메시징 API를 쓰는지, 무료인지, 메시징 API의 24시간·댓글 비공개 답장 1회·7일 조건이 지금도 같은지 (§6-1).
10. 이미지 생성 단가·한도·약관의 남은 확인 사항은 03-image-production.md '확인 필요'에서 관리합니다.
