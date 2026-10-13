# 게시물 파일 형식 (`post.yaml`)

게시물 하나는 폴더 하나입니다: `content/posts/<YYYY-MM-DD>-<슬러그>/`

```
content/posts/2026-10-15-black-slacks-3ways/
├── post.yaml        # 이 문서의 형식
├── images/          # 생성했거나 직접 넣은 사진 (s01.png …). 없으면 자리표시 이미지로 렌더링
└── out/             # 렌더링 결과 (git에 올리지 않음)
    ├── slides/01.png …      # 카드뉴스 (1080x1440)
    ├── reel/reel.mp4        # 릴스 (1080x1920)
    ├── reel/cover.png
    ├── caption.txt          # 붙여넣기용 캡션 (광고·AI 표시 포함)
    ├── contact-sheet.png    # 한눈에 보는 미리보기
    └── preview.html         # 휴대폰 화면 비율 미리보기
```

## 필드

```yaml
id: 2026-10-15-black-slacks-3ways   # 폴더 이름과 같게
date: 2026-10-15                     # 게시 예정일
time: "07:40"                        # 게시 예정 시각 (KST)
status: draft    # idea → draft → images → rendered → reviewed → approved → posted
series: 한 벌 3가지                  # 반복 시리즈 이름 (성과 분석 단위)
format: both     # carousel | reel | both
pillar: 돌려입기  # 콘텐츠 기둥: 돌려입기 | 컬러공식 | 비율 | 상황별 | 아이템가이드 | 협찬 | 제휴
goal: save       # 이 게시물의 1차 목표 지표: save | share | follow | click | reach
hook: "검은 슬랙스 하나로 3일 출근룩"   # 첫 문장 (커버·릴스 첫 장면·캡션 첫 줄)

disclosure:
  ai_persona: true     # 항상 true. 렌더러가 인물 슬라이드에 'AI 가상 인물' 배지를 붙임
  paid: false          # 금전 대가를 받음 → '광고'
  gifted: false        # 제품을 무상으로 받음 → '협찬'
  affiliate: false     # 제휴 링크/코드 수수료 → '제휴 링크 포함'
  brand: ""            # 대가를 준 브랜드명 (해당 시)
  # 하나라도 true면 렌더러가 커버 상단과 캡션 첫 줄에 표시를 자동으로 넣음

images:                 # 사진 목록. 키는 슬라이드·장면에서 참조
  s01:
    file: images/s01.png
    prompt: >-          # 장면 묘사만 쓴다. 인물 묘사·촬영 스타일은 brand/doha.yaml에서 자동으로 붙음
      full-body shot walking out of a minimal office lobby, ...
    outfit: >-          # 의상을 따로 적어 두면 코디 일관성 검수에 씀
      black wide-leg wool slacks, ivory crew-neck knit, camel loafers
    framing: full-body  # full-body | three-quarter | waist-up | detail | flatlay
    status: todo        # todo | generated | approved | rejected

slides:                 # 카드뉴스 순서대로
  - layout: cover       # cover | look | tip | compare | checklist | cta | product
    image: s01          # images의 키 (없으면 텍스트형 슬라이드)
    kicker: "출근룩 공식 01"
    title: "검은 슬랙스 한 벌로\n출근룩 3가지"   # \n 으로 줄바꿈 지정
    subtitle: "월·수·금, 상의만 바꿔요"
  - layout: look
    image: s02
    label: "LOOK 01 · 월요일"
    title: "아이보리 니트로 단정하게"
    items: ["아이보리 라운드 니트", "검은 와이드 슬랙스", "카멜 로퍼"]
    tip: "밝은 상의가 얼굴 쪽을 환하게 해줘요."
  - layout: tip
    number: "TIP"
    title: "…"
    body: "…"
    bullets: ["…", "…"]
  - layout: compare
    left:  { image: s03, label: "A", caption: "…" }
    right: { image: s04, label: "B", caption: "…" }
    verdict: "…"
  - layout: checklist
    title: "출근 전 30초 체크"
    checks: ["…", "…", "…"]
  - layout: product      # 협찬·제휴 제품. 사실 정보는 출처와 확인일 필수
    image: s05
    product: p1
  - layout: cta
    title: "저장해두고 출근 전에 꺼내보세요"
    body: "다음 편: …"

products:                # 협찬·제휴 제품 (없으면 빈 목록)
  - id: p1
    brand: "…"
    name: "…"
    price_krw: 59000
    facts: ["울 30% 혼방 (공식 상세페이지)"]
    source_url: "https://…"     # 공식 페이지
    checked_at: 2026-10-13      # 가격·소재 확인일
    link: "https://…"           # 제휴 링크 (있으면 disclosure.affiliate: true)

reel:
  audio: null            # 사용권 확인된 음원 파일 경로. null이면 무음 (앱에서 음원 추가 가능)
  scenes:
    - image: s01
      layout: reel-hook   # reel-hook | reel-look | reel-text | reel-end
      text: "검은 슬랙스 하나로\n3일 출근룩"
      seconds: 2.2
      motion: zoom-in     # zoom-in | zoom-out | pan-left | pan-right | still
    - image: s02
      layout: reel-look
      label: "MON"
      text: "아이보리 니트"
      seconds: 2.0
      motion: pan-right

caption: |
  (첫 줄은 hook. 광고 표시가 필요하면 렌더러가 첫 줄 앞에 자동 삽입)
  …
hashtags: [출근룩, 직장인코디, 슬랙스코디, 데일리룩, 오피스룩]   # config.publishing.max_hashtags 이하
alt_text: "…"            # 접근성 대체 텍스트 (앱의 고급 설정에 입력)

review:                  # 사람 검수 기록 (check 스크립트가 채우지 않음)
  approved_by: ""
  approved_at: ""
  notes: ""

posted:                  # 게시 후 기록 (insights 명령이 이 주소로 지표를 매칭)
  url: ""                # 카드뉴스(또는 단일) 게시물 주소
  reel_url: ""           # format: both 일 때 릴스 주소
  posted_at: ""
```

## 슬라이드 선택 필드

사진 구도에 맞춰 배치를 조정할 때만 씁니다.

| 필드 | 값 | 설명 |
|---|---|---|
| `focus` | `"50% 30%"` | 사진을 자르는 기준점 (CSS object-position). 숫자 하나면 세로 위치 |
| `tone` | `light` / `dark` | 사진 위 글자 색을 강제. 기본은 사진 밝기로 자동 |
| `text_position` | `top` / `bottom` | cover 제목 위치. 기본 `top` (사진 위쪽 1/3을 비워 두는 촬영 규칙) |
| `badge_position` | `left` / `center` / `right` | 'AI 가상인물' 배지 위치. 인물이 한쪽에 치우친 사진이면 인물 쪽으로 (공정위 지침: 인물 가까이 표시) |
| `title` | 문자열 | compare 레이아웃의 상단 제목 |
| `note` | 문자열 | checklist 하단 안내 문구 |

## 키트 이전 게시물 (`legacy: true`)

키트 없이 앱에서 직접 만든 게시물은 `legacy: true` 와 `posted.url` / `posted.reel_url` 만 적어 둡니다.
`insights` 가 이 주소로 성과를 연결하고, `check`·`render`·`reel` 은 건너뜁니다.
예: `content/posts/2026-10-12-first-drop-vector/post.yaml`

## 규칙

- 사진 안에 글자를 그리지 않습니다. 이미지 생성 → 렌더러가 글자 배치 순서입니다.
- 인물 사진이 들어간 슬라이드에는 렌더러가 `AI 가상 인물` 배지를 자동으로 붙입니다.
- `disclosure`의 `paid`/`gifted`/`affiliate` 중 하나라도 true면 커버와 캡션 첫 줄에 한국어 표시가 자동으로 들어갑니다. 끌 수 없습니다.
- `products`의 가격·소재·효능은 `source_url`과 `checked_at`이 없으면 검수(`check`)에서 실패합니다.
- 캡션·슬라이드에 "입어보니", "써보니", "제가 샀는데" 같은 체험 표현이 있으면 검수에서 실패합니다.
