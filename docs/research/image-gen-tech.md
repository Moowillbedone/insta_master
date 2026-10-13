# 가상인물 '도하' 이미지·영상 제작 기술과 비용 조사

- 기준일: 2026-10-13 (KST)
- 대상: @doha.dailyfit. 실사형 AI 가상인물 '도하'의 출근룩·데일리룩 카드뉴스와 릴스
- 범위: OpenAI 이미지 API, ChatGPT 구독 생성, 대안 이미지 모델, 이미지→영상 도구, 얼굴 일관성 기법, 약관·표시 의무, 추천 스택과 게시물당 비용
- **신뢰도 표시**: [확인] 공식·1차 출처 · [보도] 언론·2차 출처 · [주장] 업체·블로그·재판매사의 자기 주장 · [미확인] 확인 못 함 · (해석) 리서치 판단 · (가정) 계산용 가정
- **한계**: 웹 페이지 본문을 직접 열 수 없어 검색 결과 요약을 근거로 썼습니다. 가격은 대부분 제3자 추적 사이트 수치이고 자주 바뀝니다. 결제 전에 각 회사의 공식 가격 페이지에서 다시 확인해야 합니다.
- 환율: 1 USD = 1,400원 (`config.yaml`의 `fx.usd_krw`) (가정)

---

## 0. 요약

1. **OpenAI 이미지 모델은 2026-09에 한 세대 더 나왔습니다.** gpt-image-2(2026-04 출시)에 이어 `gpt-image-2.5-flare`(빠른 일반용)와 `gpt-image-2.5-sunburst`(정밀 편집용)가 2026-09-08에 API로 나왔다는 보도가 일치합니다(OpenRouter 등록은 09-09). 2.5의 토큰 단가는 텍스트 입력 $5, 이미지 입력 $8(캐시 $2), 이미지 출력 $30/100만 토큰으로 보도되고 flare와 sunburst가 같습니다. **gpt-image-2와 같은 단가라는 출처와 2배라는 출처가 엇갈립니다.** [보도] [출처](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare), [출처](https://tech-insider.org/chatgpt-images-2-5-gpt-image-2-5-launch-2026/), [출처](https://fal.ai/gpt-image-2.5)
2. **gpt-image-2 세로 1024×1536 한 장의 출력 비용은 low 약 $0.005, medium 약 $0.041, high 약 $0.165입니다.** 여러 사이트가 같은 수치를 OpenAI 예시로 인용합니다. 기준 사진 입력 비용은 따로 붙습니다. [보도] [출처](https://aireiter.com/blog/gpt-image-2-api-pricing), [출처](https://www.nemovideo.com/blog/gpt-image-2-pricing-breakdown)
3. **gpt-image-2는 입력 이미지를 항상 고충실도(high fidelity)로 처리합니다.** 그래서 `input_fidelity`는 보내지 않는 것이 공식 가이드의 설명입니다. 보내면 오류가 난다는 제3자 문서도 있습니다. 다만 API 레퍼런스에는 아직 `high`/`low`가 남아 있어 문서끼리 맞지 않습니다. [확인] [출처](https://developers.openai.com/api/docs/guides/image-generation), [출처](https://developers.openai.com/api/reference/resources/images/methods/edit)
4. **OpenAI 이미지(ChatGPT·Codex·API)에는 C2PA 메타데이터와 SynthID 워터마크가 들어갑니다.** 2026-05-19~20 발표입니다. [확인] [출처](https://developers.openai.com/api/docs/guides/content-provenance), [보도] [출처](https://thenextweb.com/news/openai-c2pa-synthid-ai-image-detection-watermark)
5. **Sora 2 API(Videos API와 sora-2·sora-2-pro 모델)는 2026-09-24에 종료됐습니다.** 2026-03-24에 종료 예고가 나왔고 공식 대체 모델은 없습니다. 릴스 영상 후보에서 뺍니다. [보도] [출처](https://techjacksolutions.com/ai-brief/openai-videos-api-sora-2-deprecated-september-2026/), [출처](https://twinailabs.com/en/blog/sora-api-shutdown-september-2026)
6. **영상은 Veo 3.1 Fast·Lite(1080p 초당 $0.08~0.12, 소리 포함)와 Kling 3.0 API(무음 1080p 초당 $0.112)가 현실적인 가격대입니다.** Veo 3.1 Lite 1080p $0.08은 여러 추적 사이트가 일치합니다. Kling 단가는 출처마다 다릅니다. [보도]/[주장] [출처](https://benchlm.ai/media-pricing/veo), [출처](https://aireiter.com/blog/kling-api-pricing)
7. **추정 비용**: API로 사진만 만들면 게시물 1건에 약 $1.6~2.2(약 2,300~3,100원), AI 영상 2컷을 더하면 약 $3.9~4.5(약 5,400~6,300원)입니다. 월 12건이면 약 2.8만~7.5만 원입니다. 목표 매출(월 500만 원)에 비하면 도구비는 작고, 실제 비용은 사람의 검수 시간입니다. (가정·해석, §7)

---

## 1. OpenAI Image API

### 1-1. 모델 현황 (2026-10 기준)

| 모델 | 상태 | 비고 | 출처 |
|---|---|---|---|
| `gpt-image-2` | 2026-04-21 출시로 보도. 공식 가이드가 새 개발의 기본 모델로 권장 | 신원 유지(identity-sensitive) 편집에 권장 | [확인] [출처](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), [보도] [출처](https://docs.apiyi.com/en/news/gpt-image-2-launch) |
| `gpt-image-2.5-flare` | 2026-09 출시. 공식 모델 페이지 있음 | 빠른 일반용. 지연 시간 최대 50% 감소라는 주장 | [확인] [출처](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare), [주장] [출처](https://cellcog.ai/blog/gpt-image-2-5-release-date/) |
| `gpt-image-2.5-sunburst` | 2026-09-08 출시 보도 (OpenRouter 등록 09-09) | 정밀 편집용. 생성 시간이 더 김 | [보도] [출처](https://openrouter.ai/openai/gpt-image-2.5-sunburst), [출처](https://www.cometapi.com/what-is-gpt-image-2-5/) |
| `gpt-image-1.5`, `gpt-image-1` | 구형. gpt-image-1 모델 페이지는 지원 중단(deprecated) 표시 | 호환용 | [확인] [출처](https://developers.openai.com/api/docs/models/gpt-image-1), [출처](https://developers.openai.com/api/docs/models/gpt-image-1.5) |

- ChatGPT 앱의 이미지 기능 이름은 'ChatGPT Images 2.0'에서 '2.5'로 바뀐 것으로 보도됐습니다. [보도] [출처](https://tech-insider.org/chatgpt-images-2-5-gpt-image-2-5-launch-2026/), [출처](https://en.wikipedia.org/wiki/GPT_Image)
- 2.5의 품질 단계는 `low`, `medium`, `high`, `xhigh`, `max`, `auto`라고 합니다. gpt-image-2보다 두 단계가 많습니다. [보도/주장] [출처](https://tech-insider.org/chatgpt-images-2-5-gpt-image-2-5-launch-2026/)
- 검색 결과의 코드 예시에 `gpt-6-astra` 같은 이름도 보였지만 공식 모델 목록에서는 확인하지 못했습니다. [미확인]
- (해석) 키트(`config.yaml`)는 `gpt-image-2`를 씁니다. 지금 바꿀 필요는 없습니다. 다만 얼굴 유지가 핵심이므로 `gpt-image-2.5-sunburst`를 같은 기준 사진과 프롬프트로 10장쯤 비교해 보고 정합니다.

### 1-2. 엔드포인트

| 방식 | 용도 | 출처 |
|---|---|---|
| `images.generate` (Image API, 생성) | 글만으로 생성. 기준 사진이 없을 때 | [확인] [출처](https://developers.openai.com/api/reference/resources/images/methods/generate) |
| `images.edit` (Image API, 편집) | 기준 사진 여러 장과 마스크를 넣어 편집·합성. **도하의 기본 경로** | [확인] [출처](https://developers.openai.com/api/reference/resources/images/methods/edit) |
| Responses API의 이미지 생성 도구 | 대화형으로 여러 번 고칠 때 | [확인] [출처](https://developers.openai.com/api/docs/guides/image-generation) |

- 키트(`doha/imagegen.py`)는 기준 사진이 있으면 `images.edit`, 없으면 `images.generate`를 부릅니다. `input_fidelity="high"`를 먼저 보내고, 거부되면 빼고 다시 보냅니다. gpt-image-2에서는 이 동작이 문서와 맞습니다. (해석)

### 1-3. 주요 파라미터

| 파라미터 | 내용 | 신뢰도·출처 |
|---|---|---|
| `size` | gpt-image-2는 고정 3종(1024×1024, 1024×1536, 1536×1024)뿐 아니라 **양쪽 변이 16의 배수, 긴 변 3840px 이하, 가로세로 비 3:1 이하, 총 화소 655,360~8,294,400 사이면 자유 크기**를 받는다는 설명이 여러 문서에서 일치합니다. 공식 가이드는 2560×1440을 넘는 크기를 '실험적'으로 봅니다 | 자유 크기: [보도] [출처](https://fal.ai/models/openai/gpt-image-2), [출처](https://www.digitalapplied.com/blog/chatgpt-images-2-0-features-use-cases-impact), [출처](https://lumalabs.ai/learning-center/articles/gpt-image-2-complete-guide) · 실험적: [확인] [출처](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide) |
| `quality` | gpt-image-2는 `low`/`medium`/`high`/`auto`. 2.5는 `xhigh`, `max` 추가 | [보도] [출처](https://tech-insider.org/chatgpt-images-2-5-gpt-image-2-5-launch-2026/) |
| `n` | 한 번에 여러 장. 상한(1~10으로 알려짐)은 이번에 확인 못 함 | [미확인] |
| `output_format` | png(기본), jpeg, webp | [확인] [출처](https://developers.openai.com/api/docs/guides/image-generation) |
| `output_compression` | 0~100. jpeg·webp에서만. png에는 보내지 않음 | [확인] [출처](https://developers.openai.com/api/docs/guides/image-generation) |
| `background` | `transparent`/`opaque`/`auto`. **gpt-image-2의 투명 배경은 출처마다 다릅니다**: 출시 때 미지원, 2026-08-21 지원 시작(재판매사), 공식 가이드는 '프리뷰'로 표기. ComfyUI 문서는 투명 배경을 2.5-flare·2.5-sunburst·1.5·1에만 허용하고 gpt-image-2는 뺍니다. 키트는 투명 배경을 쓰지 않으므로 영향 없음 | [확인] [출처](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), [주장] [출처](https://help.apiyi.com/en/gpt-image-2-transparent-background-not-supported-en.html), [출처](https://docs.comfy.org/built-in-nodes/OpenAIGPTImageNodeV2) |
| `input_fidelity` | gpt-image-1·1.5는 `low`/`high` (high는 입력 토큰을 더 씀). gpt-image-2는 항상 high로 처리해서 보내지 않음. 보내면 오류가 난다는 제3자 문서가 있음 | [확인] [출처](https://developers.openai.com/api/docs/guides/image-generation), [출처](https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity) · 오류: [주장] (검증 검색 요약에만 나옴, 원문 출처 특정 못 함) |
| 기준 사진 여러 장 | `images.edit`에 여러 장을 넣을 수 있음. gpt-image-2의 최대 장수는 확인 못 함 | [확인]/[미확인] [출처](https://developers.openai.com/api/reference/resources/images/methods/edit) |
| `mask` | **첫 번째 입력 이미지**에만 적용. 가려진 부분만 바뀜. 고충실도에서는 마스크 안쪽이 원본에서 더 벗어난다는 개발자 보고가 있음 | [확인] [출처](https://developers.openai.com/api/docs/guides/image-generation) · [주장] [출처](https://community.openai.com/t/image-generation-high-fidelity-editing/1317649) |

- (해석) 인스타 앱 업로드 권장 비율은 3:4(1080×1440)입니다(research/ig-platform.md). 지금 쓰는 1024×1536(2:3)은 3:4로 자르면 세로가 약 11% 잘립니다. 자유 크기가 실제로 되면 **1152×1536(정확히 3:4, 양 변 16의 배수)**으로 바로 만드는 편이 낫습니다. 출력 화소가 늘어 장당 비용이 조금 오를 수 있습니다. `--dry-run`과 1장 실험으로 먼저 확인합니다.

### 1-4. 비용

**토큰 단가 (100만 토큰당)**

| 항목 | gpt-image-2 | gpt-image-2.5 (flare·sunburst) | 신뢰도·출처 |
|---|---|---|---|
| 텍스트 입력 | $5 | $5 | [보도] [출처](https://aireiter.com/blog/gpt-image-2-api-pricing) · 2.5: [보도] [출처](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare), [출처](https://tech-insider.org/how-to-use-gpt-image-2-5-api-2026/) |
| 이미지 입력 | $8 | $8 (캐시 입력 $2) | [보도] [출처](https://aireiter.com/blog/gpt-image-2-api-pricing), [주장] [출처](https://openrouter.ai/openai/gpt-image-2.5-flare) |
| 이미지 출력 | $30 | $30 (Batch는 $15) | [보도] · 2.5: [보도] [출처](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare) |

- **2.5 단가가 gpt-image-2의 2배라는 설명도 검색됐습니다(원문 출처는 특정 못 함).** 출처끼리 맞지 않으므로 OpenAI 가격 페이지에서 두 모델의 단가를 나란히 확인해야 합니다. [미확인]
- 한 재판매사(Segmind)는 출력 $37.50/100만 토큰으로 다르게 적었습니다. 재판매가로 보고 제외했습니다. CometAPI는 2.5를 입력 $4·출력 $24로 더 싸게 팝니다(재판매가). [주장] [출처](https://www.segmind.com/models/gpt-image-2/pricing), [출처](https://www.cometapi.com/what-is-gpt-image-2-5/)

**장당 출력 비용 (gpt-image-2, 1024×1536 세로)**

| 품질 | 표준 | Batch(약 50%) | 출처 |
|---|---|---|---|
| low | 약 $0.005 | 약 $0.0025 | [보도] [출처](https://aireiter.com/blog/gpt-image-2-api-pricing) |
| medium | 약 $0.041 | 약 $0.02 | [보도] [출처](https://yingtu.ai/en/blog/gpt-image-2-cost-per-image) |
| high | 약 $0.165 | 약 $0.083 | [보도] [출처](https://www.nemovideo.com/blog/gpt-image-2-pricing-breakdown) |

- 위 세로 단가는 Batch API에서 50% 할인된다는 설명이 일치합니다. [보도] [출처](https://www.nemovideo.com/blog/gpt-image-2-pricing-breakdown)
- gpt-image-2 1024×1024는 low 약 $0.006, medium 약 $0.053, high 약 $0.211이라는 수치가 여러 곳에 나옵니다. 이보다 훨씬 낮은 수치(medium $0.011, high $0.036)를 적은 페이지도 있으나 다른 출처와 맞지 않아 제외했습니다. [보도] [출처](https://news.ycombinator.com/item?id=47853328), [출처](https://costgoat.com/pricing/openai-images)
- gpt-image-2.5는 1024×1024 기준 low 약 $0.006, max 약 $0.211로 측정됐다는 주장이 있습니다. fal.ai는 2.5 글→이미지 1024×1024를 low $0.0060, medium $0.0133, high $0.0528로 적었습니다. 이 수치가 맞으면 같은 high 품질에서 gpt-image-2(약 $0.211)보다 장당 훨씬 쌉니다. 편집은 기준 사진 입력 비용이 더 붙습니다. [주장] [출처](https://cellcog.ai/blog/gpt-image-2-5-release-date/), [출처](https://fal.ai/gpt-image-2.5)
- **기준 사진 입력 비용**: gpt-image-2는 입력 이미지를 항상 고충실도로 처리하므로 기준 사진 1장마다 이미지 입력 토큰이 꽤 붙습니다. 장당 토큰 수는 공식 수치를 찾지 못했습니다. [미확인] 응답의 `usage.input_tokens_details.image_tokens`로 실제 값을 확인해야 합니다.
- (해석) 키트는 `token_prices_usd_per_1m`이 설정돼 있으면 응답의 토큰 수로 실제 비용을 계산합니다. `text_input: 5`, `image_input: 8`, `image_output: 30`을 넣으면 추정치 대신 사용량 기반 금액이 `tracking/costs.csv`에 남습니다. 단가는 OpenAI 가격 페이지에서 먼저 확인합니다.

### 1-5. 계정 요건: 조직 인증, 사용 등급, 선불 결제

- **조직 인증**: OpenAI는 일부 제품·기능·모델을 쓰기 전에 조직 인증을 요구할 수 있습니다. 개인 인증에는 지원 국가에서 발급한 **실물 정부 신분증 원본**과 카메라가 있는 기기, 필요하면 셀카가 필요합니다. 인증 후에도 별도 승인이 필요한 모델이 있습니다. [확인] [출처](https://help.openai.com/en/articles/10910291-api-organization-verification)
  - **GPT Image 모델이 지금 인증을 요구하는지는 확인하지 못했습니다.** 공식 도움말에 모델별 목록이 없었습니다. [미확인] 첫 API 호출이 인증 관련 오류를 내면 Platform 설정에서 인증을 진행합니다.
- **사용 등급(Usage tier)**: 2026-10-06부터 기존 5단계(Tier 1~5)가 3단계 유료 등급으로 바뀌었습니다. 누적 크레딧 구매액이 $5면 Build(월 사용 한도 $500), $100면 Launch(월 $5,000), $500면 Grow(월 $200,000)로 자동 상향됩니다. 허용 지역에는 Free 등급(월 $100)도 있습니다. [확인] [출처](https://developers.openai.com/api/docs/guides/rate-limits), [보도] [출처](https://mixed-news.com/en/openai-api-usage-tiers-five-to-three-build-launch-grow/)
  - gpt-image-1 기준 분당 이미지 수(IPM)는 Build 20, Launch 150, Grow 250이고 무료 등급은 지원하지 않습니다. 새 모델의 수치는 각 모델 페이지와 대시보드 Limits에서 봐야 합니다. [확인] [출처](https://developers.openai.com/api/docs/models/gpt-image-1)
  - (해석) 이 계정의 생산량(주 수십 장)에는 Build 등급이면 충분합니다.
- **선불 결제**: 첫 구매 최소 $5(기본값 $10). 자동 충전도 최소 $5이고, 설정 과정에서 **기본으로 켜져 있습니다**. 잔액 기준선, 충전 후 잔액, 월 충전 한도를 정할 수 있습니다. 잔액이 0이 되면 API가 결제 오류를 냅니다. 구매 크레딧은 1년 뒤 만료되고 환불되지 않는다는 도움말이 있습니다(문서 작성 시점이 오래됐을 수 있음). [확인] [출처](https://help.openai.com/en/articles/8264778-what-is-prepaid-billing)
  - (해석) 처음에는 $10만 넣고, 자동 충전은 끄거나 월 한도를 $20 이하로 둡니다. 키트의 `max_cost_per_run_usd: 1.00`과 실행 전 `y` 확인이 2차 안전장치입니다.

### 1-6. 출처 표시: C2PA와 SynthID

- ChatGPT, Codex, OpenAI API로 만든 이미지에는 **C2PA 메타데이터와 SynthID 워터마크(Google DeepMind 기술)가 함께** 들어갑니다. 2026-05-19~20 발표이며, 같은 때 OpenAI 이미지 여부를 확인하는 'Verify' 연구 프리뷰도 나왔습니다. OpenAI는 이미지에 OpenAI 출처 신호가 있는지 확인하는 Content Provenance API도 제공하며, 응답은 C2PA와 SynthID 결과를 따로 돌려줍니다. [확인] [출처](https://developers.openai.com/api/docs/guides/content-provenance), [보도] [출처](https://petapixel.com/2026/05/20/openai-gets-serious-about-detecting-fake-images/)
- **편집·변환·공유 과정에서 메타데이터가 지워질 수 있습니다.** SynthID는 이미지 자체에 들어가 일부 변형 뒤에도 남을 수 있습니다. [확인] [출처](https://developers.openai.com/api/docs/guides/content-provenance)
- gpt-image-1 출시 때부터 API 이미지에 C2PA가 들어간다고 밝혔습니다. [확인] [출처](https://openai.com/index/image-generation-api/)
- ChatGPT에 올린 PNG의 C2PA가 사라진 것 같다는 사용자 보고가 있습니다. [주장] [출처](https://community.openai.com/t/are-c2pa-metadata-chunks-intentionally-stripped-from-images-uploaded-to-chatgpt/1385097)
- (해석) **키트의 렌더러는 사진 위에 글자를 얹어 새 PNG를 만들므로 C2PA 메타데이터는 최종 슬라이드에 남지 않을 가능성이 큽니다.** 메타는 C2PA를 감지해 'AI 정보' 라벨을 자동으로 붙이는데(research/ig-platform.md §3-1), 메타데이터가 빠지면 자동 라벨이 안 붙을 수 있습니다. 그래서 게시할 때 'AI 정보'를 **직접 켜야** 합니다. 생성 원본(C2PA 포함)은 `images/`에 그대로 보관합니다.

---

## 2. ChatGPT 구독으로 만들기 (API 비용 없음)

| 플랜 | 이미지 한도 (모두 비공식) | 출처 |
|---|---|---|
| Free | 24시간에 약 2~3장이라는 보고. 숫자 없이 '제한적'이라고만 표기 | [주장] [출처](https://www.cometapi.com/how-many-images-can-you-create-with-chatgpt-free-in-2026/) |
| Go | OpenAI 발표 문구로 '무료보다 메시지·파일 업로드·이미지 생성 10배'. 하루 20~30장은 추정 | [주장] [출처](https://chatgptimage2.org/blog/chatgpt-go-image-generation-limit), 플랜 설명: [확인] [출처](https://help.openai.com/en/articles/11989085-what-is-chatgpt-go) |
| Plus | 3시간에 약 40~50장이라는 사용자 보고가 많음. 하루 200장이라는 다른 주장도 있음 | [주장] [출처](https://aivideobootcamp.com/blog/chatgpt-plus-image-generation-complete-guide-2026/), [출처](https://gptimg.co/blog/chatgpt-image-limits) |
| Pro | '무제한'(남용 방지 장치 적용) | [주장] [출처](https://gptimg.co/blog/chatgpt-image-limits) |

- **OpenAI는 플랜별 고정 장수를 공개하지 않습니다.** 앱의 사용량 안내가 기준입니다. [주장] [출처](https://gptimg.co/blog/chatgpt-image-limits)
- **한국 원화 가격(부가세 10% 포함, 2026-10 블로그 기준)**: Go 월 13,000원, Plus 월 29,000원, Pro 월 159,000원(상위 티어 299,000원). 달러로는 Go $8, Plus $20, Pro $100부터입니다. Pro 구성과 가격은 2026-09 이후 여러 번 바뀌었다는 기록이 있고 공식 페이지를 직접 인용한 자료는 없었습니다. [주장] [출처](https://sireal.co/blog/how-to/chatgpt-pricing-plans-free-plus-pro), [출처](https://aiyogeum.com/tools/chatgpt) → 결제 화면에서 최종 금액을 확인합니다.
- 개인 플랜(Free·Go·Plus·Pro)에서 크레딧을 사서 사용량을 늘리는 제도에 대한 공식 도움말이 있습니다(제목만 확인). [확인] [출처](https://help.openai.com/en/articles/12642688-using-credits-for-flexible-usage-in-chatgpt-freegopluspro-sora)
- ChatGPT로 만든 이미지에도 C2PA와 SynthID가 들어갑니다. [확인] [출처](https://developers.openai.com/api/docs/guides/content-provenance), [출처](https://help.openai.com/en/articles/12677804-what-is-chatgpt-faq)
- **상업적 이용**: 개인의 ChatGPT 사용은 이용약관(Terms of Use, 2026-01-01 시행)을, API·기업 고객은 별도의 OpenAI 서비스 계약(Services Agreement, 2026-01-01 시행)을 따릅니다(§6 참고). 구독 경로라서 상업 이용이 따로 막힌다는 근거는 찾지 못했습니다. [미확인]
- (해석) **장당 추가 비용이 0원이어서 시안을 많이 뽑는 단계에 가장 경제적입니다.** 단점은 한도가 들쭉날쭉하고, 크기·품질 같은 파라미터를 정확히 고정하기 어렵고, 비용·토큰 기록이 자동으로 남지 않는다는 점입니다.

---

## 3. 얼굴 일관성이 강한 대안 이미지 도구

### 3-1. Google Gemini 이미지 (Nano Banana 계열)

| 모델 | 기준 이미지 | 가격 (장당) | 출처 |
|---|---|---|---|
| Nano Banana Pro (`gemini-3-pro-image`) | 최대 14장 혼합. **인물 일관성용 최대 5장**, 고충실도 사물 최대 6장, 스타일 최대 3장 (문서 안에서도 표기가 조금 다름) | 1K·2K $0.134, 4K $0.24. Batch는 약 절반 | 기준: [확인] [출처](https://ai.google.dev/gemini-api/docs/image-generation), [출처](https://blog.google/technology/ai/nano-banana-pro/) · 가격: [주장] [출처](https://aipricing.org/models/gemini-3-pro-image) |
| Nano Banana 2 (`gemini-3.1-flash-image`) | 인물 최대 4명 유사도, 사물 최대 10개 | 0.5K $0.045, 1K $0.067, 2K $0.101, 4K $0.151 | 기준: [확인] [출처](https://ai.google.dev/gemini-api/docs/image-generation) · 가격: [주장] [출처](https://benchlm.ai/media-pricing/nano-banana) |
| Nano Banana 2.1, Gemini 3.1 Flash-Lite Image | 공식 문서에 이름이 보임. 가격 확인 못 함 | — | [확인] [출처](https://deepmind.google/models/gemini-image/flash-lite/) · 가격 [미확인] |

- OpenRouter는 Nano Banana 2를 토큰 단가(이미지 출력 $60/100만 토큰)로 표기해 위 장당 가격과 맞지 않습니다. [주장] [출처](https://openrouter.ai/google/gemini-3.1-flash-image)
- Google 개발자 블로그: Nano Banana Pro는 고충실도 사진 6장 또는 일반 입력 14장까지 섞을 수 있습니다. [확인] [출처](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-3-pro-image-developers/)
- 생성 이미지에는 **SynthID 워터마크와 C2PA 콘텐츠 자격 증명**이 들어갑니다. [확인] [출처](https://ai.google.dev/gemini-api/docs/image-generation)
- 공식 문서는 새 프로젝트에 더 새로운 모델을 권장합니다. `gemini-3-pro-image-preview` 같은 모델 ID는 확인하지 못했으니 AI Studio의 모델 목록을 봐야 합니다. [확인]/[미확인] [출처](https://ai.google.dev/gemini-api/docs/image-generation)
- **데이터 사용**: 무료(unpaid) 서비스에 넣은 내용과 응답은 Google 제품 개선에 쓰입니다. 유료 서비스에서는 쓰지 않습니다. [확인] [출처](https://ai.google.dev/gemini-api/terms) → (해석) 도하 얼굴 기준 사진은 **유료 등급에서만** 넣습니다.

### 3-2. Midjourney

- 플랜: Basic $10, Standard $30, Pro $60, Mega $120 (월). Standard 이상은 빠른 GPU 시간이 끝나면 Relax 대기열로 넘어갑니다. [보도] [출처](https://tech-insider.org/how-to-use-midjourney-v8-2-2026/), [출처](https://www.aiworthit.com/blog/midjourney-review/)
- **비공개(Stealth) 모드는 Pro·Mega에서만** 됩니다. 그 아래 플랜은 생성물이 공개 갤러리에 보일 수 있습니다. [주장] [출처](https://beginnersinai.org/midjourney-v8-explained/)
- 기본 모델은 V8.1(2026-06-11부터)이라는 설명과 V8.2라는 설명이 엇갈립니다. [주장] [출처](https://beginnersinai.org/midjourney-v8-explained/)
- Omni Reference(`--oref`)의 V7·V8 공식 작동 방식, 연 매출 100만 달러 초과 기업의 상위 플랜 의무 같은 상업 이용 조건은 이번에 확인하지 못했습니다. [미확인] 공식 API가 있는지도 재판매사 주장뿐입니다. [주장] [출처](https://evolink.ai/midjourney-v8-1)
- (해석) API 자동화가 어렵고, 협찬 신제품이 공개 갤러리에 노출될 위험이 있어 이 계정의 기본 도구로는 맞지 않습니다.

### 3-3. FLUX (Black Forest Labs)

| 모델 | 가격 | 출처 |
|---|---|---|
| FLUX.1 Kontext [pro] | $0.04/장 | [확인] [출처](https://help.bfl.ai/articles/7424166364-wip-welcome-to-the-forest) |
| FLUX.1 Kontext [max] | $0.08/장 | [확인] 같은 출처 |
| FLUX.2 [pro] | 생성 $0.03/MP, 편집 $0.045/MP | [확인] 같은 출처 |
| FLUX.2 [flex] | 생성 $0.05/MP, 편집 $0.10/MP | [확인] 같은 출처 |
| FLUX.2 [max] | $0.07/MP | [확인] 같은 출처 |

- 1 크레딧 = $0.01, API와 플레이그라운드 가격이 같습니다. 정확한 금액은 가격 계산기로 보라고 안내합니다(위 단가는 최저가에 가까움). [확인] [출처](https://docs.eu.bfl.ai/quick_start/pricing)
- 다중 기준 이미지의 추가 요금은 BFL 공식 수치를 찾지 못했습니다. Azure는 FLUX.2 [pro]에 기준 이미지 1MP마다 $0.015를 받습니다. [주장] [출처](https://developer.puter.com/tutorials/flux-api-pricing/)
- 상업 이용 조건과 출처 표시(워터마크) 정책은 이번에 확인하지 못했습니다. [미확인]

### 3-4. Higgsfield 등 'AI 인플루언서' 도구

- 가격이 출처마다 크게 다릅니다. 입문 $15~19(약 200~270 크레딧), Plus $39~59(약 1,000~1,200), Ultra $99~129(약 3,000)라는 설명이 많고, Basic $9·Plus $49·Ultra $129라는 표도 있습니다. [주장] [출처](https://www.layer3labs.io/guides/higgsfield-ai-pricing), [출처](https://www.scopeful.org/tools/higgsfield), [출처](https://stackedreview.com/higgsfield-ai-pricing/)
- 2026-09-08 기준 가격 페이지에 무료 플랜이 없다는 주장이 있습니다. [주장] [출처](https://www.scopeful.org/tools/higgsfield)
- 'Soul ID'로 캐릭터를 학습시키는 기능과 AI Influencer Studio가 있다고 소개됩니다. [주장] [출처](https://make-influencer.ai/tools/higgsfield-ai), [출처](https://www.therundown.ai/tools/higgsfield-soul-2-0)
- 상업 이용은 유료 플랜에 포함된다는 설명이 많지만 출처끼리 다릅니다. 구독 크레딧은 이월되지 않는다는 주장이 있습니다. [주장] [출처](https://aifunnelinsider.com/higgsfield-ai-review-2026/)
- 경쟁사(Krea)의 가격 해설 글도 검색됐습니다. 이해관계가 있는 출처입니다. [주장] [출처](https://www.krea.ai/blog/higgsfield-pricing-explained-2026-unlimited-credits-and-real-monthly-costs)
- (해석) 공식 가격·약관을 확인하기 전에는 월 구독을 시작하지 않습니다. 키트가 이미 기준 사진 기반 편집 흐름을 갖추고 있어 당장 필요하지 않습니다.

---

## 4. 이미지→영상 (릴스용)

| 도구 | 가격 | 상태·조건 | 출처 |
|---|---|---|---|
| **Sora 2 / Sora 2 Pro (API)** | sora-2 720p $0.10/초. sora-2-pro 720p $0.30, 1792×1024 $0.50, 1080p $0.70/초 (1080p $0.50이라는 출처도 있음) | **2026-09-24 API 종료**(Videos API와 sora-2·sora-2-pro 및 날짜 스냅샷 3종 제거, 2026-03-24 예고, 대체 모델 없음). Sora 웹·앱은 2026-04-26 종료. 사용 불가 | 종료: [보도] [출처](https://techjacksolutions.com/ai-brief/openai-videos-api-sora-2-deprecated-september-2026/), [출처](https://www.aistackcurrent.com/news/openai-sora-api-shutdown/) · 가격(참고): [주장] [출처](https://costgoat.com/pricing/sora), [출처](https://queststudio.io/blog/sora-2-pricing-limits-prompt-tips) |
| **Veo 3.1** (Gemini API, 소리 포함) | 표준 720p·1080p $0.40/초, 4K $0.60 | 무료 등급 없음 | [주장] [출처](https://benchlm.ai/media-pricing/veo), [출처](https://magichour.ai/blog/veo-3-pricing) |
| **Veo 3.1 Fast** | 720p $0.10, 1080p $0.12, 4K $0.30/초 | 8초 1080p 약 $0.96 | [주장] 같은 출처 |
| **Veo 3.1 Lite** | 720p $0.05, 1080p $0.08/초 (소리 포함) | 4K 없음. 8초 1080p 약 $0.64. OpenRouter는 1080p 무음을 $0.05/초로 표기 | [보도] 여러 추적 사이트 일치 [출처](https://benchlm.ai/media-pricing/veo), [출처](https://costgoat.com/pricing/google-veo) · 무음: [주장] [출처](https://openrouter.ai/google/veo-3.1-lite) |
| **Kling 3.0 API** | 1080p 무음 $0.112/초, 소리 포함 $0.168/초, 720p $0.084/초, 4K $0.42/초. 3.0 Turbo(소리) 1080p $0.14/초 | 선불 유닛 $0.14/개. 체험 100유닛 $9.80. 1080p를 $0.07/초로 적은 출처도 있고, 재판매사(APIMart)는 $0.0896/초. Kling 공식 가격 페이지는 직접 확인 못 함 | [주장] [출처](https://aireiter.com/blog/kling-api-pricing), [출처](https://magichour.ai/blog/kling-ai-pricing), [출처](https://www.cloudzero.com/blog/kling-ai-pricing/), [출처](https://costbench.com/software/ai-media-apis/kling-api/) |
| **Kling 3.0 구독** | 1080p 무음 8크레딧/초, 소리 12크레딧/초 (5초 소리 포함 60크레딧). 100크레딧 = Standard $1.33 ~ Ultra $0.62 | **무료 등급은 워터마크, 상업 이용 불가.** 유료는 워터마크 없음이라는 표 | [주장] [출처](https://www.virse.ai/blog/kling-3-0-pricing), [출처](https://framesurfer.com/blogs/kling-ai-pricing) |
| **Runway** | Gen-4.5 12크레딧/초, Gen-4 Turbo 5크레딧/초. Standard $15/월(625크레딧), Pro $35(2,250), Max $95(9,500, 이월) | 무료는 워터마크. Unlimited 플랜은 2026년 Max로 대체. 상업 이용 조건 미확인 | [주장] [출처](<https://creatify.ai/blog/runway-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay>), [출처](https://www.eesel.ai/en/blog/runway-ai-pricing) |
| **Higgsfield** | §3-4 구독 크레딧 | 영상 단가·모델 구성은 확인 못 함 | [미확인] |

- (해석) Runway Standard로 Gen-4.5를 쓰면 1초에 약 $0.29입니다($15 ÷ 625 × 12). Veo 3.1 Fast나 Kling 3.0 API보다 비쌉니다.
- Veo 영상의 SynthID·C2PA 포함 여부, Veo의 기준 이미지('재료') 입력 장수와 9:16 세로 출력 단가는 이번에 확인하지 못했습니다. [미확인] Google은 Gemini 이미지에 SynthID·C2PA가 들어간다고 밝혔습니다. [확인] [출처](https://ai.google.dev/gemini-api/docs/image-generation)
- Sora 2 Pro에 C2PA·워터마크가 들어간다는 설명은 제3자 요약뿐입니다. [주장] [출처](https://openrouter.ai/openai/sora-2-pro)
- 패션(원단 움직임, 걷기)에서 어느 도구가 나은지 비교한 믿을 만한 자료는 찾지 못했습니다. [미확인]
- (해석) 얼굴이 바뀌는 위험은 클립이 길고 움직임이 클수록 커집니다. 4~5초, 동작 1개(돌아서기, 두 걸음, 재킷 여미기), 확정 사진 1장을 첫 프레임으로 쓰는 방식이 안전합니다. 릴스 음원은 인스타의 상업용 음원을 쓰므로 **소리 없는 요금**으로 충분합니다.

---

## 5. 얼굴 일관성 기법과 검수

### 5-1. 공식 문서가 권하는 것

- 얼굴·로고처럼 **세부를 유지해야 하는 편집**은 고충실도 입력이 핵심입니다. OpenAI 쿡북에 얼굴 보존 예시가 있습니다. [확인] [출처](https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity)
- OpenAI 프롬프트 가이드는 신원 유지 편집에 gpt-image-2를 권하고, 바꿀 것과 **바꾸지 말 것**을 따로 적으라고 안내합니다. [확인] [출처](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), [출처](https://developers.openai.com/api/docs/guides/image-prompting)
- Gemini는 인물 일관성용 기준 이미지를 최대 5장(Pro)까지 받습니다. Google은 Nano Banana 프롬프트 가이드를 따로 냈습니다. [확인] [출처](https://ai.google.dev/gemini-api/docs/image-generation), [출처](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana)

### 5-2. 운영 기법 (해석)

1. **기준 사진 세트 고정**: 정면, 3/4, 상반신 3장(brand/reference). 같은 조명·무표정·단색 배경. 머리 모양을 바꿀 때만 새 세트를 승인합니다.
2. **고정 묘사문**: 얼굴형·눈매·피부 톤·점 위치·머리 길이·키 비율을 영어 한 문단으로 고정해 매번 같은 문장으로 붙입니다. 바뀌는 것(옷·장소·자세)만 뒤에 씁니다.
3. **편집 우선**: 새로 생성하지 말고 기준 사진을 넣은 `images.edit`로 만듭니다. 확정 사진에서 옷만 바꿀 때는 그 사진을 첫 입력으로 넣고 마스크로 옷 영역만 엽니다.
4. **기준 사진은 2~3장**: 장수가 늘면 입력 비용이 늘고 얼굴이 섞일 수 있습니다.
5. **같은 세션 반복 수정 금지**: 수정을 여러 번 이어 가면 얼굴이 조금씩 흐려집니다. 3번 안에 안 되면 기준 사진에서 다시 시작합니다.
6. **한국 패션 에디토리얼 톤**: 카메라·렌즈(예: 50mm, f/2.8), 자연광 방향, 장소(성수동 골목, 여의도 오피스 로비 등 일반 묘사), 원단 이름(울 개버딘, 코튼 포플린)과 핏(세미 오버, 하이웨이스트)을 구체적으로 씁니다. 실존 브랜드 로고·매장 간판·실존 인물 이름은 넣지 않습니다.
7. **협찬 제품**: 제품 사진을 기준 이미지로 함께 넣되, 로고·라벨 글자는 생성물에서 깨지기 쉬우므로 실물 사진 합성이나 렌더러 표기로 처리하고, 브랜드에 시안 승인을 받습니다.

### 5-3. 자주 나오는 결함 (검수 항목, 해석)

| 부위 | 흔한 결함 |
|---|---|
| 얼굴 | 기준 사진과 눈매·코끝·턱선 차이, 나이 들어 보임, 피부가 지나치게 매끈함 |
| 손 | 손가락 수, 관절 꺾임, 가방 손잡이·컵을 쥔 손의 겹침 |
| 원단 | 체크·스트라이프 무늬 왜곡, 단추 수·위치 불일치, 지퍼·주머니 좌우 비대칭, 니트 짜임 뭉개짐 |
| 액세서리 | 귀걸이 좌우 다름, 시계 바늘·숫자 깨짐, 가방 스트랩이 몸을 관통 |
| 글자 | 간판·라벨·로고의 가짜 글자 (키트 원칙대로 사진에 글자를 넣지 않음) |
| 배경 | 사람·차량 왜곡, 원근 어긋남, 실존 장소로 오인될 간판 |
| 영상 | 프레임 사이 얼굴 변화, 옷 색 변화, 발 미끄러짐, 손가락 녹아내림 |

---

## 6. 약관과 표시 의무

### 6-1. OpenAI

- **이용 정책(2025-10-29 개정)**: 기만·사기·스팸·**사칭** 금지. 동의 없이 **실존 인물의 실사 이미지나 목소리**를 진위를 혼동시키는 방식으로 쓰는 것도 금지합니다. [확인] [출처](https://openai.com/policies/usage-policies/)
- **AI 역할 숨기기 금지**: AI가 맡은 역할을 잘못 알리거나 숨기는 것을 금지한다고 안내합니다(ChatGPT agent 정책 안내). [확인] [출처](https://openai.com/policies/using-chatgpt-agent-in-line-with-our-policies/)
- **이용약관(Terms of Use, 2026-01-01 시행)**: 금지 사용 목록에 사람이 만들지 않은 출력물을 사람이 만든 것처럼 표시하는 것이 들어 있습니다. 이 약관은 개인 사용자(ChatGPT 등)에 적용됩니다. [확인] [출처](https://openai.com/policies/row-terms-of-use/)
  - (해석) 도하를 '실제 사람'처럼 소개하면 이 조항에 걸릴 수 있습니다. 프로필·캡션·이미지에 AI 가상인물임을 밝히는 현재 원칙이 약관과도 맞습니다.
- **API는 별도 계약**: API·기업·비즈니스 고객에는 OpenAI 서비스 계약(Services Agreement, 2026-01-01 시행)이 적용됩니다. 이 계약은 법이 허용하는 범위에서 **고객이 출력물을 소유하고 OpenAI가 출력물에 대한 권리를 고객에게 넘긴다**고 적습니다. [확인] [출처](https://openai.com/policies/services-agreement/) 이 계약에 '사람이 만든 것처럼 표시 금지' 조항이 같은 문구로 있는지는 확인하지 못했습니다. [미확인]
- **출력물 소유권(개인 약관)**: 제3자 요약에 따르면 2026-01-01 시행 이용약관도 이용자가 입력을 소유하고 OpenAI가 출력물에 대한 권리를 이용자에게 넘기는 구조입니다. 원문 문구는 직접 보지 못했습니다. [주장] [출처](https://terms.law/ToS-Watchdog/ai-services/openai/) 약관 원문에서 'Output' 항목을 직접 확인해야 합니다.
- Sora 2 시스템 카드는 Sora 2 출시(2025-09-30) 당시의 안전 장치를 설명합니다. [확인] [출처](https://cdn.openai.com/pdf/50d5973c-c4ff-4c2d-986f-c72b5d0ff069/sora_2_system_card.pdf)

### 6-2. Google (Gemini API)

- Gemini API는 **업무·사업 목적의 개발자용**이고 소비자용이 아닙니다. [확인] [출처](https://ai.google.dev/gemini-api/terms)
- Google은 생성물의 소유권을 주장하지 않습니다. 같거나 비슷한 결과를 다른 사람에게도 만들어 줄 수 있습니다. 생성물 사용과 공유에 대한 책임은 이용자에게 있습니다. [확인] 같은 출처
- 생성형 AI 금지 사용 정책(Prohibited Use Policy)을 따라야 합니다. 이 정책의 'AI 생성물 오인·사칭' 세부 문구는 이번에 확인하지 못했습니다. [확인]/[미확인] [출처](https://developers.google.com/ml-kit/genai-terms)

### 6-3. 한국 법과 인스타그램

- AI 기본법 표시 의무, 과기정통부 투명성 가이드라인, 개정 추진 상황, 메타 'AI 정보' 라벨은 [research/kr-compliance.md](kr-compliance.md)와 [research/ig-platform.md](ig-platform.md)에 정리돼 있습니다.
- (해석) 기술 측면에서 정리하면: 생성 원본의 C2PA·SynthID는 지우지 않고 보관합니다. 렌더링 과정에서 메타데이터가 빠지므로 **눈에 보이는 'AI 가상인물' 배지**(렌더러)와 **게시 시 'AI 정보' 라벨**(앱)을 둘 다 씁니다.
- (해석) 순수 AI 생성 이미지는 저작권 보호를 받지 못할 수 있습니다. 브랜드에 '사용권'을 팔 때는 저작권 양도가 아니라 **계약상 이용 허락**(기간·매체·지역)으로 문서화하는 편이 안전합니다. 법적 판단은 전문가 확인이 필요합니다.

---

## 7. 추천 스택과 게시물당 비용 (추정)

### 7-1. 추천 스택 (해석)

| 단계 | 기본 | 보조·대체 | 이유 |
|---|---|---|---|
| 얼굴 기준 사진 | ChatGPT 앱 (구독) | — | 후보를 많이 뽑아야 해서 장당 0원 경로가 유리 |
| 시안(후보) | ChatGPT 앱 + 기준 사진 첨부 | API `gpt-image-2` medium, `images.edit` + 기준 2~3장 | 앱 한도에 걸리거나 기록·재현이 필요할 때 API |
| 확정컷 | API `gpt-image-2` high (또는 시험 후 `gpt-image-2.5-sunburst`) | Nano Banana Pro (유료 등급) | 얼굴이 계속 흔들리는 장면만 Gemini로 교차 시도 |
| 협찬 확정컷 | API (비용·토큰·파일 기록이 남음) | — | 견적·정산 근거 |
| 릴스 | 키트 `reel` (사진 기반 모션, 0원) | Kling 3.0 API 무음 1080p 또는 Veo 3.1 Fast·Lite | AI 영상은 협찬·대표 릴스에만 |
| 제외 | Sora 2(종료 보도), Midjourney(API·비공개 제약), Higgsfield(가격·약관 미확인) | — | — |

### 7-2. 게시물 1건 비용 (추정)

**가정**: 카드뉴스 1건에 사진 5장, 사진마다 시안 3장(총 15장), 확정 5장. 기준 사진 2장을 넣은 편집. 기준 사진 입력 비용은 생성 1회당 $0.01~0.04로 가정 (공식 토큰 수 미확인). 환율 1,400원.

| 경로 | 계산 | USD | 원화 |
|---|---|---|---|
| A. 전부 ChatGPT 앱 | 장당 추가 비용 0 | $0 (구독료 별도) | 0원 |
| B. API 시안만 (medium 15장) | 15 × ($0.041 + $0.01~0.04) | $0.77~1.22 | 약 1,100~1,700원 |
| C. API 시안 + 확정 (B + high 5장) | B + 5 × ($0.165 + $0.01~0.04) | $1.64~2.24 | 약 2,300~3,100원 |
| D. 앱 시안 + API 확정 (권장) | 5 × ($0.165 + $0.01~0.04) | $0.88~1.03 | 약 1,200~1,400원 |
| (참고) Nano Banana Pro로 C와 같은 수량 | 20 × $0.134 (입력 비용 별도) | 약 $2.68 | 약 3,800원 |

**릴스 AI 영상 추가 시 (2컷 × 2번 시도)**

| 도구 | 계산 | USD | 원화 |
|---|---|---|---|
| 키트 사진 기반 릴스 | — | $0 | 0원 |
| Kling 3.0 API 무음 1080p, 5초 컷 | 20초 × $0.112 | $2.24 | 약 3,100원 |
| Veo 3.1 Lite 1080p, 8초 컷 | 32초 × $0.08 | $2.56 | 약 3,600원 |
| (참고) Veo 3.1 Lite 1080p 무음, 8초 컷 (OpenRouter 표기, [주장]) | 32초 × $0.05 | $1.60 | 약 2,200원 |
| Veo 3.1 Fast 1080p, 8초 컷 | 32초 × $0.12 | $3.84 | 약 5,400원 |

**월 비용 (주 3건, 월 12건 가정)**

- 경로 D만: 약 $11~12 (약 1.5만~1.7만 원) + ChatGPT 구독료 (Plus 월 29,000원, 부가세 포함, [주장] §2)
- 경로 C만: 약 $20~27 (약 2.8만~3.8만 원)
- 경로 C + 매 게시물 Kling 영상: 약 $47~54 (약 6.5만~7.5만 원)
- (해석) API·영상 도구비는 목표 매출(월 500만 원)의 약 1.5% 이하이고, Plus 구독료를 더해도 약 2% 수준입니다. 비용보다 **검수 시간과 재생성 횟수**가 실제 병목입니다. 그래서 `review.notes`에 '제작 시간·후보 수'를 남기는 현재 규칙이 중요합니다.

---

## 운영에 바로 쓰는 결론

- **시안은 ChatGPT 앱, 확정컷과 협찬컷은 API로 나눕니다.** 앱은 장당 0원이라 후보 뽑기에, API는 비용·토큰·파일 기록이 남아 견적과 정산 근거가 필요한 컷에 씁니다.
- **`config.yaml`에 토큰 단가를 넣어 실제 비용을 기록합니다.** `token_prices_usd_per_1m`에 `text_input: 5`, `image_input: 8`, `image_output: 30`을 넣으면(먼저 OpenAI 가격 페이지 확인) 추정치 대신 사용량 기반 금액이 남습니다. 현재 `est_cost_usd`의 low 0.02는 실제 출력 단가(약 0.005)보다 높아 보수적인 값입니다.
- **gpt-image-2에는 `input_fidelity`를 보내지 않아도 됩니다.** 항상 고충실도로 처리합니다. 보내면 오류가 난다는 보고가 있지만 키트는 거부되면 빼고 다시 보내므로 그대로 둬도 동작합니다(첫 호출이 매번 한 번 실패할 수 있으니, gpt-image-2일 때는 처음부터 빼는 편이 깔끔합니다).
- **3:4 크기를 시험합니다.** `size: 1152x1536`이 받아지면 인스타 3:4(1080×1440)에 맞춰 잘림 없이 쓸 수 있습니다. 1장 생성으로 먼저 확인하고, 거부되면 1024×1536을 유지합니다.
- **gpt-image-2.5-sunburst를 10장 비교 시험합니다.** 같은 기준 사진·프롬프트로 gpt-image-2와 나란히 만들어 얼굴 일치도와 비용을 비교한 뒤 기본 모델을 정합니다. 2.5의 토큰 단가가 gpt-image-2와 같은지 2배인지 출처가 엇갈리므로, 응답의 `usage`로 실제 장당 비용을 비교합니다.
- **API 결제는 $10 선불, 자동 충전은 끄거나 월 한도 $20 이하**로 둡니다. 크레딧은 1년 뒤 만료되고 환불되지 않습니다.
- **Sora 2는 쓰지 않습니다.** API가 2026-09-24에 종료됐습니다. AI 영상이 필요하면 Kling 3.0 API(무음 1080p) 또는 Veo 3.1 Fast·Lite로 4~5초, 동작 1개, 확정 사진을 첫 프레임으로 씁니다. 기본 릴스는 키트의 사진 기반 영상(0원)입니다.
- **게시할 때마다 'AI 정보' 라벨을 직접 켭니다.** 렌더링 과정에서 C2PA가 빠져 자동 라벨이 안 붙을 수 있습니다. 생성 원본(C2PA·SynthID 포함)은 지우지 않고 보관합니다.
- **도하를 사람처럼 소개하지 않습니다.** OpenAI 이용약관(2026-01-01 시행, ChatGPT 등 개인 사용)이 AI 출력물을 사람이 만든 것처럼 표시하는 것을 금지합니다. API에 적용되는 서비스 계약의 같은 조항은 확인하지 못했지만, 기만·사칭 금지 이용 정책은 양쪽에 적용됩니다. 실존 인물과 닮지 않았는지 역이미지 검색 기록도 유지합니다.
- **Gemini를 쓰면 유료 등급에서만** 기준 사진을 넣습니다. 무료 등급 입력은 Google 제품 개선에 쓰입니다.
- **브랜드 사용권은 계약상 이용 허락으로 문서화합니다.** AI 생성물의 저작권 보호가 불확실하므로 기간·매체·지역을 계약서에 적습니다(법률 확인 필요).

## 남은 확인 사항

- **OpenAI Platform 대시보드**: `gpt-image-2`·`gpt-image-2.5-*` 호출에 조직 인증이 필요한지, 현재 등급의 IPM 한도, 공식 가격표의 크기별·품질별 단가와 이미지 입력 단가.
- **실제 응답의 `usage`**: 기준 사진 1장당 `image_tokens`가 몇 개인지. 이 값으로 §7의 '기준 사진 입력 비용' 가정을 고칩니다.
- **API 파라미터 실측**: `size: 1152x1536` 허용 여부, `n` 상한, `images.edit`에 넣을 수 있는 기준 사진 최대 장수.
- **OpenAI 이용약관 원문**(openai.com/policies): 2026-01-01 시행본의 출력물(Output) 소유권 조항, API용 서비스 계약(Services Agreement)에 '사람이 만든 것처럼 표시 금지' 조항이 있는지.
- **OpenAI 가격 페이지**: gpt-image-2와 gpt-image-2.5의 토큰 단가가 같은지(2배라는 설명이 있음).
- **ChatGPT 앱**: 현재 플랜의 이미지 한도 안내, 결제 화면의 원화 구독료(블로그 기준 Go 13,000원·Plus 29,000원), 크레딧 추가 구매 여부, 앱 이미지가 'ChatGPT Images 2.5'로 바뀌었는지.
- **인스타그램 앱**: 게시 화면의 'AI 정보' 라벨 위치, 렌더링된 슬라이드에 라벨이 자동으로 붙는지(테스트 계정이나 비공개 게시로 확인).
- **Google AI Studio**: 현재 이미지 모델 ID와 공식 가격, 한국에서 유료 등급 사용 가능 여부, 생성형 AI 금지 사용 정책의 AI 생성물 표시 관련 문구.
- **영상 도구 공식 페이지**: Kling(API 1080p 무음 단가, 유료 플랜의 상업 이용·워터마크), Veo 3.1(무음 단가, 세로 9:16 단가, 기준 이미지 입력, SynthID 포함 여부), Runway(상업 이용 조건).
- **Midjourney·Higgsfield·FLUX**: 쓰기로 하면 공식 가격 페이지와 상업 이용 약관(Midjourney의 기업 매출 기준, Higgsfield의 플랜별 라이선스, FLUX 출력물 이용 조건).

## 검증 메모 (2026-10-13)

반박 시도용 웹 검색 10회(영어 9, 한국어 1). 웹 페이지 본문은 열지 못해 검색 결과 요약을 근거로 했습니다. 아래에 없는 URL은 개별 검증하지 않았습니다.

| # | 확인한 주장 | 판정 | 근거 |
|---|---|---|---|
| 1 | gpt-image-2.5-flare·sunburst 2026-09-08 출시, 토큰 단가 gpt-image-2와 같음 | **수정** | 출시일·$5/$8/$30(캐시 $2)은 여러 출처 일치. 'gpt-image-2와 같음'은 '2배'라는 반대 설명이 있어 [미확인] 단서 추가. 태그 [확인]→[보도] |
| 2 | gpt-image-2 1024×1536 장당 low $0.005·medium $0.041·high $0.165 | **유지** | 여러 출처가 OpenAI 예시로 같은 수치 인용. 1024×1024 수치($0.006/$0.053/$0.211)와 2.5의 fal.ai 장당가 추가 |
| 3 | gpt-image-2 자유 크기(16의 배수, 긴 변 ≤3840, 총 화소 범위) | **상향** | fal.ai·Digital Applied 등 여러 문서 일치 → [주장]→[보도]. 가로세로 비 3:1 이하 조건 추가 |
| 4 | gpt-image-2는 `input_fidelity`를 보내지 않음, 투명 배경 상태 | **유지(보강)** | 보내면 오류라는 제3자 설명 추가. 투명 배경은 ComfyUI 문서가 gpt-image-2를 제외해 여전히 엇갈림 |
| 5 | OpenAI 이미지에 C2PA + SynthID | **유지(보강)** | 공식 Content provenance 문서와 2026-05-19~20 언론 보도 일치. Verify 프리뷰 추가 |
| 6 | 사용 등급 Build $5·Launch $100·Grow $500 | **유지(보강)** | 공식 rate limits 페이지와 보도 일치. 2026-10-06 개편일, 등급별 월 한도($500/$5,000/$200,000), Free 등급 추가 |
| 7 | Sora 2 API 2026-09-24 종료, Sora 앱 2026-04-26 종료 | **유지(보강)** | 여러 출처 일치. 2026-03-24 예고·대체 모델 없음 추가. 근거가 약한 unifically.com 링크는 검색에서 확인된 보도 링크로 교체 |
| 8 | Veo 3.1 Lite 1080p $0.08/초, Fast $0.12/초 | **부분 상향** | Lite는 추적 사이트 다수 일치 → [보도]. OpenRouter 무음 $0.05/초 추가. Fast는 이번에 재확인 못 해 [주장] 유지 |
| 9 | Kling 3.0 API 1080p 무음 $0.112/초 | **유지([주장])** | 가장 많이 나오는 수치이나 $0.07·$0.0896(재판매) 등 반대 수치가 있어 단서 추가. 공식 페이지 미확인 |
| 10 | 이용약관(2026-01-01) '사람이 만든 것처럼 표시 금지', ChatGPT·API 같은 약관 적용 | **수정** | 금지 조항은 공식 약관 페이지에서 확인. 다만 API·기업 고객은 별도 Services Agreement(2026-01-01)를 따르므로 'ChatGPT와 API 모두 같은 약관' 문장을 고침. 이 계약의 출력물 소유권(고객 소유) 추가 |
| 11 | ChatGPT 플랜 가격(Go $8 또는 $10 등), 원화 가격 미확인 | **수정** | 한국 블로그 다수 기준 Go 13,000원·Plus 29,000원·Pro 159,000원(부가세 포함). 공식 인용 없어 [주장]. §7 구독료 반영 |

- 계산 재검산: §0·§7의 게시물당·월 비용 합계는 모두 맞았습니다. 'Plus 구독료 포함 시 약 2%'로 문장만 고쳤습니다.
- 확인하지 못한 채 남긴 것: Midjourney 연 매출 기준·Stealth 조건, FLUX 단가, Nano Banana 가격, 선불 크레딧 1년 만료, ChatGPT 플랜별 이미지 한도. 쓰기 전에 각 공식 페이지에서 확인합니다.
