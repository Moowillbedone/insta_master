# X(구 트위터) 자동화 규칙과 X API 팩트 시트: 개인 크리에이터 기준

- 작성 기준일: 2026-10-14 (KST)
- 대상: @doha.dailyfit 운영자. 인스타그램에서 AI 가상 스타일리스트 '도하'의 출근룩 콘텐츠를 운영하고 있고, X에서 크리에이터 수익을 얻으려 한다. 자동화는 허용되는 범위까지만 쓴다.
- 신뢰도 태그
  - [확인]: X 공식 문서(help.x.com, docs.x.com)나 정부 1차 자료. 검색 결과에 나온 공식 페이지 발췌를 근거로 붙였다.
  - [보도]: 언론 보도나 신뢰할 만한 2차 자료
  - [주장]: 업체 블로그, 경쟁사 비교 글, 커뮤니티 글처럼 검증되지 않은 자기 주장
  - [미확인]: 이번 조사로 확인하지 못함
- 조사 한계
  - x.com, help.x.com, docs.x.com 원문은 직접 열지 못했다. 공식 문서 내용은 검색 결과에 나온 발췌와 요약을 근거로 정리했다.
  - X는 2026년 들어 API 가격, 답글 규칙, 수익 프로그램을 여러 차례 바꿨다. 실행 전에 원문을 다시 확인해야 한다.
  - 숫자는 출처마다 다를 수 있다. 출처끼리 다르면 본문에 함께 적었다.

---

## 핵심 요약

1. **"다른 사람 게시글에 자동으로 댓글 달기"는 지금 X에서 막혀 있다.**
   - 2026-02-23부터 API로 다는 답글(POST /2/tweets)은 원글 작성자가 내 계정을 @멘션했거나 내 글을 인용했을 때만 허용된다. 이 조건을 '소환(summoned)'이라고 부른다. 조건에 맞지 않는 답글은 거부된다 ([출처](https://docs.x.com/changelog), [출처](https://x.com/XDevelopers/status/2026084506822730185)) [확인].
   - 적용 대상은 셀프서브 요금제(Free, Basic, Pro, Pay-Per-Use)다. Enterprise와 Public Utility 앱은 빠진다. API로 남을 @멘션하거나 인용하는 글에도 추가 제한이 붙었다 ([출처](https://docs.x.com/changelog), [출처](https://x.com/XDevelopers/status/2026084506822730185)) [확인]. 2026년 2월쯤부터 `quote_tweet_id`로 다른 계정 글을 인용하면 오류가 난다는 개발자 보고도 있다 ([출처](https://devcommunity.x.com/t/quote-tweet-id-no-longer-works-for-cross-account-quote-posts-undocumented-change/259927)) [주장].
   - 개발자 가이드라인도 같은 방향이다. 상대가 먼저 반응했을 때만, 그 반응 1건에 답글 1개까지만 허용한다. 키워드에 반응해 자동으로 답하는 앱은 안 된다. AI로 답글을 생성하려면 X의 사전 승인이 필요하다 ([출처](https://docs.x.com/developer-guidelines)) [확인].
   - API를 거치지 않고 웹사이트를 스크립트로 조작하는 방식(Playwright·Selenium 등)도 금지다. 영구 정지까지 갈 수 있다 ([출처](https://help.x.com/en/rules-and-policies/x-automation)) [확인].
2. **자동 좋아요와 자동 팔로우도 금지이고, API에서도 빠졌다.**
   - X 자동화 규칙은 게시물 자동 좋아요를 금지하고, 대량·공격적·무차별 팔로우와 언팔로우를 위반으로 적는다. 개발자 가이드라인도 좋아요는 사용자가 직접 해야 한다고 적는다 ([출처](https://help.x.com/en/rules-and-policies/x-automation), [출처](https://docs.x.com/developer-guidelines), [출처](https://help.x.com/en/rules-and-policies/authenticity)) [확인].
   - 2026-04-20부터 셀프서브 API 전 요금제에서 팔로우, 좋아요, 인용 게시 쓰기 기능 자체가 빠졌다. X 개발자 공식 계정이 공지했다 ([출처](https://x.com/XDevelopers/status/2044919375153483812), [출처](https://docs.x.com/changelog)) [확인]. 날짜를 04-16으로 적은 정리도 있지만 공식 공지는 04-20 시행이다 ([출처](https://socialnexis.com/guides/x-api-basic-enterprise-automation-rules)) [주장].
3. **기존 수익 공유 프로그램은 2026-09-07에 종료됐다. 그리고 지급은 '주급'이 아니라 2주 단위다.**
   - X는 Creator Revenue Sharing을 끝내고 Original Content Rewards(원본 콘텐츠 보상)로 바꿨다 ([출처](https://help.x.com/en/using-x/creator-revenue-sharing), [출처](https://help.x.com/en/using-x/original-content-rewards)) [확인].
   - 새 프로그램 자격 계산은 답글 노출을 뺀다. 지급 계산은 Premium 사용자가 홈 타임라인에서 본 고유 노출만 센다 ([출처](https://help.x.com/en/using-x/original-content-rewards)) [확인].
   - 지급은 2주마다, 최소 지급액은 $30라고 보도됐다 ([출처](https://www.tech2geek.net/x-original-content-rewards-program-eligibility-payouts-and-rules/), [출처](https://x.com/healing824/status/2085873337679712328)) [보도]. 사용자가 들은 '주급'은 사실과 다르다.
   - 그래서 "남의 글에 댓글을 많이 달아 수익을 올리는" 방식은 규칙 위반 위험이 큰 데다, 이제는 수익 계산에도 거의 도움이 되지 않는다.
4. **허용되는 자동화는 "내 원본 글 예약 게시 + 내 지표 수집 + 나를 부른 멘션에 응답"까지다.**
   - API 비용은 작다. 링크 없는 글은 1건에 $0.015다 ([출처](https://docs.x.com/changelog)) [확인]. 하루 3~10건이면 한 달 약 $1.35~$4.50다(계산값).
   - 단, 링크가 들어간 글은 1건에 $0.20이다. 2026-04-20 시행 가격 변경으로 붙었다 ([출처](https://x.com/XDevelopers/status/2044919375153483812), [출처](https://docs.x.com/changelog)) [확인]. 업체 가격표들도 같은 숫자를 적는다 ([출처](https://opentweet.io/x-api-pricing), [출처](https://www.upload-post.com/x-api-pricing/)) [주장]. 쇼핑 링크를 매번 넣으면 비용이 13배 넘게 뛴다.
5. **AI 콘텐츠 표시 기능이 생겼다.**
   - X는 2026년 2월 말~3월 초 'Made with AI' 라벨을 내놓았다. 게시 화면에서 미디어를 올린 뒤 직접 켜는 방식이다 ([출처](https://techweez.com/2026/03/02/x-rolls-out-made-with-ai-label/), [출처](https://www.buzzincontent.com/news/x-introduces-made-with-ai-label-for-creator-posts-11171030)) [보도].
   - 일반 라벨은 크리에이터가 스스로 켜는 자율 토글로 출시됐다 [보도]. 예외가 하나 있다. 수익 프로그램 참여자가 무력 분쟁을 그린 AI 영상을 표시 없이 올리면 처음엔 90일, 반복하면 영구적으로 프로그램에서 빠진다 ([출처](https://www.engadget.com/social-media/x-to-require-ai-labels-on-armed-conflict-videos-from-paid-creators-citing-times-of-war-183631400.html)) [보도]. 일반 라벨이 이후 의무가 됐는지는 [미확인]이다. 그래도 도하처럼 AI로 만든 인물 이미지는 항상 켜는 쪽이 안전하다.

---

## 1. X 자동화 규칙과 플랫폼 조작·스팸 정책

### 1-1. 공식 규칙의 위치와 최근 개정

- X 자동화 규칙 페이지는 2026년 4월 개정판으로 표시돼 있다 ([출처](https://help.x.com/en/rules-and-policies/x-automation)) [확인].
- 개발자 쪽 규칙은 Developer Guidelines에 정리돼 있다 ([출처](https://docs.x.com/developer-guidelines)) [확인].
- 2026년 4월 이후 AI 답글 봇이나 AI 단독 게시물 관련 규칙이 더 바뀌었다는 정리가 있다 ([출처](https://siftfeed.com/guides/safe-vs-not-automation-on-x)) [주장]. X 원문으로는 확인하지 못했다 [미확인].

### 1-2. 허용되는 자동화

| 항목 | 상태 | 근거 |
|---|---|---|
| 내가 쓴 원본 글을 API로 예약 게시 | 허용. 글 작성 엔드포인트가 유료로 열려 있다 | [출처](https://docs.x.com/changelog) [확인] |
| 나를 @멘션하거나 내 글을 인용한 사람에게 답글 | 허용. 반응 1건당 답글 1개까지 | [출처](https://docs.x.com/changelog), [출처](https://docs.x.com/developer-guidelines) [확인] |
| 멘션 엔드포인트를 지켜보다가 들어온 @멘션에 답하는 도구 | 규칙 안에 든다고 정리됨 | [출처](https://replysurge.com/blog/x-api-reply-restriction-what-still-works) [주장] |
| AI로 초안만 만들고 사람이 직접 '게시'를 누르는 방식 | 일반적으로 문제없다고 정리됨. 기준은 "누가 게시 버튼을 누르는가"다 | [출처](https://postweavers.com/blog/ai-replies-x-ban-risk) [주장] |
| 정보 제공용 봇(날씨, 알림 등) | 'Automated' 라벨을 켜면 운영 가능 | [출처](https://docs.x.com/developer-guidelines) [확인] |

### 1-3. 금지되거나 막힌 자동화

| 항목 | 상태 | 근거 |
|---|---|---|
| 나를 부르지 않은 사람의 글에 API로 답글 | 2026-02-23부터 API가 거부 | [출처](https://docs.x.com/changelog), [출처](https://x.com/XDevelopers/status/2026084506822730185) [확인] |
| 키워드·주제 검색 결과에 자동 답글 | 금지 | [출처](https://docs.x.com/developer-guidelines) [확인] |
| AI 생성 답글 자동화 | X의 사전 승인 필요 | [출처](https://docs.x.com/developer-guidelines) [확인] |
| 위 승인이 "서면·명시적" 승인이어야 한다는 설명 | 업체 정리. 자동화 규칙(help.x.com)에 같은 문구가 있다는 검색 발췌가 한 번 나왔지만 다른 검색에서는 확인되지 않음. 개발자 포럼에는 "사전 서면 승인 요청" 글이 실제로 올라온다 | [출처](https://vorplabs.com/agent-tools/x-api), [출처](https://devcommunity.x.com/t/request-for-prior-written-approval-for-ai-generated-replies/273526) [주장] |
| 자동 좋아요 | 금지 | [출처](https://help.x.com/en/rules-and-policies/x-automation), [출처](https://docs.x.com/developer-guidelines) [확인] |
| 대량·공격적·무차별 팔로우(언팔로우 포함) | 금지 | [출처](https://help.x.com/en/rules-and-policies/x-automation), [출처](https://help.x.com/en/rules-and-policies/authenticity) [확인] |
| API로 팔로우·좋아요·인용 게시 | 2026-04-20 셀프서브 API 전 요금제에서 제거 | [출처](https://x.com/XDevelopers/status/2044919375153483812), [출처](https://docs.x.com/changelog) [확인] |
| 웹사이트 스크립트 조작 등 비(非)API 자동화 | 금지, 영구 정지 가능 | [출처](https://help.x.com/en/rules-and-policies/x-automation) [확인] |
| 게시물 보상형 앱(InfoFi) | 2026-01-15 API 정책에서 금지 | [출처](https://decrypt.co/354736/elon-musks-x-bans-access-infofi-crypto-projects-ai-slop-backlash), [출처](https://www.theblock.co/post/385805/kaito-token-plummets-x-revises-api-policies-ban-infofi-crypto-projects) [보도] |

- 다중 계정 운영, 트렌드 조작, 중복 게시 금지에 관한 플랫폼 조작·스팸 정책 원문은 이번 검색에서 직접 확인하지 못했다 [미확인]. 업계 정리 글들은 이를 정지 사유로 꼽는다 ([출처](https://opentweet.io/blog/twitter-automation-rules-2026), [출처](https://www.unfollr.com/blog/twitter-automation-rules)) [주장].

### 1-4. 'Automated' 라벨: 누가 켜야 하나

- X 개발자 가이드라인은 자동화 계정에 라벨을 달아야 한다고 적는다 ([출처](https://docs.x.com/developer-guidelines)) [확인]. 2022년 개발자 포럼 답변에는 라벨이 선택 사항이라는 말도 있었지만 공식 규칙은 아니다 ([출처](https://devcommunity.x.com/t/when-is-automation-label-required/170461)) [주장].
- X에는 API로 자동 게시하는 봇 계정용 라벨이 이미 있지만, 모든 봇이 라벨을 켜지는 않는다는 보도가 있다 ([출처](https://www.engadget.com/social-media/xs-new-parody-labels-wont-fix-its-impersonation-problem-134514427.html), [출처](https://techcrunch.com/2024/11/29/x-could-introduce-labels-for-parody-accounts-but-enforcement-might-be-tricky)) [보도].
- 판단이 애매한 부분
  - 사람이 쓰고 승인한 글을 예약 게시만 하는 크리에이터 계정이 '자동화 계정'에 들어가는지는 확인하지 못했다 [미확인].
  - 'Automated' 라벨이 Original Content Rewards 자격에 영향을 주는지도 확인하지 못했다 [미확인].
  - 라벨을 켜는 설정 경로도 이번 검색으로는 확인하지 못했다 [미확인]. 앱 설정의 계정 정보 메뉴에서 직접 확인해야 한다.
- 실무 판단: 도하 계정은 사람이 글을 검토하고 승인하는 '예약 게시 계정'으로 운영한다. 사람 검토 없이 글을 쏟아내는 봇 형태로 운영하지 않는다.

### 1-5. 위반 시 결과와 최근 단속

- **영구 정지**: 비API 자동화(웹사이트 스크립트 조작)는 영구 정지까지 갈 수 있다 ([출처](https://help.x.com/en/rules-and-policies/x-automation)) [확인]. 개발자 가이드라인도 브라우저 스크래핑을 영구 정지 시나리오로 든다 ([출처](https://docs.x.com/developer-guidelines)) [확인].
- **실제 잠금 사례**: 한 오픈소스 X 자동화 도구 저장소에 "X가 스팸 차단으로 계정을 잠갔다. 자동화가 한도를 넘었고 금지된 비API 자동화를 썼다"는 이슈가 올라와 있다 ([출처](https://github.com/azeezalhajj570-ai/xflow/issues/76)) [주장].
- **수익 프로그램 퇴출 (2026년 7월)**
  - X 제품 책임자 Nikita Bier는 답글이나 참여를 직접 유도하는 계정을 수익 공유 프로그램에서 빼겠다고 밝혔다 ([출처](https://www.socialmediatoday.com/news/x-updates-its-engagement-bait-detection/825495/)) [보도].
  - 하루에 약 4,000개 계정이 프로그램에서 빠졌고, 대부분 참여 유도(engagement bait)로 걸렸다는 정리가 있다 ([출처](https://kompozy.io/guides/x-engagement-bait-detection-update)) [주장].
  - 같은 업데이트로 중복 콘텐츠 탐지가 강화됐다. 도용 게시물 약 150만 건을 잡았고, 원작자에게 100만 달러 이상을 돌려준다는 정리도 있다 ([출처](https://kompozy.io/guides/x-engagement-bait-detection-update)) [주장].
- **InfoFi 금지 (2026-01-15)**
  - Bier는 게시 활동에 보상을 주는 앱을 더는 허용하지 않겠다고 밝혔다. 이유로 대량의 'AI slop'과 답글 스팸을 들었다 ([출처](https://decrypt.co/354736/elon-musks-x-bans-access-infofi-crypto-projects-ai-slop-backlash)) [보도].
  - 이 앱들이 이미 Enterprise API 비용으로 수백만 달러를 내고 있었지만 X는 "원하지 않는다"고 했다 ([출처](https://decrypt.co/354736/elon-musks-x-bans-access-infofi-crypto-projects-ai-slop-backlash)) [보도].
  - 대표 서비스였던 Kaito는 Yaps와 보상형 리더보드를 종료했다 ([출처](https://www.theblock.co/post/385805/kaito-token-plummets-x-revises-api-policies-ban-infofi-crypto-projects), [출처](https://whale-alert.io/stories/eb7aaf8a751c/Kaito-Shuts-Down-Yaps-After-X-Bans-Incentivized-Posts-Launches-Kaito-Studio)) [보도].
- **흐름 정리**: 2026년 X의 방향은 하나다. 1월 InfoFi 금지, 2월 비소환 답글 차단, 4월 팔로우·좋아요 API 제거, 7월 참여 유도 계정 퇴출, 9월 원본 콘텐츠 중심 보상 전환으로 이어졌다. 모두 'AI 답글 봇'과 '리플 가이(reply guy)' 수익 모델을 겨냥한다.

---

## 2. 크리에이터 수익 프로그램 변화 (자동화 판단에 필요한 부분만)

> 이 절은 자동화 전략에 영향을 주는 부분만 다룬다. 수익 구조 전체는 별도 조사로 확인해야 한다.

- **타임라인**
  - 2026-08-07: Creator Revenue Sharing 신규 가입 마감 ([출처](https://help.x.com/en/using-x/creator-revenue-sharing)) [확인].
  - 2026-09-07: 기존 프로그램 종료 ([출처](https://help.x.com/en/using-x/creator-revenue-sharing)) [확인].
  - 2026-09-08: 기존 회원도 Creator Studio에서 Original Content Rewards에 다시 신청해야 한다 ([출처](https://help.x.com/en/using-x/creator-revenue-sharing), [출처](https://www.blockmedia.co.kr/archives/1125551)) [확인].
  - 신규 프로그램 첫 지급일은 2026-08-28로 안내됐다는 X 공식 글 번역 게시물이 있다 ([출처](https://x.com/healing824/status/2085873337679712328)) [주장].
  - 위 세 날짜는 X 고객센터 페이지 발췌로 확인했다. 원문은 열지 못했다.
- **바꾼 이유**: X 크리에이터 수익화 책임자 Allegra Jacchia가 기존 프로그램의 인센티브가 어긋나 원작보다 도용을 보상했다고 말했다는 보도가 있다 ([출처](https://www.studioglobal.ai/discover/answers/what-changes-is-x-making-to-its-6a775912ecf67ecb42dc4b94), [출처](https://www.influencers-time.com/x-kills-revenue-sharing-for-original-content-rewards/)) [주장]. 검색 요약으로만 봤고 발언 원문은 확인하지 못했다.
- 기존 프로그램은 답글에 붙은 광고 수익을 나눠 답글이 많은 글이 유리했다는 보도도 있다. 다만 어느 기사인지 특정하지 못했다 [미확인].
- **새 자격 요건(X 고객센터 기준)** ([출처](https://help.x.com/en/using-x/original-content-rewards)) [확인]
  - 만 18세 이상
  - 정상 상태(good standing)의 개인 또는 비즈니스 계정
  - Premium, Premium+, Premium Business 중 하나를 구독. 고객센터 발췌에는 The X Subscription의 Plus, Premium, Super, Ultra 플랜도 인정한다고 나온다.
  - 인증 팔로워 500명 이상
  - 최근 90일 인증 사용자 홈 타임라인 노출 50만 회 이상. 답글 노출은 제외한다.
  - 원본 콘텐츠를 꾸준히 올려야 한다.
  - 심사 결과는 3영업일 안에 알려 주고, 거절되면 한 번 이의를 낼 수 있다.
- **국가와 한국**
  - 기존 Creator Revenue Sharing 고객센터 페이지의 지급 처리사 지원 국가 목록에 한국이 들어 있다 ([출처](https://help.x.com/en/using-x/creator-revenue-sharing)) [확인]. 2024년 11월 기준 국가 목록 정리 글에도 한국이 있다 ([출처](https://x.com/monetization_x/status/1856867509648986281)) [주장].
  - Original Content Rewards가 같은 국가 목록을 쓰는지는 [미확인]이다. 국가 수는 약 116개, 140개 이상 등 정리 글마다 다르다 [주장]. Creator Studio 신청 화면에서 직접 확인해야 한다.
- **노출 인정 기준(지급 계산용)**: Premium 사용자의 고유 노출만 센다. 홈 타임라인에서 글이 50% 이상 보여야 한다. 광고·프로모션 노출, 같은 계정의 반복 조회, 부정 노출은 빠진다 ([출처](https://help.x.com/en/using-x/original-content-rewards)) [확인]. 자격 요건의 50만 회가 이 '적격 노출'만 세는지, 인증 사용자 노출 전체를 세는지는 정리 글마다 다르다 [미확인].
- **자동화 관련 조건**
  - 봇이나 자동화 도구로 참여를 부풀리면 안 되고, 지급 시스템이나 추천 알고리즘을 조작하면 안 된다는 조건을 정리한 가이드가 있다 ([출처](https://www.tech2geek.net/x-original-content-rewards-program-eligibility-payouts-and-rules/), [출처](https://www.usefastlane.ai/blog/x-original-content-rewards-program)) [주장]. 자동화 계정만 따로 다루는 규칙은 찾지 못했다 [미확인].
  - Grok이 재가공하거나 살짝 고친 콘텐츠를 잡아낸다. 워터마크나 인트로를 붙여 도용을 가려도 자격을 잃는다 ([출처](https://techweez.com/2026/09/09/x-revenue-sharing-original-content-rewards/), [출처](https://internationalfinance.com/technology/x-kills-revenue-sharing-to-start-paying-only-for-work-you-actually-made/)) [보도].
- **지급 주기와 방법**
  - 주급이 아니다. 2주마다 지급하고 최소 지급액은 $30라고 보도됐다 ([출처](https://www.tech2geek.net/x-original-content-rewards-program-eligibility-payouts-and-rules/), [출처](https://x.com/healing824/status/2085873337679712328)) [보도].
  - 미국 크리에이터는 2026-09-02부터 Stripe 대신 X Money로 받는다. 미국 밖 크리에이터는 Stripe로 받고 Stripe 신원 확인을 마쳐야 한다 ([출처](https://www.storyboard18.com/digital/x-shifts-us-creator-payouts-from-stripe-to-x-money-109660.htm)) [보도].
  - 한국 거주자의 Stripe 정산 가능 여부, 원화 정산, 세금 서류는 [미확인]이다.

---

## 3. X API로 게시하기 (2026년 10월 기준)

### 3-1. 요금제: 종량제(pay-per-use)

- 2026-02-06 종량제가 시작됐고, 그때 글 작성 단가는 $0.01이었다는 정리가 있다 ([출처](https://www.upload-post.com/x-api-pricing/), [출처](https://invisibleapi.ai/blog/x-api-pricing/)) [주장].
- 2026-04-16쯤 가격 변경이 발표됐고, 04-20부터 글 작성 $0.015, 링크 포함 글 $0.20이 적용됐다. X 개발자 공식 계정이 04-20 시행을 공지했다 ([출처](https://x.com/XDevelopers/status/2044919375153483812), [출처](https://docs.x.com/changelog)) [확인]. 발표일 04-16은 업체 정리 기준이다 ([출처](https://invisibleapi.ai/blog/x-api-pricing/)) [주장].
- X changelog는 일반 글 작성 $0.015, 소환 답글 $0.01을 적고 있다 ([출처](https://docs.x.com/changelog)) [확인].
- 아직 글 작성 $0.01을 적은 2026년 글도 있다. 04-20 이전 가격이다 ([출처](https://zernio.com/blog/twitter-api-pricing)) [주장].

| 항목 | 단가 | 근거 |
|---|---|---|
| 글 작성(링크 없음) | $0.015/건 | [출처](https://docs.x.com/changelog) [확인] |
| 링크 포함 글 | $0.20/건 | [출처](https://x.com/XDevelopers/status/2044919375153483812), [출처](https://docs.x.com/changelog) [확인] |
| 소환 답글(나를 멘션·인용한 글에 답) | $0.01/건 | [출처](https://docs.x.com/changelog) [확인] |
| DM, 사용자 상호작용 | $0.015/건 | [출처](https://opentweet.io/x-api-pricing) [주장] |
| 게시물 읽기 | $0.005/건 | [출처](https://www.outstand.so/blog/x-api-pricing), [출처](https://postproxy.dev/blog/x-api-pricing-2026/) [주장] |
| 내 게시물 읽기(owned read) | $0.001/건 | [출처](https://www.upload-post.com/x-api-pricing/) [주장] |
| 미디어 업로드 | 별도 과금 여부 확인 못 함 | [미확인] |

- 결제는 선불 크레딧 방식이다. 신규 개발자용 무료 티어는 없다 ([출처](https://opentweet.io/x-api-pricing)) [주장].
- 예전 Basic($200/월)과 Pro($5,000/월)는 신규 가입을 받지 않는다 ([출처](https://opentweet.io/x-api-pricing), [출처](https://postproxy.dev/blog/x-api-pricing-2026/)) [주장].
- 월 읽기 한도는 200만 건이라는 출처와 300만 건이라는 출처가 있다 ([출처](https://www.outstand.so/blog/x-api-pricing), [출처](https://opentweet.io/x-api-pricing)) [주장]. 개인 크리에이터는 이 한도에 닿지 않는다.

### 3-2. 하루 3~10건 게시 비용 (계산값)

| 시나리오 | 월 게시 수 | 월 비용 |
|---|---|---|
| 하루 3건, 링크 없음 | 90 | $1.35 |
| 하루 10건, 링크 없음 | 300 | $4.50 |
| 하루 3건, 전부 링크 포함 | 90 | $18.00 |
| 하루 10건, 전부 링크 포함 | 300 | $60.00 |
| 내 최근 글 30개 지표를 매일 조회 | 900회 조회 | 약 $0.90 (owned read $0.001 기준), $4.50 (일반 읽기 $0.005 기준) |

- 단가는 위 표를 그대로 썼다. 미디어 업로드 비용과 세금은 빠져 있다.
- 쇼핑 링크는 본문에 넣지 않는다. 프로필 링크나 별도 링크 글을 활용하는 편이 싸다.
- 내 글에 링크를 단 답글을 이어 붙이는 경우의 처리도 확인하지 못했다. 자기 글 답글이 '소환' 조건에 맞는지, 링크 단가가 그대로 붙는지 모두 [미확인]이다.

### 3-3. 쓰기 한도(rate limit)

- POST /2/tweets: 앱 전체 24시간 10,000건, 사용자당 15분 100건이라는 정리가 있다 ([출처](https://api.sorsa.io/blog/twitter-api-rate-limits-2026)) [주장]. 공식 한도 표의 해당 행은 검색 발췌에 나오지 않아 확인하지 못했다 [미확인]. 2024~2025년 개발자 포럼에는 요금제별로 다른 숫자(Basic 사용자당 24시간 100건, 앱당 1,667건 등)가 보고돼 있다 ([출처](https://devcommunity.x.com/t/contradictory-rate-limits-for-posting-tweets-using-v2-api/230306)) [주장].
- 한도를 넘으면 창이 초기화될 때까지 HTTP 429가 돌아온다 ([출처](https://docs.x.com/x-api/fundamentals/rate-limits)) [확인].
- 하루 3~10건은 한도와 거리가 멀다. 한도보다 스팸 판정이 먼저 문제가 된다.

### 3-4. 인증: OAuth 2.0 사용자 컨텍스트 vs OAuth 1.0a

- 미디어 업로드는 사용자 컨텍스트 인증(OAuth 1.0a User Context 또는 OAuth 2.0 User Context)이 필요하다. 앱 전용 토큰으로는 안 된다는 개발자 보고가 있다 ([출처](https://devcommunity.x.com/t/how-to-upload-media-to-twitter-api-v2-using-oauth-2-0/238518)) [주장].
- OAuth 2.0에서는 인증 요청에 `media.write` 스코프를 넣어야 업로드 403 오류가 풀렸다는 보고가 있다. 기존 계정은 다시 인증해야 새 스코프가 붙는다 ([출처](https://devcommunity.x.com/t/how-to-upload-media-to-twitter-api-v2-using-oauth-2-0/238518), [출처](https://github.com/Themis128/cu130-slim/pull/303)) [주장].
- OAuth 1.0a로 v2 업로드 엔드포인트를 쓸 수 있는지는 출처가 엇갈린다 ([출처](https://devcommunity.x.com/t/chunked-upload-media-not-working-with-oauth-1-0a/242218), [출처](https://bundle.social/blog/x-api-media-upload)) [주장]. 새로 만든다면 OAuth 2.0 사용자 컨텍스트로 통일하는 편이 단순하다.
- 글 작성에 필요한 전체 스코프 목록은 docs.x.com 원문으로 확인해야 한다 [미확인].

### 3-5. 이미지·영상 업로드

- v2 분할 업로드 흐름은 INIT, APPEND, FINALIZE, STATUS 확인 순서다 ([출처](https://bundle.social/blog/x-api-media-upload), [출처](https://postproxy.dev/blog/x-twitter-api-posting-integration-guide/)) [주장].
- 이미지와 자막은 한 번에 올리는 `POST /2/media/upload`로 처리한다. 대체 텍스트(alt text)는 `POST /2/media/metadata`로 따로 붙인다는 정리가 있다 ([출처](https://bundle.social/blog/x-api-media-upload)) [주장].
- 업로드한 미디어 ID를 POST /2/tweets 요청에 붙여 글을 올린다 ([출처](https://postproxy.dev/blog/x-twitter-api-posting-integration-guide/)) [주장].
- 이미지 장수, 파일 크기, 영상 길이 제한은 이번 조사에서 확인하지 못했다 [미확인].

### 3-6. 내 게시물 지표(노출수, 참여) 읽기

- 내 글의 노출수(impressions) 같은 비공개 지표를 어떤 필드와 스코프로, 어떤 기간까지 읽을 수 있는지 2026년 기준으로 확인하지 못했다 [미확인].
- 내 글 읽기 단가 $0.001만 확인됐다 ([출처](https://www.upload-post.com/x-api-pricing/)) [주장].
- 실무 대안: 처음에는 X 앱의 분석 화면에서 직접 숫자를 옮겨 적는다. API 지표 수집은 원문 확인 후 붙인다.

---

## 4. 서드파티 예약 도구 (API 직접 개발 대신)

- 예약 도구도 X API 위에서 돌아간다. 그래서 위 규칙이 똑같이 적용된다. 자동 좋아요, 자동 팔로우, 비소환 답글은 도구를 써도 안 된다 ([출처](https://docs.x.com/developer-guidelines), [출처](https://docs.x.com/changelog)) [확인].
- 2026년 API 변경이 각 도구의 예약 기능에 어떤 영향을 줬는지 설명한 자료는 찾지 못했다 [미확인].

| 도구 | X 지원 | 가격(출처별) | 근거 |
|---|---|---|---|
| Buffer | 지원. 출처들이 일치 | 무료: 채널 3개, 채널당 예약 10건. 유료는 채널당 월 $6부터 | [출처](https://www.blotato.com/blog/best-x-twitter-schedulers), [출처](https://posteverywhere.ai/blog/best-x-twitter-scheduler) [주장] |
| Typefully | 지원으로 정리됨 | 출처마다 월 $8, $12.50, $15 등 다름. 연 $99(Creator)라는 정리도 있음. 무료 예약은 1건 또는 3건 | [출처](https://www.blotato.com/blog/best-x-twitter-schedulers), [출처](https://xautopilot.app/blog/typefully-pricing-plans-costs-value-2026) [주장] |
| Hypefury | 엇갈림. 경쟁사 Blotato는 "2026년 X 지원 중단"이라고 적었고, 다른 2026년 비교 글은 여전히 X 도구로 소개 | 월 $29부터 | [출처](https://www.blotato.com/blog/best-x-twitter-schedulers), [출처](https://socialrails.com/blog/hypefury-pricing) [주장] |

- 가격과 지원 여부는 모두 업체·경쟁사 블로그 기준이다. 결제 전에 각 업체 가격 페이지를 확인해야 한다.
- 비용 비교: 하루 10건 이하, 링크 없는 글이면 API 직접 비용은 월 $5 안팎이다(3-2절 계산). 예약 도구는 편의성과 X 앱 미리보기를 사는 비용이다.

---

## 5. AI 생성 콘텐츠, 합성 미디어, 사칭·패러디 규칙

### 5-1. 'Made with AI' 라벨

- X는 2026년 2월 말~3월 초 'Made with AI' 라벨을 출시했다. 크리에이터가 게시 화면에서 켜서 AI로 만들거나 조작한 텍스트, 이미지, 영상임을 밝힌다 ([출처](https://techweez.com/2026/03/02/x-rolls-out-made-with-ai-label/), [출처](https://www.buzzincontent.com/news/x-introduces-made-with-ai-label-for-creator-posts-11171030), [출처](https://techmoran.com/2026/03/03/x-introduces-made-with-ai-labels-for-creators/)) [보도]. 켜는 순서는 미디어 업로드 → 깃발 아이콘 → 'Made with AI' 켜기라는 사용자 안내가 있다 ([출처](https://x.com/cb_doge/status/2027885910969274679)) [주장].
- 일반 라벨은 크리에이터가 스스로 켜는 자율 토글로 출시됐다. 곧 의무화될 것이라는 전망 기사는 있지만 X 정책으로 확인된 것은 아니다 ([출처](https://techweez.com/2026/03/02/x-rolls-out-made-with-ai-label-puts-disclosure-pressure-on-creators/)) [보도].
- 의무 표시가 확인된 범위는 좁다. 2026-03-03 Nikita Bier는 수익 프로그램 참여자가 무력 분쟁을 그린 AI 영상을 표시 없이 올리면 처음엔 90일, 반복하면 영구적으로 프로그램에서 빼겠다고 밝혔다. 커뮤니티 노트나 생성형 AI 메타데이터로 잡아낸다 ([출처](https://www.engadget.com/social-media/x-to-require-ai-labels-on-armed-conflict-videos-from-paid-creators-citing-times-of-war-183631400.html)) [보도]. 이 규칙이 Original Content Rewards에도 이어지는지는 [미확인]이다.
- 2026년 1월 해롭거나 오해를 부르는 편집물에 자동으로 붙는 'Manipulated Media' 태그가 도입됐다는 정리가 있다 ([출처](https://susit.ai/blog/platform-policies-ai-content-2026)) [주장].

### 5-2. Grok 생성물

- X는 Grok으로 만든 이미지와 영상에 워터마크를 붙인다고 정리됐다 ([출처](https://susit.ai/blog/platform-policies-ai-content-2026), [출처](https://www.exchange4media.com/digital-news/x-rolls-out-ai-content-labels-as-it-seeks-to-stabilise-advertising-revenue-152469.html)) [주장].
- 한 독립 테스트에서는 ChatGPT 이미지는 X에서 AI 라벨이 붙었지만 Grok·Gemini 이미지는 붙지 않은 경우가 있었다 ([출처](https://susit.ai/blog/platform-policies-ai-content-2026)) [주장]. 자동 라벨에 기대지 말고 직접 켜야 한다.
- Grok 이미지 도구는 성적 딥페이크 논란을 겪었다 ([출처](https://en.wikipedia.org/wiki/Grok_sexual_deepfake_scandal)) [보도].
- 캐나다 개인정보보호위원회는 xAI가 2026년 3월에야 Grok Imagine을 개인정보 영향평가에 넣었다고 적었다 ([출처](https://www.priv.gc.ca/en/opc-actions-and-decisions/investigations/investigations-into-businesses/2026/pipeda-2026-004/)) [확인].
- 도하 운영 기준: 실존 인물 얼굴을 합성하지 않는다. 브랜드 모델 사진을 참조 이미지로 쓰지 않는다.

### 5-3. 사칭과 패러디·논평·팬(PCF) 라벨

- X는 2025년 1월 패러디 계정 라벨을 도입했다. 다른 사람이나 단체를 묘사하는 계정이 직접 켜서 혼동이나 제휴 오해를 막는 용도다 ([출처](https://www.socialsamosa.com/news-2/x-labels-parody-satire-accounts-8607885), [출처](https://www.engadget.com/social-media/xs-new-parody-labels-wont-fix-its-impersonation-problem-134514427.html)) [보도].
- 이후 PCF 계정은 계정 이름 앞에 PCF 키워드를 넣고, 묘사 대상과 같은 프로필 사진을 쓰지 말라는 요건이 보도됐다 ([출처](https://www.marketing-interactive.com/x-tightens-the-screws-on-parody-and-fan-accounts)) [보도]. 의무화 여부와 현재 문구는 [미확인]이다.
- 도하는 실존 인물을 묘사하지 않는 독자 캐릭터다. 그래서 PCF 라벨 대상은 아닌 것으로 본다(판단). 대신 프로필에 'AI 가상 스타일리스트'임을 밝혀 실존 인물로 오해받지 않게 한다.

---

## 6. 브라우저 자동화(Playwright·Selenium)와 스크래핑

- **웹사이트 자동 조작은 금지다.** X 자동화 규칙은 웹사이트 스크립트 조작 같은 비API 자동화를 하지 말라고 하고, 영구 정지까지 경고한다 ([출처](https://help.x.com/en/rules-and-policies/x-automation)) [확인]. Playwright나 Selenium으로 x.com에 로그인해 글쓰기, 댓글, 좋아요를 하는 방식이 여기에 해당한다.
- **브라우저 스크래핑도 금지다.** 개발자 가이드라인은 브라우저 스크래핑을 영구 정지 시나리오로 들고, 공식 API를 쓰라고 한다 ([출처](https://docs.x.com/developer-guidelines)) [확인].
- **약관상 손해배상 조항**
  - 2024-11-15 시행 X 약관에 '손해배상 예정액' 조항이 추가됐다. 약관을 어기고 24시간에 게시물 100만 건 넘게 접근하면 $15,000를 물린다는 내용이다 ([출처](https://knightcolumbia.org/content/knight-institute-says-xs-new-terms-of-service-will-stifle-independent-research)) [보도].
  - EU·영국 이용자 버전은 EUR 15,000이라는 정리가 있다 ([출처](https://conductatlas.com/platform/x/x-terms-of-service/liquidated-damages-for-excessive-post-access-eu/)) [주장].
  - 법원에서 이 조항이 유효한지는 정해지지 않았다 ([출처](https://conductatlas.com/platform/x/x-terms-of-service/liquidated-damages-for-excessive-post-access/)) [주장].
- **"잘 버는 계정 다 확인하기" 작업에 적용하면**
  - 사람이 직접 몇십 개 계정을 둘러보고 메모하는 것은 일반 이용이다.
  - 수백·수천 개 계정 글을 스크립트로 긁는 것은 약관과 자동화 규칙 위반 위험이 있다.
  - API로 남의 글을 읽으면 1건에 $0.005다 ([출처](https://www.outstand.so/blog/x-api-pricing)) [주장]. 계정 20개 × 최근 글 50개 = 1,000건이면 약 $5다(계산값). 소규모 벤치마킹이라면 비용 부담이 작다.
  - 남의 글이나 이미지를 가져와 재가공해 올리면 Original Content Rewards에서 탈락한다 ([출처](https://techweez.com/2026/09/09/x-revenue-sharing-original-content-rewards/)) [보도]. 벤치마킹은 형식과 주제만 참고하고 문장과 이미지는 새로 만든다.

---

## 운영에 바로 쓰는 결론

- **댓글 자동화는 만들지 않는다.** 남의 글에 자동 댓글을 다는 기능은 API가 거부하고(2026-02-23~), 브라우저로 우회하면 영구 정지 위험이 있다. 게다가 새 보상 프로그램은 답글 노출을 세지 않는다. 남의 글 댓글은 하루 10~20개 정도 사람이 직접 단다.
- **자동 좋아요, 자동 팔로우·언팔로우, 맞팔 툴은 쓰지 않는다.** X 자동화 규칙상 금지이고, 2026-04-20부터 셀프서브 API에서도 빠졌다.
- **'주급' 기대는 버린다.** 새 보상은 2주 단위 지급, 최소 $30로 보도됐다. 한국 거주자가 새 프로그램에서 실제로 받을 수 있는지는 신청 화면에서 확인해야 한다.
- **자동화 범위는 세 가지로 정한다.**
  1. AI(도하 파이프라인)로 글·이미지 초안을 만든다.
  2. 사람이 검토하고 승인한 글만 API나 예약 도구로 예약 게시한다.
  3. 내 글 지표를 수집하고, 나를 @멘션한 글에 답할 초안을 만든다. 게시는 사람이 누른다.
- **게시 방법 선택**
  - 직접 개발: X 개발자 계정과 OAuth 2.0 사용자 인증(`media.write` 포함)으로 POST /2/media/upload → POST /2/tweets 구조를 만든다. 하루 3~10건, 링크 없는 글 기준 월 $1.35~$4.50다.
  - 개발 없이 시작: Buffer 무료 플랜(채널 3개, 예약 10건)으로 먼저 운영해 보고, 필요할 때 API로 옮긴다.
- **링크는 본문에 넣지 않는다.** API 기준으로 링크 포함 글은 $0.20이라 13배 넘게 비싸다. 쿠팡 파트너스 등 제휴 링크는 프로필 링크나 별도 링크 페이지로 모은다.
- **모든 도하 이미지 글에 'Made with AI' 라벨을 켠다.** 프로필 소개에 'AI 가상 스타일리스트'를 적는다. 실존 인물 얼굴과 브랜드 모델 사진은 쓰지 않는다.
- **참여 유도 문구를 쓰지 않는다.** "댓글 달면 ○○ 드려요", "RT하면" 같은 문구는 2026년 7월 단속 대상이다. 질문형 캡션은 정보 질문으로만 쓴다.
- **원본성 확보**: 다른 계정의 글이나 이미지를 번역·편집해 올리지 않는다. 인스타그램 도하 콘텐츠를 X에 올릴 때도 X에 맞게 문장을 새로 쓴다.
- **벤치마킹은 손으로 한다.** 잘되는 X 계정 10~20개를 사람이 직접 보고 형식, 게시 시간, 스레드 구조를 기록한다. 스크래핑 도구는 쓰지 않는다.
- **수익 목표를 다시 잡는다.** 새 보상 프로그램 요건(Premium 구독, 인증 팔로워 500명, 90일 인증 사용자 홈 노출 50만 회)은 신규 계정에 높은 문턱이다. 초기 X 수익은 플랫폼 보상보다 인스타그램 유입과 브랜드 협찬 포트폴리오 쪽에서 기대하는 편이 현실적이다.
- **'Automated' 라벨 판단**: 사람 승인 기반 예약 게시만 하면 일반 크리에이터 계정으로 운영한다. 사람 검토 없이 자동 게시하는 순간 'Automated' 라벨 대상이 되고, 보상 자격에 영향이 있을 수 있으니 그런 운영은 하지 않는다.

---

## 남은 확인 사항

- [ ] X 자동화 규칙(help.x.com) 원문: 2026년 4월 이후 추가 개정 여부, AI 답글·AI 단독 게시물 관련 문구
- [ ] 플랫폼 조작·스팸 정책 원문: 다중 계정, 중복 게시, 트렌드 조작 기준
- [x] 2026-04-20 팔로우·좋아요·인용 게시 API 제거: X Developers 공지로 시행일 확인(2026-10-14 검증)
- [ ] 공식 가격 페이지: owned read $0.001, 미디어 업로드 과금 여부, 월 읽기 한도(200만 vs 300만). 링크 포함 글 $0.20은 공지로 확인됨
- [ ] 공식 한도 표: POST /2/tweets 앱·사용자 한도(10,000/24h, 100/15분은 2차 자료만 있음)
- [ ] 내 글 비공개 지표(노출수 등)를 읽는 필드, 필요한 스코프, 조회 가능 기간
- [ ] 글 작성과 미디어 업로드에 필요한 OAuth 2.0 스코프 전체 목록
- [ ] 이미지 장수, 파일 크기, 영상 길이 등 미디어 제한
- [ ] 자기 글에 다는 답글(스레드)이 '소환' 조건에 걸리는지, 링크 단가가 적용되는지
- [ ] 'Automated' 라벨 설정 경로, 예약 게시만 하는 크리에이터 계정이 대상인지, 보상 자격에 주는 영향
- [ ] Original Content Rewards: 한국 포함 여부(기존 프로그램 목록엔 포함), 한국 거주자 Stripe 정산, 세금 서류. 지급 주기는 2주·최소 $30로 보도됨(공식 문서로는 미확인)
- [ ] 'Made with AI' 일반 라벨이 의무화됐는지에 대한 X 공식 문구(출시 시점엔 자율, 무력 분쟁 AI 영상만 수익 참여자에게 의무)
- [ ] Typefully, Buffer, Hypefury의 현재 X 지원 상태와 가격(각 업체 가격 페이지)

---

## 검증 메모 (2026-10-14)

반박 시도 방식: 영어·한국어 웹 검색 12회. 공식 페이지는 검색 발췌로만 봤다. 아래 10개 외 항목(InfoFi 금지, 2026년 7월 참여 유도 단속, 약관 손해배상, 예약 도구 가격 등)의 출처 URL은 이번에 다시 확인하지 않았다.

| # | 주장 | 판정 | 이유 |
|---|---|---|---|
| 1 | 2026-02-23부터 API 답글은 소환된 경우만 허용 | 유지 | changelog와 X Developers 공지가 일치. Enterprise·Public Utility 제외와 @멘션·인용 추가 제한을 보탰다. |
| 2 | AI 생성 답글은 사전 승인, 키워드 자동 답글 금지 | 유지 | 개발자 가이드라인 발췌로 확인. '서면·명시적' 문구는 검색 결과가 엇갈려 [주장] 유지. |
| 3 | 자동 좋아요·대량 팔로우 금지 | 수정 | 근거를 개발자 가이드라인에서 자동화 규칙(help.x.com)과 Authenticity 정책으로 바꿨다. 둘 다 금지 문구 확인. |
| 4 | 2026-04-20 셀프서브 API에서 팔로우·좋아요·인용 게시 제거 | 수정(상향) | X Developers 공식 공지로 04-20 시행 확인. [주장]→[확인]. 04-16은 업체 한 곳만 적음. |
| 5 | 기존 프로그램 08-07 가입 마감, 09-07 종료, 09-08 재신청 | 수정(상향) | X 고객센터 Creator Revenue Sharing 페이지 발췌로 세 날짜 확인. [보도]→[확인]. 확인 안 된 언론 URL은 공식 페이지로 교체. |
| 6 | Original Content Rewards 자격(18세, Premium, 인증 팔로워 500, 90일 홈 노출 50만, 답글 제외) | 수정(상향) | X 고객센터 OCR 페이지 발췌로 확인. 정상 상태 계정, X Subscription 플랜, 원본 게시, 3영업일 심사, 이의 1회를 보탰다. |
| 7 | 지급 주기 [미확인] / 사용자 전제 '주급' | 수정 | 주급이 아니라 2주 단위, 최소 $30라고 보도됨. 미국은 09-02부터 X Money, 해외는 Stripe. 공식 문서 발췌는 못 봐서 [보도]. |
| 8 | 한국 포함 여부 [미확인] | 수정(부분) | 기존 프로그램 지급 국가 목록에 한국 포함 [확인]. OCR이 같은 목록인지는 여전히 [미확인]. |
| 9 | 글 $0.015, 링크 글 $0.20, 소환 답글 $0.01 | 수정(상향) | $0.20이 X Developers 04-20 가격 변경 공지에 있다는 발췌 확인. [주장]→[확인]. $0.01 표기 글은 04-20 이전 가격. |
| 10 | POST /2/tweets 한도 10,000/24h(앱), 100/15분(사용자) | 하향 | 공식 한도 표에서 해당 행을 찾지 못했고 2차 블로그만 같은 숫자. 포럼에는 요금제별 다른 숫자. [확인]→[주장]. 429는 공식 문서로 확인. |
| 11 | 'Made with AI' 라벨 의무 여부 [미확인] | 수정 | 출시 시점엔 자율 토글. 수익 참여자의 무력 분쟁 AI 영상만 미표시 시 90일·영구 퇴출(Engadget). 확인 안 된 URL 2개 삭제. |
| 12 | 웹사이트 스크립트 조작 등 비API 자동화 금지, 영구 정지 가능 | 유지 | 자동화 규칙과 개발자 가이드라인 발췌 모두 같은 문구. |
