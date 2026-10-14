# X(구 트위터) 고팔로워·고정산 계정 패턴 분석: 도하 계정에 옮길 수 있는 강점과 버릴 것

- 작성 기준일: 2026-10-14 (KST)
- 대상: @doha.dailyfit 운영자. 인스타그램에서 AI 가상 스타일리스트 '도하'의 한국어 출근룩 콘텐츠를 운영하고 있고, X에서 크리에이터 보상을 받으려 한다.
- 요청 배경: "팔로우 수 높고 주급 많이 받는 애들"의 장점을 모아 내 계정에 적용하고 싶다는 요청이다.
- 함께 볼 문서: [x-automation-api.md](./x-automation-api.md)는 자동화 규칙과 API를 다룬다. 이 문서는 "누가, 무엇으로, 얼마를 받았나"와 "그중 무엇을 따라 해도 되나"를 다룬다.
- 신뢰도 태그
  - [확인]: X 공식 도움말(help.x.com), X 공식 계정(@XCreators), X 제품 책임자 본인 게시물 같은 1차 자료. 원문을 직접 열지 못해 검색 결과 발췌를 근거로 했다.
  - [보도]: 언론 보도. 정산 금액은 대부분 언론이 크리에이터 본인의 스크린샷이나 발언을 옮긴 것이다. X가 금액을 확인해 준 사례는 찾지 못했다.
  - [주장]: 개인 게시물, 업체 블로그, 계산기 사이트, 위키, 강의 판매 페이지처럼 검증되지 않은 자료
  - [미확인]: 이번 조사로 확인하지 못함
  - [분석]: 위 자료를 바탕으로 한 이 문서의 추론이나 계산값. 사실이 아니라 판단이다.
- 조사 한계
  - x.com 원문은 열지 않았다. 스크래핑도 하지 않았다. X 게시물은 검색 결과 발췌로만 봤다.
  - X 게시물의 작성 시점은 게시물 ID(스노플레이크 ID)에서 계산했다. 계산 방법이 공개돼 있어 신뢰도는 높지만, 게시물 내용 자체는 발췌 기준이다.
  - 검색 요약이 여러 기사를 묶어 설명한 경우가 있다. 그럴 때는 해당 기사들을 함께 걸고, 어느 기사의 문장인지 특정하지 못했다고 적었다.
  - **한국 계정의 큰 정산 금액을 언론이 보도한 사례는 찾지 못했다.** 한국 사례는 모두 개인 후기 수준이다.

---

## 핵심 요약

1. **'주급'이 아니라 2주 단위 지급이고, 프로그램 자체가 바뀌었다.**
   - 지급은 2주마다 이뤄지고 최소 지급액은 $30이다. 미국 밖 사용자는 Stripe로 받는다 ([출처](https://help.x.com/en/using-x/original-content-rewards)) [확인].
   - 기존 Creator Revenue Sharing은 끝났다. 마지막 지급은 2026-09-11(금)이었다. 새 프로그램 Original Content Rewards(OCR)의 첫 지급은 2026-09-25다 ([출처](https://x.com/XCreators/status/2097371482804363669)) [확인].
   - 그러니 "주급 많이 받는 계정"의 과거 스크린샷은 대부분 지금은 없는 프로그램 기준이다.
2. **큰 금액 사례는 드물고, 오래됐고, 초대형 계정 이야기다.**
   - MrBeast가 영상 1개로 $263,655를 받았다는 화면을 공개했다(2024-01). 본인도 이 숫자를 '보여주기(facade)'라고 불렀다 ([출처](https://edition.cnn.com/2024/01/23/tech/mr-beast-x-video-worth), [출처](https://www.fortune.com/2024/01/23/mrbeast-jimmy-donaldson-youtube-tests-x-revenue-elon-musk/)) [보도].
   - 2023-07 첫 지급 때 $7천~$3만7천을 받았다는 계정들은 팔로워 70만 명 이상이었다 ([출처](https://techcrunch.com/?p=2569087), [출처](https://thewrap.com/twitter-creators-payments-ad-revenue-plan)) [보도].
   - 2026년의 큰돈은 정산이 아니라 일회성 상금이었다. 장문 Article 대회 1등이 $1M을 받았다. 미국 거주자만 참가할 수 있었다 ([출처](https://www.socialmediatoday.com/news/x-awards-1-million-to-top-article-for-january/811396/), [출처](https://www.kucoin.com/news/flash/x-announces-winners-of-1m-long-form-writing-contest-beaverd-takes-top-prize)) [보도].
3. **2026년 단속은 '고정산 계정'이 쓰던 방식을 정확히 겨냥했다.**
   - 4월: 뉴스 모음(aggregator) 계정의 지급액을 60%로 깎고 다음 회차에 20%를 더 줄였다. '🚨BREAKING'을 습관적으로 붙이는 계정도 지급을 줄였다 ([출처](https://techcrunch.com/2026/04/12/x-says-its-reducing-payments-to-clickbait-accounts/), [출처](https://www.nbcnews.com/tech/social-media/x-slashes-aggregator-payouts-boost-original-creators-rcna324820)) [보도].
   - 7월: "답글 달면 다 팔로우할게" 같은 참여 요청을 3번 이상 하면 프로그램에서 퇴출한다고 밝혔다. 그날 약 4,000개 계정이 빠졌다 ([출처](https://x.com/nikitabier/status/2077774853650944028)) [확인].
   - 2월: 나이지리아 크리에이터 약 80%의 수익 공유가 중단됐다 ([출처](https://technext24.com/2026/02/15/why-x-cut-payments-for-nigerian-creators/)) [보도].
4. **새 프로그램에서는 답글이 돈이 되지 않는다.**
   - 인정 노출은 Premium 사용자가 홈 타임라인에서 본 고유 노출이다. 글이 절반 이상 보여야 한다 ([출처](https://help.x.com/en/using-x/original-content-rewards), [출처](https://x.com/XCreators/article/2085835082166653393)) [확인].
   - 답글 노출은 계산에서 빠진다고 보도됐다 ([출처](https://www.netinfluencer.com/x-details-eligibility-rules-for-new-original-content-rewards-program/)) [보도].
   - 따라서 "다른 사람 글에 댓글 자동화"는 규칙 위반 위험만 있고 수익에는 도움이 거의 안 된다. 규칙 쪽 근거는 [x-automation-api.md](./x-automation-api.md)에 있다.
5. **한국 데이터는 작다.**
   - 한국 사용자 후기 1건: 조회수 500만을 넘긴 뒤 첫 정산 약 $10, 2주 뒤 약 $40을 받았다(2024-07) ([출처](https://x.com/chwj77/status/1814517957168664940?lang=ko)) [주장].
   - 한국은 Premium 가입 비중이 낮아 단가가 영미권보다 낮을 수 있다는 설명이 있다 ([출처](https://linkfarm.ai/blog/x-creator-monetization-incentives-2026)) [주장].
6. **도하에게 X 정산은 부수입 수준이다.** 직접 정산보다 원본 이미지와 장문 가이드로 인지도를 쌓는 보조 채널로 보는 편이 현실적이다 [분석]. 근거는 7절에 정리했다.

---

## 1. 사례 모음: 누가 얼마를 받았다고 했나

> 정산 금액을 X가 공식 확인한 사례는 하나도 찾지 못했다. [보도]도 "언론이 본인 주장을 옮겼다"는 뜻이다. 팔로워 수는 출처에 나온 경우만 적었다.

### 1-1. 해외 사례

| # | 계정·사례 | 팔로워 | 분야 | 주장·보도 금액 | 시점 | 근거 유형 |
|---|---|---|---|---|---|---|
| 1 | MrBeast | 초대형(수치 [미확인]) | 영상 | 영상 1개로 $263,655. 화면 공개 ([출처](https://edition.cnn.com/2024/01/23/tech/mr-beast-x-video-worth), [출처](https://www.fortune.com/2024/01/23/mrbeast-jimmy-donaldson-youtube-tests-x-revenue-elon-musk/)) | 2024-01 | [보도] 본인 공개 화면 |
| 2 | 익명 크리에이터 (MrBeast 사례 반박) | [미확인] | [미확인] | 노출 3,000만 회에 $102.57 ([출처](https://www.creatorhandbook.net/mrbeast-exposes-elon-musk-for-facade-250k-x-payout-to-lure-creators/)) | 2024-01 | [주장] |
| 3 | Billy Markus (@BillyM2k) | [미확인] | 도지코인 공동창업자 | $37,000 이상 ([출처](https://thewrap.com/twitter-creators-payments-ad-revenue-plan)) | 2023-07 | [보도] 본인 게시 |
| 4 | Brian Krassenstein | 약 75만 | 작가 | $24,305 ([출처](https://techcrunch.com/?p=2569087)) | 2023-07 | [보도] 본인 주장. 다른 매체는 형제 Ed로 적어 엇갈린다 ([출처](https://www.channelnews.com.au/twitter-pays-out-millions-to-verified-accounts/)) |
| 5 | Ashley St. Clair | 약 71만 | Babylon Bee 작가 | $7,153 ([출처](https://techcrunch.com/?p=2569087)) | 2023-07 | [보도] 본인 주장 |
| 6 | 380K 팔로워 크리에이터(익명) | 38만 | [미확인] | 70일간 $131.03 ([출처](https://x.com/MohiniWealth/status/1976626371116835268)) | 2025-10 게시 | [주장] 제3자 전언 |
| 7 | Beaverd (@beaverd) | [미확인] | 장문 분석(미국 정부 IT와 Deloitte) | Article 대회 1등 상금 $1M. 해당 Article 조회 4,471만 ([출처](https://www.kucoin.com/news/flash/x-announces-winners-of-1m-long-form-writing-contest-beaverd-takes-top-prize), [출처](https://www.socialmediatoday.com/news/x-awards-1-million-to-top-article-for-january/811396/)) | 2026-02-04 발표 | [보도] 상금이지 정산이 아님 |
| 8 | The Kobeissi Letter | [미확인] | 금융·시장 해설로 알려짐 [미확인] | 같은 대회 2등 $500,000 ([출처](https://www.kucoin.com/news/flash/x-announces-winners-of-1m-long-form-writing-contest-beaverd-takes-top-prize)) | 2026-02 | [보도] |
| 9 | DAN KOE | [미확인] | 자기계발·크리에이터 글쓰기로 알려짐 [미확인] | Creator's Choice $250,000 ([출처](https://www.kucoin.com/news/flash/x-announces-winners-of-1m-long-form-writing-contest-beaverd-takes-top-prize)) | 2026-02 | [보도] |
| 10 | 뉴스 모음(aggregator) 계정 전반 | 대형 | 뉴스 큐레이션·속보 | 지급액 60%로 삭감 후 20% 추가 삭감 예고 ([출처](https://techcrunch.com/2026/04/12/x-says-its-reducing-payments-to-clickbait-accounts/), [출처](https://www.emarketer.com/content/x-cuts-aggregator-payouts-curb-spam-reward-original-creators)) | 2026-04-12 | [보도]. 근거는 모두 Bier 본인 게시물이다 |
| 11 | 참여 유도 계정 약 4,000개 | 다양 | 맞팔·답글 유도 | 프로그램 퇴출 ([출처](https://x.com/nikitabier/status/2077774853650944028)) | 2026-07-16 | [확인] Bier 게시물 발췌 |
| 12 | MrBeast (2회차) | 초대형 | 참여 유도 게시물 | Bier가 "이번 회차엔 지급하지 않는다"고 댓글. 이후 삭제 ([출처](https://www.sportskeeda.com/us/streamers/news-mrbeast-engagement-farming-x-controversy-explained-nikita-bier-appears-target-recent-post), [출처](https://www.latestly.com/socially/technology/mrbeast-wont-be-paid-for-engagement-farming-on-x-says-product-head-nikita-bier-7415118.html)) | 2026-05 | [보도]. 실제 미지급 여부는 [미확인] |
| 13 | 나이지리아 크리에이터 | 다양 | 다양 | 상위권이 월 최대 $500 수준. 2026-02-14에 약 80% 지급 중단 ([출처](https://technext24.com/2026/02/15/why-x-cut-payments-for-nigerian-creators/), [출처](https://techpression.com/x-halts-payouts-for-nigerian-creators-spam-bots-blamed/)) | 2026-02 | [보도]. 금액이 두 기사 중 어디 문장인지 특정하지 못함 |
| 14 | 영국 암호화폐 인플루언서 | [미확인] | 암호화폐 | X가 부당 수령 정산금 최소 £207,384 반환 소송 ([출처](https://technext24.com/reviews/x-sues-engagement-farmers-revenue-fraud/)) | 2026 [미확인] | [보도] |
| 15 | 인도·케냐 등에서 미국·일본인 행세한 계정 | 다양 | 다양 | 현지 지역 참여를 우대하는 가중치 도입 예고 ([출처](https://www.androidheadlines.com/2026/03/x-revenue-sharing-update-local-engagement-payouts.html)) | 2026-03 | [보도]. 이후 보류됐다는 말이 있으나 [미확인] |

### 1-2. 한국 사례

| # | 계정·사례 | 팔로워 | 분야 | 주장 금액·내용 | 시점 | 근거 유형 |
|---|---|---|---|---|---|---|
| 16 | Dr.차우준 (@chwj77) | [미확인] | 일본 유학·정보 | 조회수 500만 달성 후 첫 정산 약 $10, 2주 뒤 두 번째 $40 남짓 ([출처](https://x.com/chwj77/status/1814517957168664940?lang=ko)) | 2024-07-20 게시 | [주장] |
| 17 | 같은 게시물 반응 | - | - | 첫 정산은 금액이 작아 계좌로 들어오지 않았다는 내용과, 연 수익이 일정 수준을 넘으면 건강보험료·종합소득세 부담 때문에 수익화를 하지 않겠다는 의견이 함께 검색됐다 ([출처](https://x.com/chwj77/status/1814517957168664940?lang=ko)) | 2024-07 | [주장] 작성자가 본인인지 [미확인] |
| 18 | 한국 X 육성 기록 (Threads 게시물) | [미확인] | 계정 키우기 기록 | 수익화 조건(팔로워 500, 노출 500만) 도전 과정 공유 ([출처](https://www.threads.com/@im_planner927/post/DZrnqOOk6BT/%EC%9A%94%EC%A6%98-x%EA%B5%AC-%ED%8A%B8%EC%9C%84%ED%84%B0%EB%A5%BC-%ED%82%A4%EC%9B%8C%EB%B3%B4%EA%B3%A0-%EC%9E%88%EB%8A%94%EB%8D%B0%EC%9A%94x-%EC%88%98%EC%9D%B5%ED%99%94-%EC%A1%B0%EA%B1%B4%EC%9E%85%EB%8B%88%EB%8B%A41-%ED%8C%94%EB%A1%9C%EC%9B%8C-500%EB%AA%852-%EA%B2%8C%EC%8B%9C%EB%AC%BC-500%EB%A7%8C%ED%9A%8C-%EC%9D%B4%EC%83%81-%EB%85%B8%EC%B6%9C2%EB%B2%88%EC%9D%B4-%EC%89%BD%EC%A7%80-%EC%95%8A%EC%9D%84%EB%93%AF%ED%95%98%EC%A7%80%EB%A7%8C-%EA%BE%B8%EC%A4%80%ED%9E%88%ED%95%B4%EB%B3%B8-%EA%B2%B0%EA%B3%BC/)) | 2026 [미확인] | [주장]. 옛 기준이다 |
| 19 | 한국어 수익화 안내 게시물 | [미확인] | 수익화 팁 | 수익화 계정을 '정직원'이라 부르는 표현이 쓰인다 ([출처](https://x.com/cosake12/status/2014127958848586053)) | 2026-01-22 게시 | [주장] |

### 1-3. 사례에서 읽히는 것 [분석]

- 큰 금액(수만~수십만 달러)은 2023~2024년, 팔로워 수십만~초대형, 영어권 계정에 몰려 있다.
- 2026년에는 정산보다 단속 뉴스가 훨씬 많다. "주급 많이 받는 계정"의 과거 방식이 지금도 통한다고 볼 근거가 없다.
- 한국어 계정이 의미 있는 금액을 받았다는 공개 자료는 찾지 못했다. 조회수 500만에 $10~$40 수준이 유일한 구체 사례다.
- 2026년 큰돈을 받은 쪽(Article 대회)은 모두 **원본 장문 분석**이었다. 다만 대회는 미국 거주자 한정의 일회성 행사였다.

---

## 2. 수익 구조 변화: 과거 사례를 읽기 위한 배경

### 2-1. 예전 프로그램은 '답글 광고'를 나눴다

- 2023년 7월 시작한 수익 공유는 인기 게시물의 **답글 사이에 붙은 광고** 수익 일부를 나누는 방식이었다 ([출처](https://edition.cnn.com/2024/01/23/tech/mr-beast-x-video-worth), [출처](https://www.fortune.com/2024/01/23/mrbeast-jimmy-donaldson-youtube-tests-x-revenue-elon-musk/)) [보도].
- 첫 회 지급 총액은 약 $500만이었다 ([출처](https://techcrunch.com/?p=2569087)) [보도]. 두 달 뒤 누적 약 $2,000만이 됐다 ([출처](https://www.mediapost.com/publications/article/389736/x-ceo-says-platform-has-paid-creators-20m.html)) [보도].
- 2023년 이후 누적 지급액이 $4,500만을 넘었다는 국내 보도가 있다 ([출처](https://www.digitaltoday.co.kr/news/articleView.html?idxno=637756)) [보도].
- 이 구조 때문에 논쟁을 부르는 '핫테이크'나 속보처럼 답글이 많이 달리는 글이 유리했다 [분석].

### 2-2. 노출 100만 회당 단가: 공식 수치 없음

- X는 노출당 단가를 공개하지 않는다 ([출처](https://www.gemlist.io/blog/how-much-does-x-twitter-pay-creators), [출처](https://tweetranking.com/how-much-does-twitter-pay/)) [주장].
- 계산기 사이트들은 인증 노출 100만 회당 약 $3~$15, 중간값 약 $8.50로 본다. 미국 Premium+ 시청자는 최대 $29.75까지 적는다 ([출처](https://www.xpayoutcalculator.com/updates/x-creator-payout-rates-per-million-impressions-2026/), [출처](https://posteverywhere.ai/blog/how-much-does-twitter-x-pay-creators)) [주장].
- 이 숫자는 끝난 프로그램 기준이라 OCR에는 그대로 맞지 않을 수 있다 ([출처](https://opentweet.io/blog/twitter-x-side-hustle-how-much-x-pays-creators-2026)) [주장].

### 2-3. 새 프로그램 OCR (2026-09-08부터)

- **자격**: 최근 90일 인증 사용자 홈 타임라인 노출 50만 회, 인증 팔로워 500명. 노출은 Premium Basic, Premium, Premium+, Premium Business 사용자가 홈 타임라인에서 본 경우만 센다 ([출처](https://www.digitalasset.works/news/articleView.html?idxno=42905)) [보도]. 세부 조건은 출처마다 조금씩 다르다. [x-automation-api.md](./x-automation-api.md) 2절을 함께 볼 것.
- **인정 노출**: Premium 사용자의 고유 노출, 홈 타임라인, 글의 절반 이상이 화면에 보인 경우 ([출처](https://help.x.com/en/using-x/original-content-rewards), [출처](https://x.com/XCreators/article/2085835082166653393)) [확인].
- **지급**: 2주마다, 최소 $30. 미국은 X Money, 미국 밖은 Stripe 계정 연결과 본인 확인 ([출처](https://help.x.com/en/using-x/original-content-rewards)) [확인]. 미국 크리에이터 지급을 X Money로 옮긴 것은 2026-09 초 보도됐다 ([출처](https://techcrunch.com/2026/09/02/x-shifts-us-creator-payouts-from-stripe-to-x-money/)) [보도].
- **지급일**: 첫 OCR 지급 2026-09-25(금) ([출처](https://x.com/XCreators/status/2097371482804363669)) [확인]. 2주 주기가 유지되면 이후는 10-09, 10-23 순서가 된다 [분석].
- **한국 포함 여부**
  - 예전 프로그램 도움말은 한국을 Stripe 지급 가능 국가로 적었다 ([출처](https://help.x.com/en/using-x/creator-revenue-sharing)) [확인].
  - OCR 국가 목록에 한국이 있다는 자료는 제3자 글 1건뿐이다 ([출처](https://www.ray256.com/2026/09/can-africans-make-money-on-x-countries.html)) [주장]. 공식 목록 확인은 [미확인].

### 2-4. 2026년 변화 타임라인

| 날짜 | 변화 | 근거 |
|---|---|---|
| 2026-01-15 | 게시 활동에 보상하는 InfoFi 앱 금지 | [x-automation-api.md](./x-automation-api.md) 1-5 ([출처](https://decrypt.co/354736/elon-musks-x-bans-access-infofi-crypto-projects-ai-slop-backlash)) [보도] |
| 2026-01-16~28 | $1M 장문 Article 대회(미국 거주자 한정) | ([출처](https://www.kucoin.com/news/flash/x-announces-winners-of-1m-long-form-writing-contest-beaverd-takes-top-prize)) [보도] |
| 2026-01-19 | 추천 알고리즘 코드 공개(보도 기준) | ([출처](https://opentweet.io/blog/x-algorithm-open-source-github-2026)) [주장] |
| 2026-02-14 | 나이지리아 크리에이터 약 80% 지급 중단 | ([출처](https://technext24.com/2026/02/15/why-x-cut-payments-for-nigerian-creators/)) [보도] |
| 2026-03 | 현지 지역 참여 우대 가중치 예고 | ([출처](https://www.androidheadlines.com/2026/03/x-revenue-sharing-update-local-engagement-payouts.html)) [보도], 시행 여부 [미확인] |
| 2026-04-12 | 뉴스 모음 계정 지급 60%로 삭감, '🚨BREAKING' 습관 계정 감액 | ([출처](https://techcrunch.com/2026/04/12/x-says-its-reducing-payments-to-clickbait-accounts/)) [보도] |
| 2026-05 | MrBeast 참여 유도 게시물에 Bier가 미지급 언급 후 삭제 | ([출처](https://www.latestly.com/socially/technology/mrbeast-wont-be-paid-for-engagement-farming-on-x-says-product-head-nikita-bier-7415118.html)) [보도] |
| 2026-07-16 | 참여 요청 3회 이상 시 퇴출, 약 4,000개 계정 퇴출, 도용 게시물 150만 건 | ([출처](https://x.com/nikitabier/status/2077774853650944028)) [확인] |
| 2026-08-07 | 기존 프로그램 신규 가입 마감, OCR 발표 | ([출처](https://www.digitalasset.works/news/articleView.html?idxno=42905)) [보도] |
| 2026-09-07~11 | 기존 프로그램 적립 종료, 마지막 지급 9-11 | ([출처](https://x.com/XCreators/status/2097371482804363669)) [확인] |
| 2026-09-25 | 첫 OCR 지급 | ([출처](https://x.com/XCreators/status/2097371482804363669)) [확인] |

---

## 3. 고정산 계정이 쓰던 포맷과 지금의 상태

| 포맷 | 왜 통했나 | 2026-10 현재 상태 | 도하 적용 |
|---|---|---|---|
| 뉴스 모음·속보 | 빠른 노출, 답글 많음 | 지급 60% 이하로 삭감 ([출처](https://techcrunch.com/2026/04/12/x-says-its-reducing-payments-to-clickbait-accounts/)) [보도] | 쓰지 않는다 |
| 핫테이크·논쟁 | 예전엔 답글 광고 수익이 컸음 [분석] | OCR은 답글 노출을 뺀다 ([출처](https://www.netinfluencer.com/x-details-eligibility-rules-for-new-original-content-rewards-program/)) [보도] | 정치·성별 논쟁은 피한다. "출근룩 A vs B" 같은 가벼운 의견 묻기 정도만 |
| 장문 Article | 2026 대회 상위권이 모두 원본 장문 분석 ([출처](https://www.socialmediatoday.com/news/x-awards-1-million-to-top-article-for-january/811396/)) [보도]. Premium 사용자는 2만5천 자까지 쓸 수 있다는 정리가 있다 ([출처](https://www.socialync.io/blog/x-twitter-articles-strategy-2026)) [주장] | 원본성 중심 OCR과 방향이 맞음 [분석] | 월 1~2편 "체형별 출근룩 공식" 같은 앵커 글 |
| 영상 | MrBeast 사례 | 일정 길이 이상 영상이 추가 노출 단계를 연다는 코드 해석이 있다 ([출처](https://adlibrary.com/posts/x-algorithm-open-source-phoenix-model-explained), [출처](https://publora.com/blog/x-algorithm-open-source)) [주장] | 인스타 릴스용 착장 전환 영상을 X용으로 다시 편집 |
| 이미지·짤 | 저비용·고확산 | 도용·재편집 탐지 강화. 워터마크나 인트로를 붙여도 수익 노출은 원작자에게 간다 ([출처](https://x.com/nikitabier/status/2077774853650944028)) [확인] | 도하 이미지는 자체 제작이라 유리. 남의 사진은 쓰지 않는다 |
| 질문·투표 | 답글·투표 참여 | "답글 달면 팔로우" 식 요청은 퇴출 사유 ([출처](https://x.com/nikitabier/status/2077774853650944028)) [확인]. 평범한 의견 질문이 어디까지 허용되는지는 [미확인] | 대가 없는 진짜 질문만. 보상 약속, 맞팔 약속은 금지 |
| 큰 계정에 답글 | 노출과 팔로워 유입 | 답글 노출은 OCR 계산 제외 [보도]. API 자동 답글은 막힘(→ [x-automation-api.md](./x-automation-api.md)) [확인] | 성장용으로만, 사람이 직접, 하루 몇 개 |
| 내 글 답글에 직접 응답 | 대화 지속 | 작성자가 응답한 답글이 강한 신호라는 코드 해석이 있다 ([출처](https://opentweet.io/blog/x-algorithm-open-source-github-2026), [출처](https://postory.io/blog/x-algorithm-2026)) [주장] | 내 글에 달린 답글은 성실히 직접 답한다 |
| 링크만 있는 글 | 외부 유입 | 링크 단독 글은 점수 전에 걸러진다는 해석이 있다 ([출처](https://postory.io/blog/x-algorithm-2026), [출처](https://explainx.ai/blog/x-algorithm-open-source-github-elon-musk-2026)) [주장] | 본문에 가치를 담고, 링크는 필요할 때만 |

> 알고리즘 관련 [주장] 항목은 같은 검색에 나온 블로그 여러 개를 묶은 요약이다. 어느 블로그의 문장인지 하나로 특정하지 못해 함께 걸었다.

### 3-1. 게시 빈도

- 같은 작성자 글은 일정 구간에 3개까지만 보여주는 '작성자 다양성' 필터가 있다는 코드 해석이 있다 ([출처](https://postory.io/blog/x-algorithm-2026), [출처](https://publora.com/blog/x-algorithm-open-source)) [주장].
- 신뢰할 만한 '최적 게시 빈도' 데이터는 찾지 못했다 [미확인].
- 해석: 하루에 몰아서 많이 올리기보다 시간대를 나눠 원본 글 몇 개를 올리는 편이 낫다 [분석].
- 알고리즘 가중치에 대한 블로그 해석은 서로 엇갈린다. 원본 저장소로 언급되는 github.com/xai-org/x-algorithm을 직접 확인해야 한다 [미확인].

### 3-2. 언어: 영어냐 한국어냐

- 인도·케냐 등에서 미국인·일본인 행세를 하던 계정을 겨냥해, 내 지역 사용자 참여를 우대하는 방안이 2026-03 예고됐다 ([출처](https://www.androidheadlines.com/2026/03/x-revenue-sharing-update-local-engagement-payouts.html)) [보도]. 이후 보류됐다는 말이 있으나 [미확인].
- 한국은 Premium 가입 비중이 낮아 단가가 영미권보다 낮을 수 있다는 설명이 있다 ([출처](https://linkfarm.ai/blog/x-creator-monetization-incentives-2026)) [주장].
- 미국 Premium+ 시청자 단가가 가장 높다는 계산기 수치가 있다 ([출처](https://www.xpayoutcalculator.com/updates/x-creator-payout-rates-per-million-impressions-2026/)) [주장].
- 정리 [분석]
  - 영어 글이 단가는 높을 수 있다. 하지만 한국 거주자가 미국인처럼 보이게 꾸미는 것은 지금 X가 단속하려는 패턴이다.
  - 도하의 강점(한국 직장인 출근룩, 한국 브랜드)은 한국어 오디언스에서 나온다. 영어 병기는 해외 K-패션 관심층이 실제로 반응할 때만 늘린다.

---

## 4. 한국 X 문화

### 4-1. 이용자 규모

| 수치 | 시점 | 근거 |
|---|---|---|
| 한국 X 월간 활성 사용자 약 760만 명, 스레드 650만 명(2025년 초)으로 격차 약 120만 명 | 2025-10 기준, 2026-03-08 게시 | ([출처](https://x.com/babybluecream/status/2030554311512469602)) [주장] 개인 분석 |
| 스레드 692만 명, X 757만 명 | '지난해 말' 기준(연도 [미확인]) | 검색 요약상 와이즈앱·리테일 조사 인용. 두 기사 중 어느 쪽 문장인지 특정 못함 ([출처](https://www.youthassembly.kr/news/867535), [출처](https://www.aipostkorea.com/news/articleView.html?idxno=10516)) [보도] |
| 스레드가 모바일 사용자 수에서 X를 추월 | 기사 날짜 [미확인] | ([출처](https://www.aipostkorea.com/news/articleView.html?idxno=10516)) [보도] |
| X 월간 활성 사용자 약 462만 명, 20대 비중이 가장 높음 | 2023 | 아이지에이웍스 인용 ([출처](https://m.ddaily.co.kr/page/view/2023082215061101959)) [보도] |
| X가 "한국에서 곧 1,000만 명"이라고 밝힘 | 2024 세미나 | ([출처](https://gogumafarm.kr/x%ED%8A%B8%EC%9C%84%ED%84%B0-%EC%9A%B4%EC%98%81-%EC%9E%98%ED%95%98%EA%B8%B0-%EC%9C%84%ED%95%9C-%EC%A1%B0%EA%B1%B4%EA%B3%BC-%EC%A3%BC%EC%9D%98-%EC%82%AC%ED%95%AD-%EB%A7%88%EC%BC%80%ED%84%B0%EA%B0%80/)) [주장] 마케터 블로그의 전언 |

- 조사 기관마다 측정 방식이 달라 숫자가 엇갈린다. 대략 "700만 명대, 스레드가 바짝 추격" 정도로만 쓰는 것이 안전하다 [분석].
- 한국 X의 성별 구성이 글로벌 X와 반대라는 분석이 있다 ([출처](https://x.com/babybluecream/status/2030554311512469602)) [주장]. 세부 비율은 [미확인].
- **한국 Premium(인증) 사용자 수는 공개된 자료를 찾지 못했다** [미확인]. 수익 계산에 가장 중요한 숫자인데 비어 있다.

### 4-2. 인기 분야

- 한국 X는 '오타쿠들의 SNS'라는 인식이 있다. 아이돌 팬덤, 애니메이션, 그림 작가 같은 동인 계층이 활발하다 ([출처](https://namu.wiki/w/X(SNS)/%EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD)) [주장].
- 일상, 유머, 문화, 서브컬처, 생활정보 콘텐츠도 많다고 정리돼 있다 ([출처](https://namu.wiki/w/X(SNS)/%EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD)) [주장].
- 팬덤 문화 용어도 따로 있다. 예를 들어 '총공계'는 K-POP·뮤지컬 팬들이 구매와 응원을 독려하는 계정을 말한다 ([출처](https://namu.wiki/w/X(SNS)/%EC%9A%A9%EC%96%B4)) [주장].
- 재테크·AI 툴·패션 코디 계정이 한국 X에서 얼마나 크게 자리 잡았는지는 자료를 찾지 못했다 [미확인].

### 4-3. 한국 수익화 정보 생태계

- 한국어 수익화 안내는 2025년 기준(노출 500만)과 2026년 OCR 기준(홈 타임라인 노출 50만)이 섞여 돌아다닌다 ([출처](https://gobooki.net/%EC%B5%9C%EA%B7%BC-x-%EC%88%98%EC%9D%B5%ED%99%94-%EC%A0%95%EC%B1%85-%EC%A0%95%EB%A6%AC/), [출처](https://www.digitalasset.works/news/articleView.html?idxno=42905)) [주장]/[보도]. 날짜를 꼭 확인해야 한다.
- 한국어 계산기 페이지도 X 단가가 유튜브보다 매우 낮다고 적는다 ([출처](https://demoday.co.kr/tools/x-revenue)) [주장].
- Premium 비용을 연 9만 원 정도로 적은 정리가 있다 ([출처](https://gobooki.net/%EC%B5%9C%EA%B7%BC-x-%EC%88%98%EC%9D%B5%ED%99%94-%EC%A0%95%EC%B1%85-%EC%A0%95%EB%A6%AC/)) [주장]. 현재 가격은 [미확인].

---

## 5. 위험 신호

1. **참여 유도(engagement bait)**
   - "답글 달면 다 팔로우" 같은 참여 요청을 3번 이상 하면 프로그램에서 퇴출되고, 정지 검토 대상으로 넘겨진다. Grok이 이를 잡아낸다고 했다 ([출처](https://x.com/nikitabier/status/2077774853650944028)) [확인].
   - 초대형 계정도 예외가 아니었다. MrBeast 게시물에 미지급 언급이 나왔다 ([출처](https://www.sportskeeda.com/us/streamers/news-mrbeast-engagement-farming-x-controversy-explained-nikita-bier-appears-target-recent-post)) [보도].
2. **낚시성 속보 표기**: '🚨BREAKING'을 모든 글에 붙이는 계정은 지급이 줄었다 ([출처](https://techcrunch.com/2026/04/12/x-says-its-reducing-payments-to-clickbait-accounts/)) [보도].
3. **남의 콘텐츠 재가공**: 중복 탐지율이 예전 모델의 3배다. 한 회차에 도용 게시물 150만 건을 잡았다 ([출처](https://x.com/nikitabier/status/2077774853650944028)) [확인].
4. **리플 가이(reply guy)·AI 답글**
   - X는 'AI slop'과 답글 스팸을 이유로 보상형 앱을 금지했다 ([출처](https://decrypt.co/354736/elon-musks-x-bans-access-infofi-crypto-projects-ai-slop-backlash)) [보도].
   - API 답글은 원글 작성자가 나를 부른 경우만 허용된다. 상세는 [x-automation-api.md](./x-automation-api.md) [확인].
5. **집단 조작과 지역 일괄 정지**: 나이지리아에서 약 80% 지급 중단. 알고리즘 공략법을 파는 유료 강의(₦3,000짜리 포함)가 원인 중 하나로 거론됐다 ([출처](https://technext24.com/2026/02/15/why-x-cut-payments-for-nigerian-creators/)) [보도].
6. **환수 소송**: 참여 조작으로 받은 정산금에 대해 X가 소송을 냈다 ([출처](https://technext24.com/reviews/x-sues-engagement-farmers-revenue-fraud/)) [보도].
7. **지역 위장**: 미국 VPN 노드를 쓰고 기기 언어와 지역을 영어로 바꿔 인증을 빨리 통과했다는 후기가 돈다 ([출처](https://x.com/NewGoX/status/2039361530077352424)) [주장]. 지역 위장 단속 흐름(3-2절)과 정면으로 부딪힌다. 따라 하지 않는다.
8. **강의 판매형 '수익 인증'**
   - 검색에 강의 판매 사이트의 '수강생 수익 인증' 게시판이 걸린다 ([출처](https://cclass.kr/board/%EC%88%98%EA%B0%95%EC%83%9D-%EC%88%98%EC%9D%B5-%EC%9D%B8%EC%A6%9D/101/)) [주장]. 홍보 목적 자료라 숫자를 검증할 수 없다.
   - 나이지리아 사례처럼 "알고리즘 공략 강의"가 대량 정지의 원인으로 지목되기도 했다 [보도].
9. **브랜드 안전**: $1M 대회 1등 작성자에게 인종차별 게시 이력이 있다는 보도가 있다 ([출처](https://www.socialmediatoday.com/news/x-awards-1-million-to-top-article-for-january/811396/)) [보도]. X에서 잘 터지는 계정이 협찬 브랜드에게 안전한 계정은 아니다. 도하는 협찬 수익이 본업이므로 이 차이가 중요하다 [분석].

---

## 6. 종합: 옮겨올 강점과 따라 하지 말 것

### 6-1. 옮겨올 강점 (도하 기준)

1. **원본 우선**: 직접 만든 이미지와 직접 쓴 해설만 올린다. 도용 탐지가 강해질수록 원본 제작자가 유리하다 ([출처](https://x.com/nikitabier/status/2077774853650944028)) [확인]. 도하 이미지는 자체 생성물이라 이 점에서 출발이 좋다 [분석].
2. **장문 앵커 글**: 2026년 큰 보상은 원본 장문 분석이 받았다 [보도]. 예: "체형별 출근룩 공식", "월 10만 원 출근룩 캡슐 옷장" 같은 Article을 월 1~2편 [분석].
3. **포맷 고정 시리즈**: 요일별 출근룩, 날씨별 코디처럼 반복 포맷을 정한다. 팔로우 이유가 분명해진다 [분석].
4. **본문 완결형 정보 글**: 링크를 누르지 않아도 가치가 있는 글을 쓴다. 링크 단독 글은 불리하다는 해석이 있고 [주장], API로 링크 글을 올리면 비용도 커진다(→ [x-automation-api.md](./x-automation-api.md)).
5. **진짜 질문과 투표**: "내일 미팅룩 A vs B" 같은 질문. 보상이나 맞팔을 약속하지 않는다 ([출처](https://x.com/nikitabier/status/2077774853650944028)) [확인].
6. **내 글 답글에 직접 응답**: 작성자가 응답한 답글이 강한 신호라는 해석이 있다 [주장]. 사람이 직접 답한다.
7. **큰 계정에 수동·선별 답글**: 패션·직장인·한국 브랜드 계정에 의미 있는 답글을 하루 몇 개 단다. 수익이 아니라 팔로워 유입용이다. 답글 노출은 OCR에서 빠진다 [보도].
8. **짧은 영상 재활용**: 인스타 릴스의 착장 전환 영상을 X 비율로 다시 편집해 올린다 [분석]. 영상 우대 해석이 있다 [주장].
9. **AI 표시와 투명성**: 'Made with AI' 라벨을 켠다(→ [x-automation-api.md](./x-automation-api.md) 5절). 가상 인물임을 소개글에 밝힌다 [분석].
10. **한국어 중심, 영어는 반응을 보고**: 지역 위장 단속 흐름과 도하의 강점을 함께 고려한 선택이다 [분석].
11. **간격을 둔 게시**: 몰아서 올리지 않는다. 작성자 다양성 필터 해석에 따른 판단이다 [주장]/[분석].
12. **지표 관리**: Premium 홈 타임라인 노출을 따로 추적한다. 50만 회 기준까지 남은 거리를 주 단위로 본다 [분석]. Creator Studio에서 이 수치를 볼 수 있는지는 [미확인].

### 6-2. 따라 하지 말 것

- '🚨BREAKING', 과장 제목, 남의 뉴스 퍼 나르기
- 남의 사진·짤 재업로드. 워터마크를 붙여도 소용없다
- "답글 달면 맞팔", 팔로우 트레인, 리트윗 이벤트로 노출 사기
- 자동 댓글 봇, AI 대량 답글, 브라우저 자동화
- 미국 VPN이나 영어 설정으로 지역 위장, 외국인 행세
- 정치·성별 갈등으로 답글 끌어내기
- "수익 인증" 강의 구매와 알고리즘 공략법

---

## 7. 도하 페르소나의 X 수익 적합도

### 7-1. 분야별 비교 [분석]

> 아래 평가는 이 문서의 판단이다. 분야별 X 정산 데이터는 공개된 것이 없다.

| 분야 | Premium 시청자 비중 (추정) | 원본성 확보 | 2026 단속 위험 | 도하와의 시너지 | 종합 |
|---|---|---|---|---|---|
| 도하: AI 출근룩 (한국어) | 낮음 (한국 Premium 비중 낮다는 주장 [주장], 패션 관심층과 Premium 겹침 [미확인]) | 높음 (자체 이미지) | 낮음 | 최고 (인스타 자산 재활용) | 정산은 작고 브랜드 가치는 큼 |
| 한국어 재테크·AI 툴 정보 | 중간 [미확인] | 중간 (뉴스 요약으로 흐르기 쉬움) | 중간 (모음 계정 감액) | 낮음 | 페르소나 분산 위험 |
| 영어 금융·시장 장문 분석 | 높음 (대회 2등이 이 계열 [보도]) | 노력하면 높음 | 낮음~중간 | 없음 | 도하와 무관, 새 계정이 필요 |
| 한국 팬덤·덕질 | 낮음 [미확인] | 낮음 (공식 사진 재업 위험) | 높음 (도용 탐지) | 없음 | 부적합 |
| 뉴스 큐레이션·속보 | 중간 | 낮음 | 높음 (60% 감액) | 없음 | 부적합 |

### 7-2. 숫자로 본 현실 [분석]

- 계산 가정: 인증 노출 100만 회당 $3~$15 ([출처](https://www.xpayoutcalculator.com/updates/x-creator-payout-rates-per-million-impressions-2026/)) [주장]. 이 수치는 끝난 프로그램 기준이라 OCR에서 다를 수 있다.
- 한 달 Premium 홈 타임라인 노출 100만 회라면 월 $3~$15 정도다(계산값).
- 최소 지급액이 $30이라, 이 규모에서는 2~10개월 쌓여야 한 번 받는다(계산값).
- Premium 구독료(연 9만 원 정도로 적은 국내 정리가 있다 ([출처](https://gobooki.net/%EC%B5%9C%EA%B7%BC-x-%EC%88%98%EC%9D%B5%ED%99%94-%EC%A0%95%EC%B1%85-%EC%A0%95%EB%A6%AC/)) [주장], 월 약 7,500원)를 빼면 초기에는 적자일 수 있다.
- 한국 실제 후기(조회수 500만에 $10~$40)도 같은 범위다 ([출처](https://x.com/chwj77/status/1814517957168664940?lang=ko)) [주장].
- 결론: 도하 계정의 X 가치는 정산보다 **브랜드 협찬과 제휴 링크의 보조 채널**에 있다. 협찬·제휴 전략은 [01-monetization-playbook.md](../01-monetization-playbook.md), [08-affiliate-guide.md](../08-affiliate-guide.md)를 따른다.

---

## 운영에 바로 쓰는 결론

- **'주급' 기대는 접는다.** 지급은 2주 단위, 최소 $30이다 [확인]. 2026-09-07 이전 스크린샷과 강의 자료는 지금 프로그램 기준이 아니다.
- **"남의 글에 댓글 자동화"는 하지 않는다.** API로는 막혀 있고, 답글 노출은 OCR 정산에서 빠지며, 참여 유도는 퇴출 사유다 [확인]/[보도]. 큰 계정 답글은 사람이 직접, 하루 몇 개만 단다.
- **자동화는 내 원본 글 예약 게시와 지표 수집까지만** 쓴다. 세부 규칙은 [x-automation-api.md](./x-automation-api.md)를 따른다.
- **도하의 무기는 원본 이미지다.** 인스타 출근룩 이미지와 릴스를 X용으로 다시 편집해 하루 2~4개를 간격을 두고 올린다 [분석]. 'Made with AI' 라벨을 켠다.
- **월 1~2편 장문 Article을 앵커로 둔다.** 예: "체형별 출근룩 공식", "직장인 캡슐 옷장 10벌".
- **질문·투표는 대가 없이.** "A vs B 어느 쪽?"은 쓰되, "답글 달면 맞팔·추첨"은 절대 쓰지 않는다.
- **한국어 중심으로 운영한다.** 영어 병기는 해외 반응이 실제로 확인될 때만. VPN·영어 설정으로 지역을 위장하지 않는다.
- **OCR 자격 조건(인증 팔로워 500, 90일 홈 타임라인 노출 50만)을 주간 지표로 추적한다.** 도달 전에는 Premium 비용 대비 수익이 마이너스일 수 있다는 점을 받아들인다 [분석].
- **수익의 중심은 협찬·제휴로 둔다.** X는 인지도와 신뢰를 쌓는 보조 채널이다. 정치·혐오 논쟁 계정과 엮이지 않게 관리해 브랜드 안전을 지킨다.
- **'수익 인증' 강의는 사지 않는다.** 나이지리아 대량 정지 사례에서 알고리즘 공략 강의가 원인 중 하나로 거론됐다 [보도].

---

## 남은 확인 사항

1. **OCR 국가 목록에 한국이 있는지**: help.x.com 원문에서 확인해야 한다. 지금은 제3자 글 1건만 있다 [미확인].
2. **한국 Premium(인증) 사용자 규모**: 수익 계산의 핵심인데 공개 자료를 찾지 못했다.
3. **OCR 단가**: 2026-09-25 이후 실제 정산 사례가 아직 보도되지 않았다. 10월 이후 한국·해외 후기를 다시 찾아야 한다.
4. **AI 생성 이미지가 OCR에서 '원본'으로 인정되는지**: Grok 원본 판정이 AI 이미지를 어떻게 다루는지 [미확인].
5. **의견 질문·투표의 허용 범위**: "참여 요청"의 경계가 어디인지 공식 기준을 찾지 못했다.
6. **지역 참여 가중치**: 2026-03 예고안이 시행 중인지, 보류됐는지 [미확인].
7. **알고리즘 가중치**: 블로그 해석이 엇갈린다. github.com/xai-org/x-algorithm 원본 코드로 확인해야 한다.
8. **최적 게시 빈도와 시간대**: 신뢰할 만한 데이터를 찾지 못했다. 도하 계정 자체 데이터로 4~8주 실험해 정해야 한다.
9. **한국 X의 패션·재테크·AI 툴 분야 규모**: 분야별 인기 계정 자료를 찾지 못했다.
10. **세금과 건강보험**: X 정산을 받을 때 종합소득세·건강보험료 영향은 [kr-compliance.md](./kr-compliance.md) 기준으로 따로 확인해야 한다.
11. **Premium 현재 가격(한국)**: 연 9만 원, 월 $8 같은 수치는 오래된 정리일 수 있다.
