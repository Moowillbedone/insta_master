# Instagram 자동 게시와 AI 이미지 생성: 서버에서 어디까지 자동화할 수 있나 (2026-10-14 조사)

대상 계정은 @doha.dailyfit(AI 가상 스타일리스트, 출근룩)입니다. 서버나 클라우드 작업으로 "이미지 생성 → 게시"를 완전 자동으로 할 수 있는지, 아니면 휴대폰에서 한 번 눌러 승인하는 방식이 맞는지 조사했습니다.

- 조사 방법: 웹 검색 17회. x.com, developers.facebook.com 등은 직접 열지 못해 검색 결과에 나온 문서와 요약만 근거로 썼습니다. 저장소의 기존 조사(`docs/research/ig-platform.md`, `image-gen-tech.md`)와 겹치는 부분은 새 정보만 더했습니다.
- 신뢰도 표시: [확인] 공식·1차 자료, [보도] 언론 보도, [주장] 업체 블로그·포럼 등 자체 주장, [미확인] 근거를 찾지 못했거나 원문을 대조하지 못함. (해석)은 이 문서의 판단입니다.

---

## 0. 요약

1. **이미지 게시 API는 지금도 "공개 URL"을 요구합니다.** Instagram 로그인 방식(graph.instagram.com)에는 이미지 직접 업로드 경로가 없습니다. 재개형(resumable) 업로드는 공식 표에서 Facebook 로그인 방식의 영상 업로드용(rupload.facebook.com)으로만 나옵니다. 그래서 이미지를 잠시 공개 HTTPS 주소에 올려둘 곳이 필요합니다.
2. **현재 캐러셀 규격(1080×1440, 3:4)은 API로 올릴 수 없습니다.** 공식 규격은 JPEG, 8MB 이하, 비율 4:5~1.91:1입니다. 3:4(0.75)는 이 범위 밖이어서, API로 올리려면 `canvas.carousel_fallback`(1080×1350, 4:5)을 JPEG로 저장해야 합니다. 캐러셀은 API로 최대 10장입니다.
3. **유료 파트너십 라벨은 2026-04-22부터 API로 붙일 수 있습니다** (`is_paid_partnership`, `branded_content_sponsor_ids`). **'AI 정보' 라벨을 붙이는 공식 API 파라미터는 찾지 못했습니다.** AI 이미지를 API로 게시하면 AI 라벨이 빠질 수 있다는 점이 가장 큰 공백입니다.
4. **API에는 예약 게시 기능이 없습니다.** 대신 Instagram 앱 자체 예약(최대 75일)과 Meta Business Suite 예약을 무료로 쓸 수 있고, 앱에서는 AI 라벨과 유료 파트너십 라벨을 사람이 직접 켤 수 있습니다.
5. **OpenAI 이미지 API는 조직 인증(신분증·얼굴 인증)이 필요하고, 선불 결제는 최소 $5에 1년 뒤 만료됩니다.** high 품질은 한 장에 2~5분 걸린다는 측정이 있습니다. 저장소 `doha/imagegen.py`의 타임아웃 300초는 high 품질에서 빠듯합니다.
6. **결론 (해석):** 완전 무인 게시는 권하지 않습니다. 기본 방식은 서버가 밤에 생성·렌더·검수를 끝내고, 사람이 아침에 휴대폰으로 확인한 뒤 앱에서 라벨을 켜고 예약하는 것입니다(1건당 2~3분). API로 한 번에 승인해 게시하는 방식은 AI 라벨 문제를 시험으로 해결한 뒤 협찬이 아닌 이미지 게시물에만 씁니다.

---

## 1. Instagram API with Instagram Login으로 게시하기 (2026년 기준)

### 1-1. 로그인 방식과 권한

| 항목 | Instagram 로그인 | Facebook 로그인 | 근거 |
|---|---|---|---|
| 호스트 | graph.instagram.com | graph.facebook.com, 영상 재개형 업로드는 rupload.facebook.com | [확인] [출처](https://developers.facebook.com/docs/instagram-platform/content-publishing/) |
| 토큰 | Instagram User 액세스 토큰 | Facebook Page 액세스 토큰 | [확인] [출처](https://developers.facebook.com/docs/instagram-platform/content-publishing/) |
| 게시 권한 | `instagram_business_basic` + `instagram_business_content_publish` | `instagram_content_publish` + 페이지 권한 | 기존 조사 [확인] ([ig-platform.md §6](ig-platform.md)) |
| Facebook 페이지 | 필요 없음 | 필요 | 기존 조사 [확인] |

- 옛 권한 이름(`business_content_publish` 등)은 2025-01-27에 `instagram_business_*`로 바뀌었다는 개발 가이드가 있습니다 [주장] [출처](https://www.postzen.dev/blog/instagram-api-integration-guide).
- 내 계정에만 쓰는 앱은 Standard Access로 충분하고 앱 리뷰가 필요 없습니다. 토큰은 앱 대시보드에서 본인 계정으로 받을 수 있습니다 [확인] [출처](https://developers.facebook.com/documentation/instagram-platform/app-review).
- (해석) @doha.dailyfit은 Facebook 페이지 없이 운영하므로 Instagram 로그인 방식이 맞습니다. 저장소의 `doha.py insights`가 쓰는 `IG_ACCESS_TOKEN`에 게시 권한까지 넣으면 같은 토큰을 게시에도 쓸 수 있습니다.

### 1-2. 미디어 전달: 공개 URL이 필요한가

- **이미지:** 컨테이너를 만들 때 `image_url`로 공개 주소를 넘깁니다. Meta 서버가 이 주소에서 파일을 가져갑니다. 가져오지 못하면 오류 코드 9004, 하위 코드 2207052("media could not be fetched")가 나고, Meta는 주소가 유효하고 공개돼 있는지 확인하라고 안내합니다 [확인] [출처](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/error-codes).
  - 흔한 원인은 200이 아닌 응답, 잘못된 Content-Type, 0바이트 파일이라는 정리가 있습니다. 인증 없이 `curl`로 열어 200과 `image/jpeg`가 나오는지 먼저 확인하라고 권합니다 [주장] [출처](https://www.postpeer.dev/errors/instagram).
  - 이미지를 직접 올리는(바이트 전송) 경로는 공식 문서와 검색 어디에서도 찾지 못했습니다 [미확인]. (해석) 이미지에는 공개 URL이 필수라고 보고 설계합니다.
- **영상·릴스 재개형 업로드:** `upload_type=resumable`로 컨테이너를 만들면 rupload.facebook.com 주소가 돌아오고, 거기에 영상 바이트를 직접 보낸 뒤 `status_code`가 FINISHED가 되면 게시합니다. 이 방식이면 영상을 공개 URL에 올리지 않아도 됩니다 [주장] [출처](https://github.com/bugraskl/n8n-instagram-reels-publisher), [출처](https://github.com/deegitech/ig-publish).
  - 하지만 공식 표에는 rupload가 Facebook 로그인 방식에만 나옵니다 [확인] [출처](https://developers.facebook.com/docs/instagram-platform/content-publishing/). 재개형 업로드는 Facebook Login for Business가 필요하다는 개발 이슈도 있습니다 [주장] [출처](https://github.com/A-Baji/ClipMorph/issues/249).
  - (해석) Instagram 로그인 방식으로 릴스를 올리려면 MP4도 공개 URL에 잠시 올려야 합니다. 재개형 업로드가 꼭 필요하면 Facebook 페이지를 만들고 Facebook 로그인으로 바꿔야 합니다.
- 컨테이너는 만든 뒤 24시간 안에 게시하지 않으면 만료된다는 설명이 검색 요약에 있었지만, 원문은 확인하지 못했습니다 [미확인].

### 1-3. 이미지 규격과 캐러셀

| 항목 | 내용 | 근거 |
|---|---|---|
| 형식 | **JPEG만** 지원 (MPO, JPS 같은 확장 JPEG 불가) | [확인] [출처](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/) |
| 용량 | 최대 8MB | [확인] 같은 출처 |
| 가로 폭 | 320~1440px | [확인] 같은 출처 |
| 비율 | **4:5 ~ 1.91:1** | [확인] 같은 출처 |
| 색 공간 | sRGB | [확인] 같은 출처 |
| 캐러셀 장수 | 최대 10장 (사진·영상 섞기 가능). 앱은 20장 | API: [확인] [출처](https://developers.facebook.com/docs/instagram-platform/content-publishing/) · 앱: 기존 조사 [보도] |
| 캐러셀 비율 | 첫 장 비율에 맞춰 나머지가 잘린다는 설명 | [주장] (검색 요약에서 출처를 특정하지 못함) |
| 게시 한도 계산 | 캐러셀은 1건으로 계산 | 기존 조사 [확인] |

- **3:4는 안 됩니다 (해석).** 3:4는 0.75로 4:5(0.8)보다 세로가 깁니다. 공식 허용 범위 밖이라 API로 1080×1440을 보내면 거부될 가능성이 높습니다.
- 몇몇 업체 문서는 PNG·GIF 지원이나 9:16~16:9 범위를 적고 있지만, 공식 문서와 다릅니다. 공식 문서를 따릅니다 [주장] [출처](https://www.ayrshare.com/docs/media-guidelines/instagram), [출처](https://publishq.com/instagram-limits).
- **저장소에 바로 적용할 것 (해석):** API로 올리는 게시물은 `config.yaml`의 `canvas.carousel_fallback`(1080×1350)으로 렌더링하고, PNG를 sRGB JPEG(품질 90 안팎, 8MB 이하)로 바꿔 올립니다. 앱으로 올리는 게시물은 지금처럼 1080×1440을 씁니다.

### 1-4. 릴스

- `media_type=REELS`로 컨테이너를 만듭니다. 영상 처리가 끝날 때까지 `status_code`를 확인한 뒤 게시합니다 [확인] [출처](https://developers.facebook.com/docs/instagram-platform/content-publishing/).
- 공식 레퍼런스에 있는 릴스 옵션 [확인] [출처](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media):
  - `share_to_feed`: true면 피드와 릴스 탭 모두, false면 릴스 탭에만 표시.
  - `thumb_offset`: 커버로 쓸 프레임 위치(밀리초, 기본 0).
  - `cover_url`: 별도 커버 이미지. `thumb_offset`과 함께 보내면 `cover_url`이 우선합니다.
  - `trial_params`: 시험용 릴스(Trial reels). `media_type`이 REELS일 때만 씁니다.
- 커버는 1080×1920을 권하는 가이드가 있습니다 [주장] [출처](https://postproxy.dev/blog/instagram-reels-api-publishing-guide/). 문서상 커버는 JPEG만 되지만 PNG 커버도 실제로 됐다는 개발자 테스트가 있습니다 [주장] [출처](https://github.com/gitroomhq/postiz-app/pull/1855).
- 이미지 대체 텍스트(`alt_text`)를 API로 넣을 수 있는지는 공식 근거를 찾지 못했습니다 [미확인].

### 1-5. 예약과 게시 한도

- API에는 Facebook 페이지의 `scheduled_publish_time` 같은 예약 파라미터가 없습니다. 정해진 시각에 직접 게시 호출을 보내는 작업 큐가 필요합니다. 기존 조사 [주장] ([ig-platform.md §6-2](ig-platform.md))
- 게시 한도는 공식 가이드상 24시간 이동 창 기준 100건이지만, 레퍼런스에는 50건으로 남아 있다는 지적도 있습니다. 숫자를 코드에 넣지 말고 `GET /{ig-user-id}/content_publishing_limit`로 조회합니다. 기존 조사 [확인]/[주장] ([ig-platform.md §6-2](ig-platform.md)), [주장] [출처](https://github.com/A-Baji/ClipMorph/issues/249)
- (해석) 하루 1~2건 게시하는 도하에게 한도는 문제가 되지 않습니다. 오히려 재시도할 때 **같은 게시물이 두 번 올라가는 것**을 막는 장치가 더 중요합니다. 중복 게시 방지를 기능으로 내세운 오픈소스 게시 도구가 있다는 점도 이 문제가 실제로 있다는 신호입니다 [주장] [출처](https://github.com/deegitech/ig-publish).

### 1-6. 라벨: 유료 파트너십, AI 정보, 계정 라벨

**유료 파트너십 라벨: API로 가능 (2026-04-22부터)**

- Meta는 2026-04-22 개발자 블로그에서 Content Publishing API로 유료 파트너십 라벨을 붙일 수 있게 됐다고 발표했습니다 [확인] [출처](https://developers.facebook.com/blog/post/2026/04/22/instagram-api-updates-for-partnerships-metrics-collaboration-and-engagement/).
- 변경 기록에는 미디어 생성 엔드포인트의 새 파라미터 두 개가 있습니다 [확인] [출처](https://developers.facebook.com/documentation/instagram-platform/changelog):
  - `is_paid_partnership`: 브랜드를 지정하지 않고도 라벨을 켭니다.
  - `branded_content_sponsor_ids`: 브랜드 파트너를 최대 2개까지 Instagram 사용자 ID로 지정합니다.
- 사진, 릴스, 캐러셀, 스토리에 쓸 수 있고, 브랜드 ID는 Business Discovery API로 찾습니다 [보도] [출처](https://www.socialsamosa.com/news-2/meta-instagram-api-features-branded-content-analytics-11760299), [출처](https://www.socialmediatoday.com/news/meta-expands-instagram-management-apis/818385/).
- 그전까지는 예약 도구로 올린 뒤 앱에서 라벨을 손으로 붙여야 했습니다 [보도] [출처](https://almcorp.com/blog/meta-expands-instagram-management-apis/).
- 이 파라미터가 Instagram 로그인 방식(graph.instagram.com)에서도 되는지는 확인하지 못했습니다 [미확인]. 첫 협찬 전에 테스트 게시로 확인해야 합니다.
- 한국 법 기준으로는 라벨과 별개로 캡션 첫 줄의 '광고' 표기와, 2026-06-01부터 시행된 공정위 지침의 '가상인물' 표시가 여전히 필요합니다 [확인] [출처](https://www.law.go.kr/LSW/admRulInfoR.do?admRulSeq=2100000280130).

**'AI 정보' 라벨: 공식 API 파라미터를 찾지 못함**

- 공식 Content Publishing API에서 AI 라벨을 켜는 파라미터는 이번 검색에서 나오지 않았습니다 [미확인].
- 서드파티 게시 API인 Ayrshare는 `isAIGenerated` 옵션으로 'AI info' 라벨을 붙인다고 문서화했습니다. 캐러셀 전체에 라벨 하나가 붙는다고 합니다 [주장] [출처](https://www.ayrshare.com/docs/apis/post/social-networks/instagram). 이 업체가 어떤 Meta 경로를 쓰는지는 알 수 없습니다. (해석) Meta 쪽에 비공개 또는 파트너 전용 경로가 있을 수 있습니다.
- Meta는 C2PA, IPTC 같은 AI 메타데이터를 감지하거나 게시자가 직접 밝히면 라벨을 붙입니다 [확인] [출처](https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/), [주장] [출처](https://www.cleanaiapp.com/blog/instagram-made-with-ai-label-explained).
- (해석) 도하 파이프라인은 생성 이미지를 카드뉴스로 다시 렌더링하므로 원본 메타데이터가 사라질 가능성이 높습니다. 자동 감지에 기대면 안 됩니다.
- 게시물 라벨 이름이 'AI info'에서 'AI content'로 바뀌었다는 서드파티 글이 있습니다 [주장] [출처](https://www.privyclean.app/instagram-ai-creator-label). 한국어 메뉴 이름은 앱에서 확인해야 합니다.

**계정 단위 AI 라벨 (2026년 변화)**

- 2026-05 Instagram이 계정 단위 'AI creator' 라벨을 선택 사항으로 시험하기 시작했습니다. 시험 기간에는 배포에 영향이 없다고 했습니다 [보도] [출처](https://www.mediapost.com/publications/article/414862/instagram-unveils-new-ai-creator-account-label.html), [출처](https://www.engadget.com/2162426/instagram-is-testing-optional-ai-creator-labels/), [출처](https://www.socialmediatoday.com/news/instagram-adds-ai-creator-labels/819267/).
- 2026-08 이 라벨이 'AI generated profile'로 바뀌었고, **라벨을 달지 않은 AI 콘텐츠 계정은 도달이 줄 수 있다**는 법률사무소 블로그가 있습니다. 5월의 "영향 없음" 발표와 다르므로 확인이 필요합니다 [주장] [출처](https://blog.galalaw.com/post/102o37h/instagrams-2026-ai-labelling-rules).
- (해석) 계정 라벨은 프로필 설정에서 한 번만 켜면 되므로 자동화와 상관없습니다. 게시물 단위 라벨이 문제입니다.

### 1-7. 토큰 수명과 갱신

- 장기 토큰은 60일 유효합니다. `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=...`로 갱신하면 갱신 시점부터 다시 60일입니다 [확인] [출처](https://developers.facebook.com/documentation/instagram-platform/reference/refresh_access_token).
- 갱신 조건: 발급 후 24시간이 지났고 아직 만료되지 않아야 합니다. `instagram_business_basic` 권한이 필요합니다. 60일 동안 갱신하지 않으면 만료되고 다시 갱신할 수 없습니다 [확인] 같은 출처.
- 응답에는 새 `access_token`과 남은 초(`expires_in`)가 들어 있습니다. 비공개 계정 토큰도 이제 갱신된다고 적혀 있습니다 [확인] 같은 출처.
- 갱신 뒤에도 이전 토큰을 원래 만료일까지 쓸 수 있다는 블로그가 있습니다 [주장] [출처](https://www.getfishtank.com/blog/renewing-instagram-access-token). 30~45일마다 갱신하라는 권고도 있습니다 [주장] [출처](https://www.getfishtank.com/blog/renewing-instagram-access-token).
- (해석) 서버에서는 주 1회 갱신하고 `expires_in`이 14일 미만이면 알림을 보내도록 합니다. 새 토큰은 `.env`가 아니라 서버의 비밀 저장소에 덮어씁니다. 토큰이 만료되면 게시와 `insights`가 함께 멈춥니다.

### 1-8. 캐러셀 게시 호출 순서 (참고)

공식 문서의 컨테이너 → 게시 2단계 흐름입니다 [확인] [출처](https://developers.facebook.com/docs/instagram-platform/content-publishing/). 버전 번호는 그때의 최신 버전을 씁니다.

```
1) 장마다 (최대 10회)
   POST https://graph.instagram.com/v{버전}/{IG_USER_ID}/media
        image_url=<공개 JPEG URL>  is_carousel_item=true
2) 캐러셀 컨테이너
   POST .../{IG_USER_ID}/media
        media_type=CAROUSEL  children=<1)의 id 목록>  caption=<캡션>
        (협찬이면) is_paid_partnership=true  branded_content_sponsor_ids=[...]   ← 1-6의 [미확인] 참고
3) 상태 확인:  GET .../{컨테이너 id}?fields=status_code   → FINISHED
4) 게시:      POST .../{IG_USER_ID}/media_publish  creation_id=<2)의 id>
5) 게시 전후: GET .../{IG_USER_ID}/content_publishing_limit
```

---

## 2. 이미지를 잠깐 공개 HTTPS 주소에 올려두는 방법

API에 넘길 JPEG를 몇 분~몇 시간만 공개하면 됩니다. 게시가 끝나면 지웁니다.

| 방법 | 장점 | 주의할 점 | 판단 (해석) |
|---|---|---|---|
| **Cloudflare R2 + 내 도메인** | 공식 문서가 운영용으로 권하는 방식. 캐시, WAF, 접근 제어를 쓸 수 있음 [확인] [출처](https://developers.cloudflare.com/r2/buckets/public-buckets/) | 도메인이 필요함. 무료 구간과 요금은 이번에 확인하지 않음 [미확인] | **1순위.** 추측하기 어려운 경로(`/p/<랜덤>/01.jpg`)에 올리고 게시 후 삭제 |
| R2 `r2.dev` 주소 | 도메인 없이 바로 공개 | 테스트용이고 운영용이 아님. 속도 제한이 변동되고 넘으면 429, 대역폭도 제한될 수 있음 [확인] [출처](https://developers.cloudflare.com/r2/platform/limits). 분당 1,000건이라는 비공식 수치는 공식 설명("변동")과 다름 [주장] | 첫 테스트에만 사용 |
| S3 등 서명 URL(presigned) | 버킷을 공개하지 않아도 됨 | Meta가 인증 없이 GET으로 가져가므로 서명이 살아 있으면 될 가능성이 있음 (해석, 공식 근거 없음 [미확인]). S3 주소에서 같은 오류가 간헐적으로 났고 CloudFront로 우회했다는 포럼 글 [주장] [출처](https://developers.secure.facebook.com/community/threads/269924622604896/) | 2순위. 만료는 넉넉히(1시간 이상) |
| GitHub 공개 저장소 raw 주소 | 무료 | raw 주소는 정적 파일 서버가 아니며, 핫링크로 인기가 많아진 콘텐츠를 막은 적이 있음 [확인] (2013 글) [출처](https://github.blog/2013-04-24-heads-up-nosniff-header-support-coming-to-chrome-and-firefox/). 2025년에 비인증 요청 속도 제한이 강화됐다는 보도 [보도] [출처](https://roboin.io/article/2025/06/05/github-updated-rate-limits-for-unauthenticated-requests), 429를 받았다는 사례 [주장] [출처](https://github.com/orgs/community/discussions/157940) | **비권장.** 아직 게시하지 않은 시안과 커밋 기록이 영구히 공개됨 (해석) |
| Imgur 등 이미지 호스팅 | 무료 | 이번 조사에서 약관과 API 조건을 확인하지 않음 [미확인] | 비권장 |

- 어떤 방법을 쓰든 게시 직전에 `curl -I <URL>`로 200, `Content-Type: image/jpeg`, 0이 아닌 크기를 확인하는 단계를 넣습니다 [주장] [출처](https://www.postpeer.dev/errors/instagram).

---

## 3. 코딩 없이 쓰는 대안: 앱 예약과 Meta Business Suite

| 항목 | Instagram 앱 예약 | Meta Business Suite (웹·앱) |
|---|---|---|
| 대상 | 프로페셔널(크리에이터·비즈니스) 계정 [보도] [출처](https://techcrunch.com/2022/11/08/instagram-scheduling-tool-all-professional-accounts/) | 연결된 Instagram 프로페셔널 계정 |
| 형식 | 사진, 영상, 캐러셀, 릴스 [보도] [출처](https://www.searchenginejournal.com/instagram-lets-users-schedule-posts-reels-in-the-app) | 피드·캐러셀은 '게시물 만들기', 릴스는 '릴스 만들기' [주장] [출처](https://posteverywhere.ai/blog/how-to-schedule-instagram-reels-and-posts), [출처](https://postfa.st/blog/how-to-schedule-instagram-posts-from-desktop) |
| 예약 기간 | 최대 75일, 하루 25건 [보도] [출처](https://techcrunch.com/2022/11/08/instagram-scheduling-tool-all-professional-accounts/), [출처](https://www.searchenginejournal.com/instagram-lets-users-schedule-posts-reels-in-the-app). 2026 가이드도 75일 [주장] [출처](https://socialbee.com/?p=66464) | 29일이라는 글과 75일이라는 글이 엇갈림 [주장] [출처](https://blog.oneupapp.io/schedule-facebook-and-instagram-posts-more-than-29-days-into-future/), [출처](https://superprofile.bio/compare/instagram-schedulers) |
| 경로 | 게시물 작성 → 고급 설정 → '이 게시물 예약' [보도] [출처](https://www.searchenginejournal.com/instagram-lets-users-schedule-posts-reels-in-the-app) | 게시물 만들기 → 게시 대상 선택 → 미디어·캡션 → 예약 옵션 → 예약 [주장] [출처](https://helpdeskgeek.com/how-to-schedule-an-instagram-post-with-meta-business-suite/) |
| 유료 파트너십 라벨 | 앱에서 추가 가능 [확인] [출처](https://help.instagram.com/1109894795810258) | 확인 못 함 [미확인] |
| AI 라벨 | 앱 게시 화면에서 켤 수 있음 (기존 조사) | 예약 화면에 AI 라벨 옵션이 있는지 근거를 찾지 못함 [미확인] |
| 공동 게시물(Collab) | 예약 불가 [주장] [출처](https://socialbee.com/?p=66464) | 예약 불가 [주장] 같은 출처 |

- (해석) 도하처럼 하루 1건, 라벨이 꼭 필요한 계정에는 **Instagram 앱 예약**이 가장 안전한 무료 경로입니다. 서버는 파일과 캡션만 준비하고, 휴대폰에서 업로드 → AI 라벨·(협찬 시) 유료 파트너십 켜기 → 예약까지 2~3분이면 끝납니다.
- (해석) Business Suite는 PC로 여러 건을 한꺼번에 예약할 때 편하지만, AI 라벨을 켤 수 있는지 먼저 확인해야 합니다. 안 되면 쓰지 않습니다.

---

## 4. OpenAI 이미지 API를 서버에서 돌릴 때

### 4-1. 조직 인증

- GPT Image 모델(gpt-image-1, gpt-image-2)은 API 조직 인증을 마쳐야 쓸 수 있습니다. 안 하면 403 "organization must be verified" 오류가 납니다 [주장] [출처](https://www.datacamp.com/tutorial/gpt-image-1), [출처](https://help.apiyi.com/en/gpt-image-2-api-organization-verified-error-fix-en.html), [출처](https://www.aifreeapi.com/en/posts/openai-image-generation-api-verification). OpenAI 공식 도움말 원문은 이번 검색에 나오지 않았습니다.
- 인증은 Persona가 대행하며 정부 발급 신분증과 얼굴 인증이 필요합니다 [주장] [출처](https://www.datacamp.com/tutorial/gpt-image-1).
- 인증 반영 시간은 "15분"부터 "1~24시간", "6~24시간"까지 자료마다 다릅니다 [주장] [출처](https://help.apiyi.com/en/gpt-image-2-organization-verification-stuck-fix-en.html), [출처](https://www.aifreeapi.com/en/posts/openai-image-generation-api-verification), [출처](https://wavespeed.ai/blog/posts/gpt-image-2-api-guide/). 신분증 하나로 90일에 조직 하나만 인증할 수 있다는 글도 있습니다 [미확인] (원문 대조 못 함).
- 포럼 사례 [주장]:
  - Persona 인증을 통과했는데도 계속 거부됐고, 지원팀이 재시도를 해줄 수 없다고 답했다 [출처](https://community.openai.com/t/passed-persona-verification-but-access-to-gpt-image-1-api-still-denied-due-to-internal-error/1290141).
  - 인증된 조직인데 403이 나서, 모델 제한이 없는 새 프로젝트를 만들어 해결했다 [출처](https://community.openai.com/t/unable-to-access-gpt-image-1-model-despite-verified-organization/1361163).
  - 만료된 인증 세션은 다시 열 수 없고 실패한 세션을 수동으로 풀어주지 않는다는 사례 [출처](https://community.openai.com/t/request-new-persona-verification-link/1352280), [출처](https://community.openai.com/t/organization-verification/1361663).
- (해석) 인증은 사용자가 직접 한 번만 하면 됩니다. 실패하면 되돌리기 어려우므로 신분증 이름과 계정 정보가 맞는지 확인한 뒤 진행합니다. 인증이 막혀도 시안 생성은 ChatGPT 앱으로 계속할 수 있습니다(기존 운영 원칙).

### 4-2. 선불 결제

- 최소 구매액은 $5, 기본값은 $10입니다. 구매한 크레딧은 **1년 뒤 만료**되고 연장되지 않습니다 [확인] [출처](https://help.openai.com/en/articles/8264644-setting-up-and-managing-prepaid-api-billing).
- 자동 충전은 설정할 때 기본으로 켜져 있습니다. 끌 수 있고, 켜두면 기준 잔액·충전 후 잔액·월 충전 상한을 정합니다. 최소 충전액은 $5입니다 [확인] 같은 출처.
- 크레딧은 원칙적으로 환불되지 않습니다(결제 오류, 무단 사용 등 예외 있음). 충전 상한은 사용·결제 이력에 따른 신뢰 등급으로 정해집니다 [확인] 같은 출처.
- (해석) **자동 충전은 끄고** $10만 넣어 시작합니다. 서버 작업이 반복 실행되다 잘못돼도 손실이 잔액 안에서 멈춥니다. 저장소의 `max_cost_per_run_usd: 1.00`과 함께 이중 안전장치가 됩니다.

### 4-3. 생성 시간과 타임아웃

| 조건 | 측정 시간 | 근거 |
|---|---|---|
| gpt-image-2, 1024×1024, high | 117~132초 (2026-09-07, 2회 측정) | [주장] [출처](https://ofox.ai/blog/gpt-image-2-slow-quality-parameter-2026/) |
| gpt-image-2, 1024×1024, low | 17~20초 (같은 측정) | [주장] 같은 출처 |
| gpt-image-2, 1024×1024, high | 중앙값 약 195초, p95 약 280초 | [주장] [출처](https://ofox.ai/blog/gpt-image-2-generation-failures-fixes/) |
| gpt-image-2, 1536×1024, high (기본값) | 약 235초 | [주장] [출처](https://help.apiyi.com/en/gpt-image-2-api-performance-tuning-quality-size-guide-en.html) |

- 공식 가이드는 2560×1440을 넘는 크기를 '실험적'으로 봅니다 [확인] [출처](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide). 공식 지연 시간 수치는 찾지 못했습니다 [미확인].
- "실패"로 보이는 사례 상당수가 OpenAI 오류가 아니라 중간 프록시의 시간 초과라는 분석이 있습니다. NGINX 기본 60초, Express 120초, Cloudflare 무료 100초 같은 한도에 걸린다고 합니다 [주장] [출처](https://ofox.ai/blog/gpt-image-2-generation-failures-fixes/).
- **저장소 점검 (해석):** `doha/imagegen.py`는 `OpenAI(timeout=300, max_retries=1)`입니다. high 품질 1024×1536이면 p95 근처라 시간 초과 → 재시도 → **이중 과금**이 날 수 있습니다. 서버 작업에서는 high일 때 타임아웃을 600초로 늘리고, 시간 초과 시 자동 재시도하지 않도록 바꾸는 것을 권합니다. 생성 요청은 웹 요청 처리 안(예: Cloudflare Worker 응답)이 아니라 백그라운드 작업에서 돌립니다.

---

## 5. 무인 게시의 위험과 권장 승인 흐름

### 5-1. 무인 게시의 위험

| 위험 | 내용 | 근거 |
|---|---|---|
| AI 라벨 누락 | API로는 AI 라벨을 켤 수 없고(1-6), 렌더링으로 메타데이터가 사라져 자동 라벨도 기대하기 어려움 | [미확인]·(해석) |
| 도달 감소 | 라벨 없는 AI 계정의 도달이 줄 수 있다는 2026-08 글 | [주장] [출처](https://blog.galalaw.com/post/102o37h/instagrams-2026-ai-labelling-rules) |
| 광고 표시 위반 | 협찬인데 유료 파트너십·'광고'·'가상인물' 표시가 빠지면 공정위 지침 위반 소지 | [확인] [출처](https://www.law.go.kr/LSW/admRulInfoR.do?admRulSeq=2100000280130) |
| 이미지 품질 | 얼굴 일관성, 손·옷 구조, 로고·글자 왜곡, 실제 상품과 다른 디테일. 기존 운영 원칙상 사람 검수 항목 | `docs/00-master-plan.md` (해석) |
| 기술 실패 | 토큰 만료, URL 가져오기 실패(9004), 시간 초과 재시도로 인한 중복 생성·중복 게시 | 1-2, 1-7, 4-3 |
| 되돌리기 어려움 | 게시 뒤 삭제해도 이미 노출·캡처될 수 있음 | (해석) |

- 공식 API가 아닌 방식(비밀번호로 로그인하는 봇, 브라우저 자동 클릭)은 이번 조사 범위 밖이고 계정 제재 위험이 있어 쓰지 않습니다 (해석).

### 5-2. 권장 흐름

**A안 (기본): 서버 준비 + 앱 예약 — 지금 바로 가능**

1. 밤 배치(서버 크론): `doha.py generate`(medium, 승인된 프롬프트만) → `doha.py build`(check → render → reel → preview).
2. 결과를 휴대폰으로 보냅니다: 연락시트 이미지, 붙여넣기용 캡션, `check` 결과(광고·AI 표시 경고).
3. 아침에 사람이 확인합니다. 문제가 있으면 반려 사유를 적어 재생성합니다.
4. 승인한 파일을 휴대폰에 내려받아 Instagram 앱에서 올립니다. **AI 라벨 켜기**, (협찬 시) 유료 파트너십 라벨, 캡션 첫 줄 표기를 확인한 뒤 '이 게시물 예약'으로 07:40에 예약합니다.
5. 다음 날 `doha.py insights`로 지표를 기록합니다.

**B안 (조건부): 한 번 눌러 승인하면 API로 게시**

- 조건: (1) 협찬이 아닌 이미지 게시물, (2) 4:5 JPEG, (3) **AI 라벨 문제 해결** — 예를 들어 API로 올린 게시물에 앱의 '수정' 화면에서 AI 라벨을 나중에 켤 수 있는지 시험해 확인 [미확인]. 확인 전에는 B안을 쓰지 않습니다.
- 흐름: 미리보기 알림의 [승인] 버튼 → 서버가 R2(내 도메인)에 JPEG 업로드 → `curl` 점검 → 컨테이너 생성 → FINISHED 확인 → 정해진 시각에 `media_publish` → `GET /{media-id}`로 게시 확인 → R2 파일 삭제 → 결과 알림.
- 안전장치: 게시물마다 고유 키를 두고, 이미 게시된 키는 다시 게시하지 않습니다. `media_publish` 시간 초과 시 재시도 전에 최근 게시물 목록을 먼저 조회합니다. 토큰은 주 1회 갱신합니다.

**C안: 완전 무인 게시 — 권하지 않음.** 승인 단계가 없으면 5-1의 위험을 하나도 막지 못합니다. 기존 운영 원칙("한 번에 게시물을 자동 공개하지 않는다")과도 맞지 않습니다.

---

## 운영에 바로 쓰는 결론

- **지금은 A안으로 운영합니다.** 서버가 생성·렌더·검수·미리보기까지 끝내고, 사람은 휴대폰에서 AI 라벨을 켜고 Instagram 앱 예약(최대 75일)으로 올립니다. 1건당 2~3분입니다.
- **API 게시를 시험할 때는 1080×1350(4:5) sRGB JPEG, 8MB 이하, 캐러셀 10장 이하로 만듭니다.** 1080×1440(3:4) PNG는 API 규격 밖입니다.
- **이미지 호스팅은 Cloudflare R2 + 내 도메인**을 씁니다. `r2.dev`는 첫 테스트에만 씁니다. GitHub raw 주소는 미공개 시안이 영구 공개되므로 쓰지 않습니다.
- **협찬 게시물은 API로 `is_paid_partnership`를 넣을 수 있게 됐지만(2026-04-22), Instagram 로그인 방식에서 되는지 확인 전까지는 앱에서 라벨을 붙입니다.** 캡션 첫 줄 '광고'와 '가상인물' 표시는 어느 경로든 필수입니다.
- **Instagram 장기 토큰은 60일**입니다. 주 1회 `refresh_access_token`으로 갱신하고, 만료 14일 전에 알림을 받게 합니다.
- **OpenAI 조직 인증은 사용자가 직접** 신분증·얼굴로 한 번 진행합니다. 선불은 $10, 자동 충전은 끕니다(크레딧은 1년 뒤 만료).
- **`doha/imagegen.py`의 타임아웃 300초를 high 품질에서는 600초로 늘리고, 시간 초과 때 자동 재시도를 막습니다.** 그대로 두면 이중 과금이 날 수 있습니다.
- **프로필에서 계정 단위 AI 라벨(AI creator / AI generated profile)을 켜 둡니다.** 게시물 라벨과 별개이며, 라벨 없는 AI 계정의 도달이 줄 수 있다는 보고가 있습니다.

## 남은 확인 사항

- [ ] API로 게시한 게시물에 앱 '수정' 화면에서 AI 라벨을 나중에 켤 수 있는지 (B안의 전제).
- [ ] 공식 Content Publishing API에 AI 라벨 파라미터가 있는지. Ayrshare `isAIGenerated`가 어떤 Meta 경로를 쓰는지.
- [ ] `is_paid_partnership`, `branded_content_sponsor_ids`가 graph.instagram.com(Instagram 로그인)에서도 되는지 테스트 게시로 확인.
- [ ] Instagram 로그인 방식에서 이미지·릴스의 직접(재개형) 업로드가 정말 안 되는지 최신 공식 문서로 확인.
- [ ] 3:4(1080×1440) JPEG를 API로 보냈을 때 실제 오류 메시지 (규격상 거부 예상).
- [ ] 캐러셀이 첫 장 비율로 잘리는지, 컨테이너 24시간 만료가 맞는지 공식 문서로 확인.
- [ ] `content_publishing_limit`의 실제 `quota_total` 값 (50 또는 100).
- [ ] Meta Business Suite 예약 화면에 AI 라벨과 유료 파트너십 옵션이 있는지, 예약 가능 기간이 29일인지 75일인지.
- [ ] 2026-08 'AI generated profile' 변경과 미표시 계정 도달 감소가 공식 발표인지.
- [ ] OpenAI 공식 도움말 기준 조직 인증 요건(한국 신분증 지원, 90일 제한), gpt-image-2 공식 지연 시간.
- [ ] OpenAI API 출력에 C2PA 메타데이터가 들어가는지, 카드뉴스 렌더링 뒤에도 남는지.
- [ ] S3 서명 URL과 R2 내 도메인 URL로 실제 게시 테스트 (9004 오류가 나는지).
- [ ] Cloudflare R2 무료 구간과 요금.
