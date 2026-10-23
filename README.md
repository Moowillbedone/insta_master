# 도하(@doha.dailyfit) 운영 키트

AI 가상 스타일리스트 **도하** 계정을 키우고 브랜드 협찬·제작비·사용권·제휴 수수료로 수익을 내기 위한 작업 도구와 문서입니다.
기획 원본은 [docs/00-master-plan.md](docs/00-master-plan.md)입니다. 월 500만 원은 목표치일 뿐, 예상 수익이 아닙니다.

> **사람이 하루 한 번 승인한 글만 게시합니다.** X는 승인한 글을 정해진 시각에 API로 자동 게시하고(선택), Instagram은 미리보기 확인 뒤 앱 예약(기본) 또는 API 게시(시험 후)로 올립니다. 운영 방법은 [docs/10 자동 운영 런북](docs/10-autopilot.md)에 있습니다.
> 다른 사람 글에 자동 댓글, 자동 좋아요·팔로우, DM 자동화, 스크래핑은 하지 않습니다. 플랫폼 규칙 위반이라 계정 정지와 수익 자격 박탈로 이어집니다. 댓글은 매일 초안을 드리고, 링크를 누르면 앱에 채워진 채로 열립니다.

---

## 1. 오늘 할 일 (앱에서 직접)

자세한 순서와 확인 방법은 [docs/06-account-setup.md](docs/06-account-setup.md)에 있습니다.

1. **2단계 인증을 켠 뒤 크리에이터(프로페셔널) 계정으로 전환합니다.** 인사이트는 전환한 뒤부터 쌓입니다.
2. **'AI 생성 프로필' 라벨을 켭니다.** 2026-08-31 정책 변경으로, 라벨 없는 AI 인물 계정은 비팔로워 추천에서 빠질 수 있습니다. ([research/ig-platform.md §3-2](docs/research/ig-platform.md))
3. 소개글 첫 줄에 AI로 생성된 가상인물이라고 적습니다. 문구 3안은 docs/06에 있습니다.
4. 계정 상태 화면에서 '추천 가능' 여부를 확인합니다.
5. 기존 게시물 2개(2026-10-12)는 새 시안을 확인할 때까지 그대로 둡니다.

## 2. 처음 한 번 설치

먼저 이 폴더에 가상환경을 만들고 켭니다. 새 터미널을 열 때마다 켜는 줄만 다시 실행하세요.

```bash
# macOS (터미널) — 기본으로는 python 명령이 없고 python3 만 있어요
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell 또는 cmd)
py -m venv .venv
.venv\Scripts\activate
#   PowerShell 에서 '스크립트를 실행할 수 없으므로' 가 나오면 한 번만:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

가상환경을 켠 뒤에는 macOS·Windows 모두 `python` 으로 실행합니다.

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium     # 카드뉴스·미디어킷 렌더링용 브라우저
# ffmpeg 필요 (릴스): macOS `brew install ffmpeg` / Windows `winget install ffmpeg` (설치 뒤 새 터미널을 열어야 인식)
cp .env.example .env                      # API를 쓸 때만 (Windows cmd 는 copy .env.example .env). 키는 .env에만 두고 채팅에 붙여넣지 않기
```

## 3. 게시물 하나 만들기

```bash
python doha.py prompts black-slacks       # ① 이미지 프롬프트 → out/prompts.md
#   ChatGPT 앱에 붙여넣어 생성(추가 API 비용 없음) → images/s01.png … 로 저장
#   또는: python doha.py generate black-slacks --only s01 --dry-run   (API, 비용 확인 후 실행)
python doha.py build black-slacks         # ② 검수 → 카드뉴스 → 릴스 → 미리보기
#   out/preview.html 을 열어 휴대폰 화면처럼 확인 → 사람이 승인
#   out/caption.txt 를 앱에 붙여넣고, 빌드 끝에 나오는 체크리스트대로 게시
```

게시물 폴더에는 `post.yaml` 하나만 쓰면 됩니다. 형식은 [content/SCHEMA.md](content/SCHEMA.md)를 보세요. 새 게시물은 `python doha.py new "제목" --date 2026-11-20`으로 만듭니다.

**얼굴 일관성:** 처음에는 `python doha.py prompts --reference`로 얼굴 기준 사진 2~3장을 만들어 승인한 뒤 `brand/reference/`에 넣고, `brand/doha.yaml`의 `face_reference`에 등록합니다. 그 뒤로는 모든 생성이 이 사진을 기준으로 합니다. 지금 프로필 사진이 마음에 들면 그 사진을 기준으로 써도 됩니다. ([brand/reference/README.md](brand/reference/README.md), [brand/prompt-guide.md](brand/prompt-guide.md))

## 4. 명령 모음

| 명령 | 하는 일 |
|---|---|
| `new "제목" --date YYYY-MM-DD` | 새 게시물 폴더와 `post.yaml` 뼈대 만들기 |
| `prompts <게시물>` / `prompts --reference` | 이미지 프롬프트 내보내기 (API 비용 없음) |
| `generate <게시물> [--only s01] [--quality medium] [--dry-run]` | OpenAI API로 이미지 생성. 비용 상한과 확인 단계가 있고, 지출은 `tracking/costs.csv`에 기록 |
| `check <게시물>` / `check --all` | 광고·가상인물 표시, 체험 표현, 상품 출처, 글자 수 검수 |
| `render <게시물> [--size 4x5]` | 카드뉴스 PNG (기본 1080×1440, 3:4) |
| `reel <게시물>` | 릴스 MP4 (1080×1920) + 커버 |
| `preview <게시물>` | 붙여넣기용 캡션, 연락시트, 휴대폰 미리보기 |
| `build <게시물>` | check → render → reel → preview 한 번에 |
| `insights [--followers]` | Instagram API로 지표를 가져와 `tracking/metrics.csv`에 기록 (토큰 필요, 선택) |
| `metrics [--month 2026-10]` | 저장률·공유율·시리즈별 비교, 월 순수익 대비 목표 리포트 |
| `media-kit` | 브랜드 제안용 미디어킷 PDF·원페이지 이미지 (실제 지표만 사용) |
| `board` | 운영 보드 데이터 갱신 → `index.html`을 브라우저로 열기 |
| `ig-publish <게시물> [--dry-run] [--check-setup] [--refresh-token]` | 승인된 게시물을 Instagram API로 게시 (R2에 이미지를 잠시 올림, 4:5 JPEG로 변환). 기본 운영은 앱 예약이고, 이 명령은 시험 후 사용 |
| `x-new <날짜>` · `x-check <날짜>\|--all` | X 하루 대기열(`content/x/<날짜>.yaml`) 만들기·검수 (가중 글자 수, 링크·해시태그·멘션·참여 유도·체험 표현·중복·AI 이미지 표시) |
| `x-digest <날짜>` · `x-approve <날짜>` | 승인용 미리보기(휴대폰 카드, 댓글 초안 앱 링크) → 승인 |
| `x-publish --due` | 게시 시각이 된 승인 글만 API로 게시 (`publish_mode: manual`이면 앱 링크만 출력). 중복 게시 방지 |
| `daily-new` · `daily-check` · `daily-md <날짜>` | 매일 정보형 카드뉴스 패키지 뼈대·검수(출처·글자 길이·꼬리표·참여 유도·AI 표기)·ChatGPT용 package.md |
| `x-metrics` · `x-targets` | X 지표·팔로워 기록과 보상(OCR) 기준까지 남은 거리 / 지켜보는 계정의 최근 글을 댓글 초안 후보로 추가 (댓글은 사람이 직접) |

모든 명령은 `python doha.py <명령>` 형식으로 실행합니다.

## 5. 매주 루틴

| 요일 | 할 일 |
|---|---|
| 월 | 이번 주 게시물 프롬프트 → 이미지 생성 → 얼굴·손·옷 품질 확인 ([docs/03](docs/03-image-production.md)) |
| 화 | `build` → 미리보기 확인 → 승인 (`post.yaml`의 `review`에 기록) |
| 월·수·금 07:40, 일 20:30 | 앱에서 게시 → `posted.url` 기록 |
| 게시 24시간·7일 뒤 | `insights` 또는 손으로 `tracking/metrics.csv` 기록 |
| 금 | 브랜드 후보 조사, 연락은 5주 차부터 신규 주 5곳 안팎 ([docs/05](docs/05-brand-outreach.md), `outreach/templates/`) |
| 매월 첫 주 | `metrics` 리포트 → 다음 달 시리즈 비중 결정, `media-kit` 갱신 |

## 6. 문서

| 문서 | 내용 |
|---|---|
| [01 수익화 플레이북](docs/01-monetization-playbook.md) | 수익 경로, 제작물(AI 룩북 컷+사용권) 판매 전략, 견적 워크시트, 500만 원 시나리오(가정), 단계 게이트, 90일 로드맵 |
| [02 콘텐츠 전략](docs/02-content-strategy.md) | 콘텐츠 기둥, 반복 시리즈, 게시 리듬, 훅 공식, 실험 방법, 4주 캘린더 |
| [03 이미지 제작](docs/03-image-production.md) | 실사 이미지 제작 흐름, 얼굴 일관성, 품질 검수표, 비용 관리 |
| [04 준수 체크리스트](docs/04-compliance-checklist.md) | 공정위 추천·보증 심사지침(2026-06-01 가상인물 표시), 광고·제휴 표시 문구(프로그램별 포함), AI 툴 약관, 세무 기초, 분기별 규정 점검 |
| [05 브랜드 영업](docs/05-brand-outreach.md) | 타깃, 조사 방법, 연락 주기, AI 가상인물 질문 대응, 레드라인 |
| [06 계정 세팅](docs/06-account-setup.md) | 오늘 앱에서 할 일 11단계(보안 → 크리에이터 전환 → AI 생성 프로필 라벨 → 소개·링크 계획 등, 11번 지그재그 가입·문의는 선택) |
| [07 자동화](docs/07-automation.md) | 자동화 범위, Instagram API(인사이트) 설정, 하지 말아야 할 자동화 |
| [08 제휴 가이드](docs/08-affiliate-guide.md) | 제휴 프로그램 비교, 시작 순서, AI 가상인물 허용 문의 템플릿, 프로그램별 표시 문구, 링크 경로, 수수료 기록 |
| [09 X 플레이북](docs/09-x-playbook.md) | X 보상 프로그램(2026-09 Original Content Rewards)의 실제 조건과 기대 수익, 도하 페르소나로 운영하는 이유, 글 형식·게시 리듬·금지 사항, API/수동 게시와 'Automated' 라벨 선택 |
| [10 자동 운영 런북](docs/10-autopilot.md) | 하루 흐름(20:40 준비 → 승인 → 시각별 게시), 처음 한 번 설정(계정·환경 변수·허용 도메인), 루틴 프롬프트, 월 비용, 문제 해결 |
| [11 매일 카드뉴스](docs/11-daily-cardnews.md) | 정보형 계정용 매일 패키지: 트렌드 수집 → 선정 점수표 → 사실 확인 → ChatGPT 프롬프트·캡션. 요청할 때마다 그날 정보를 훑어 `content/daily/<날짜>/package.md`를 만들어 대화로 보냄 (예약 실행 없음) |
| [research/](docs/research/) | 조사 원문 13개(출처·신뢰도 표시): 플랫폼, 법규, 협찬, 제휴, 브랜드 후보(의류·잡화), 수익 사례, 이미지 기술·비용, 콘텐츠 트렌드(10-13) + X 보상·자동화 규칙·고수익 계정 패턴, 인스타 자동 게시(10-14). 각 문서의 '검증 메모'가 본문보다 우선 |

영업 템플릿: `outreach/templates/` (첫 DM, 이메일, 팔로업, 제안서, 견적서, 계약 체크리스트, 캠페인 리포트, 브리프 요청)

## 7. 폴더 구조

```
doha.py                 명령줄 도구 (doha/ 모듈)
config.yaml             캔버스 크기, 이미지 생성 비용 상한, 게시 설정
brand/doha.yaml         페르소나·말투·표시 문구·비주얼 바이블 (모든 도구의 기준)
content/posts/<날짜-슬러그>/post.yaml   게시물 (2026-10-15 리메이크 + 10/19~11/15 4주 16개)
content/x/<날짜>.yaml   X 하루 대기열 (샘플 10/20~10/22)
templates/              카드뉴스·릴스·미디어킷·미리보기 템플릿
tracking/               metrics / followers / revenue / costs CSV
outreach/               prospects.csv(브랜드 후보), 영업 템플릿
index.html + board-data.js   운영 보드 (브라우저로 열기)
assets/fonts/           Pretendard, Noto Serif KR, Cormorant Garamond (OFL)
```

## 8. 아직 남은 것

웹 조사는 끝났습니다(`docs/research/` 9개 문서, 2026-10-13). 결과는 운영 문서(`docs/`)에 반영했고, `outreach/prospects.csv`에 브랜드 후보 49곳(우선순위 A 11 · B 26 · C 12)을 채웠습니다. 남은 것은 조사로 풀 수 없는, 직접 해야 하는 일입니다.

- **사진:** 게시물 17개(10/15 리메이크 1개 + 10/19~11/15 4주치 16개)의 구성·문구·프롬프트는 준비돼 있지만, 사진은 아직 없습니다. 지금 렌더링하면 자리표시 이미지로 나옵니다. ChatGPT 앱이나 API로 이미지를 만든 뒤 다시 `build` 하세요.
- **계정 작업(앱):** 크리에이터 계정 전환, 'AI 생성 프로필' 라벨 켜기, 게시 화면의 'AI 정보'·유료 파트너십 레이블 위치 확인, 릴스 공유 화면에 'Add Products'(제휴 태그)가 보이는지 확인. 순서는 [docs/06](docs/06-account-setup.md), 앱에서 볼 항목은 [docs/04 '확인 필요'](docs/04-compliance-checklist.md)에 있습니다.
- **연락처·AI 수용 확인:** `prospects.csv` 49곳 중 47곳은 연락 경로가 아직 확인되지 않았습니다(44곳 "공식 사이트 문의 경로 확인 필요", 3곳은 창구 용도·공고 원문 확인 필요). 연락 전에 공식 사이트에서 문의 경로를 확인하고, 첫 연락에서 도하가 AI 가상인물임을 먼저 밝히고 협업 가능 여부를 확인합니다 ([docs/05](docs/05-brand-outreach.md)).
- **AI 가상인물 허용 문의:** 어느 제휴 프로그램에서도 AI 가상인물 계정을 허용·금지하는 문구를 찾지 못했습니다. 지그재그·무신사·네이버·쿠팡 고객센터에 문의하고 답을 보관한 뒤 시작합니다 ([docs/08 §3](docs/08-affiliate-guide.md)).
- **원문·전문가 확인:** 공정위 지침 원문(예규 번호, 사진 표시 위치), 화장품법 시행일, 세무 업종코드는 리서치로도 확정하지 못했습니다 ([docs/04 '확인 필요'](docs/04-compliance-checklist.md)).
- **자동 운영 설정:** X 계정·Premium 여부·개발자 계정(종량제 크레딧), Instagram API, Cloudflare R2, OpenAI 조직 인증은 사용자가 가입하고, 키는 클라우드 환경 설정의 환경 변수에 넣습니다(채팅에 붙여넣지 않기). 허용 도메인과 변수 이름은 [docs/10 §3](docs/10-autopilot.md)에 있습니다. 설정이 끝나면 Claude가 연결을 시험합니다. 예약 작업(루틴)은 만들지 않고, 사용자가 요청할 때 대화에서 실행합니다 (2026-10-23 사용자 결정).
- **API 실제 시험(선택):** OpenAI 이미지 API와 Instagram 인사이트 API는 키·토큰을 `.env`에 넣어야 동작합니다. 이 환경에서는 네트워크가 막혀 실제 호출은 시험하지 못했습니다(모의 데이터로만 검증). 처음에는 `generate --dry-run`과 1장 생성으로 비용·`size: 1152x1536` 허용 여부를 확인합니다 ([docs/03](docs/03-image-production.md)).

이 키트는 법률·세무 자문이 아닙니다. 계약·세금 신고 전에는 전문가에게 확인하세요.
