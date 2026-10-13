# 도하(@doha.dailyfit) 운영 키트

AI 가상 스타일리스트 **도하** 계정을 키우고 브랜드 협찬·제작비·사용권·제휴 수수료로 수익을 내기 위한 작업 도구와 문서입니다.
기획 원본은 [docs/00-master-plan.md](docs/00-master-plan.md)입니다. 월 500만 원은 목표치일 뿐, 예상 수익이 아닙니다.

> 이 키트는 Instagram에 자동으로 게시하지 않고, DM·댓글·팔로우도 자동화하지 않습니다.
> 모든 게시물은 사람이 미리보기로 확인한 뒤 앱에서 직접 올립니다.

---

## 1. 오늘 할 일 (앱에서 직접)

자세한 순서와 확인 방법은 [docs/06-account-setup.md](docs/06-account-setup.md)에 있습니다.

1. **크리에이터(프로페셔널) 계정으로 전환합니다.** 인사이트는 전환한 뒤부터 쌓입니다.
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

모든 명령은 `python doha.py <명령>` 형식으로 실행합니다.

## 5. 매주 루틴

| 요일 | 할 일 |
|---|---|
| 월 | 이번 주 게시물 프롬프트 → 이미지 생성 → 얼굴·손·옷 품질 확인 ([docs/03](docs/03-image-production.md)) |
| 화 | `build` → 미리보기 확인 → 승인 (`post.yaml`의 `review`에 기록) |
| 월·수·금 07:40, 일 20:30 | 앱에서 게시 → `posted.url` 기록 |
| 게시 24시간·7일 뒤 | `insights` 또는 손으로 `tracking/metrics.csv` 기록 |
| 금 | 브랜드 후보 2~3곳 조사·연락 ([docs/05](docs/05-brand-outreach.md), `outreach/templates/`) |
| 매월 첫 주 | `metrics` 리포트 → 다음 달 시리즈 비중 결정, `media-kit` 갱신 |

## 6. 문서

| 문서 | 내용 |
|---|---|
| [01 수익화 플레이북](docs/01-monetization-playbook.md) | 수익 경로, 제작물(AI 룩북 컷+사용권) 판매 전략, 견적 워크시트, 500만 원 시나리오(가정), 단계 게이트, 90일 로드맵 |
| [02 콘텐츠 전략](docs/02-content-strategy.md) | 콘텐츠 기둥, 반복 시리즈, 게시 리듬, 훅 공식, 실험 방법, 4주 캘린더 |
| [03 이미지 제작](docs/03-image-production.md) | 실사 이미지 제작 흐름, 얼굴 일관성, 품질 검수표, 비용 관리 |
| [04 준수 체크리스트](docs/04-compliance-checklist.md) | 공정위 추천·보증 심사지침(2026-06-01 가상인물 표시), 광고·제휴 표시 문구, 세무 기초 |
| [05 브랜드 영업](docs/05-brand-outreach.md) | 타깃, 조사 방법, 연락 주기, AI 가상인물 질문 대응, 레드라인 |
| [06 계정 세팅](docs/06-account-setup.md) | 오늘 앱에서 할 일 10단계 |
| [07 자동화](docs/07-automation.md) | 자동화 범위, Instagram API(인사이트) 설정, 하지 말아야 할 자동화 |
| [research/](docs/research/) | 조사 원문(출처·신뢰도 표시). 플랫폼·법규·협찬 조사 완료, 나머지는 아래 참고 |

영업 템플릿: `outreach/templates/` (첫 DM, 이메일, 팔로업, 제안서, 견적서, 계약 체크리스트, 캠페인 리포트, 브리프 요청)

## 7. 폴더 구조

```
doha.py                 명령줄 도구 (doha/ 모듈)
config.yaml             캔버스 크기, 이미지 생성 비용 상한, 게시 설정
brand/doha.yaml         페르소나·말투·표시 문구·비주얼 바이블 (모든 도구의 기준)
content/posts/<날짜-슬러그>/post.yaml   게시물 (2026-10-15 리메이크 + 10/19~11/15 4주 16개)
templates/              카드뉴스·릴스·미디어킷·미리보기 템플릿
tracking/               metrics / followers / revenue / costs CSV
outreach/               prospects.csv(브랜드 후보), 영업 템플릿
index.html + board-data.js   운영 보드 (브라우저로 열기)
assets/fonts/           Pretendard, Noto Serif KR, Cormorant Garamond (OFL)
```

## 8. 아직 남은 것

- **사진:** 4주치 게시물 17개의 구성·문구·프롬프트는 준비돼 있지만, 사진은 아직 없습니다. 지금 렌더링하면 자리표시 이미지로 나옵니다. ChatGPT 앱이나 API로 이미지를 만든 뒤 다시 `build` 하세요.
- **추가 조사:** 제휴 프로그램(쿠팡 파트너스 등), 브랜드 후보 목록, 수익 사례(X 포함), 이미지 모델 가격, F/W 트렌드는 웹 검색 한도 때문에 이번에 끝내지 못했습니다. 결과가 나오면 `docs/research/`와 `outreach/prospects.csv`에 채웁니다.
- **API 연결(선택):** OpenAI 이미지 API와 Instagram 인사이트 API는 키·토큰을 `.env`에 넣어야 동작합니다. 이 환경에서는 네트워크가 막혀 실제 호출은 시험하지 못했습니다(모의 데이터로만 검증).

이 키트는 법률·세무 자문이 아닙니다. 계약·세금 신고 전에는 전문가에게 확인하세요.
