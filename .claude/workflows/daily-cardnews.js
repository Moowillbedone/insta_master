export const meta = {
  name: 'daily-cardnews',
  description: 'Daily info card-news package: sweep Naver blog / Instagram / news trends, pick the most viral-worthy topic, fact-check, write ChatGPT image prompts + caption, adversarial review',
  whenToUse: 'Every morning (KST) to produce content/daily/<date>/package.md for the info-type Instagram account. args: {date: "YYYY-MM-DD"}',
  phases: [
    { title: 'Sweep', detail: 'four trend scouts with different lenses' },
    { title: 'Select', detail: 'dedupe, score, pick topic + backups + style' },
    { title: 'Facts', detail: 'verify every date/place/price from official sources' },
    { title: 'Produce', detail: 'write package.yaml, daily-check, daily-md' },
    { title: 'Review', detail: 'adversarial fact + copy + prompt review, fix' },
  ],
}

const DATE = (args && args.date) || ''
if (!DATE) throw new Error('args.date (YYYY-MM-DD, KST) is required')

const CTX = `
Repo: /home/user/insta_master (cwd). Today (KST): ${DATE}. You work on the DAILY INFO CARD-NEWS package for a Korean Instagram info account (all categories: 핫플·팝업·축제·전시·맛집·신상·혜택·생활꿀팁·시즌·이슈). Read docs/11-daily-cardnews.md first — it is the SOP (scoring rubric, red lines, slide/prompt rules).
Search: use WebSearch (load with ToolSearch "select:WebSearch" if needed; mode "extended" for fresh/niche facts). WebFetch is blocked for most sites. Never scrape or log into instagram.com / naver.com; use search results only. Cite URLs exactly as returned; never invent URLs, dates, prices or names.
Red lines: no politics/elections, tragedies/accidents, crime, celebrity gossip or private individuals, medical/health efficacy, investment/crypto advice, adult/gambling, copying another account's images or text. Prefer topics with an official source (기관·주최·브랜드 공식 발표).
`

const CANDIDATES = {
  type: 'object',
  properties: {
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string', description: 'card-news topic in Korean, e.g. "이번 주말 서울 단풍 절정 명소 5곳"' },
          category: { type: 'string' },
          why_now: { type: 'string', description: 'why it should be posted today (dates, deadline, surge)' },
          evidence: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                source: { type: 'string', enum: ['naver_blog', 'instagram', 'news', 'official', 'other'] },
                url: { type: 'string' }, note: { type: 'string' }, date: { type: 'string' },
              },
              required: ['source', 'url', 'note'],
            },
          },
          official_source: { type: 'string', description: 'official URL that can confirm the facts, or empty' },
          card_angle: { type: 'string', description: 'hook + list structure, e.g. "무료 입장 3곳 + 날짜·가는 길"' },
          risk: { type: 'string', description: 'any red-line or accuracy risk' },
        },
        required: ['title', 'category', 'why_now', 'evidence', 'card_angle'],
      },
    },
  },
  required: ['candidates'],
}

const LENSES = [
  { key: 'naver', prompt: `LENS: Naver blog & Naver search signals. Find what Korean bloggers are writing about RIGHT NOW (last 3-7 days): seasonal outings, pop-ups, festivals, new menus, 혜택·신청 기간. Queries like "site:blog.naver.com ${DATE.slice(0, 7)} 가볼만한곳", "이번 주말 가볼만한 곳", "요즘 핫한 팝업", "10월 축제 일정", "신청 마감 이번주", plus category words. Up to 18 searches. Return 4-6 candidates.` },
  { key: 'instagram', prompt: `LENS: Instagram virality. Find topics that are spreading on Instagram/SNS now and card-news formats that get saved/shared (lists with dates, free/discount info, 한정 기간). Use searches that surface coverage of SNS buzz ("인스타에서 화제", "SNS 인증샷 명소", "릴스 유행", "오픈런 팝업", "품절 대란") and popular info-card themes. Up to 18 searches. Return 4-6 candidates.` },
  { key: 'calendar', prompt: `LENS: Date-bound public info (highest save value). Events, festivals, exhibitions, ticket openings, government/city benefits and application deadlines, discounts/sales seasons, weather-driven seasonal moments (단풍 절정, 첫눈, 한파) happening within the next 1-14 days in Korea (Seoul/수도권 first, then 전국). Prefer official announcements (지자체, 공공기관, 주최측). Up to 18 searches. Return 4-6 candidates.` },
  { key: 'consumer', prompt: `LENS: Consumer & new launches. New convenience-store/franchise menus, limited collabs, pop-up stores, beauty/fashion sales (올리브영·무신사 등 행사 일정), app/service changes people must know this week. Must be verifiable from brand official channels or press. Up to 18 searches. Return 4-6 candidates.` },
]

phase('Sweep')
const sweeps = await parallel(LENSES.map(l => () =>
  agent(`${CTX}\n${l.prompt}\nFor each candidate include at least 2 evidence items with URLs and dates; mark the freshest signal.`,
    { label: `sweep:${l.key}`, phase: 'Sweep', schema: CANDIDATES })))
const pool = sweeps.filter(Boolean).flatMap(s => s.candidates || [])
log(`후보 ${pool.length}개 수집`)
if (!pool.length) throw new Error('no candidates found')

phase('Select')
const SELECT = {
  type: 'object',
  properties: {
    chosen: {
      type: 'object',
      properties: {
        title: { type: 'string' }, category: { type: 'string' }, why_now: { type: 'string' },
        card_angle: { type: 'string' }, style: { type: 'string', enum: ['info-warm', 'info-night', 'info-clean'] },
        evidence: { type: 'array', items: { type: 'object', properties: { source: { type: 'string' }, url: { type: 'string' }, note: { type: 'string' }, date: { type: 'string' } }, required: ['source', 'url', 'note'] } },
        official_source: { type: 'string' },
        score: { type: 'object', properties: { timeliness: { type: 'number' }, save_share: { type: 'number' }, breadth: { type: 'number' }, visual: { type: 'number' }, verifiability: { type: 'number' }, risk: { type: 'number' }, total: { type: 'number' } }, required: ['total'] },
      },
      required: ['title', 'category', 'why_now', 'card_angle', 'style', 'evidence', 'score'],
    },
    backups: { type: 'array', items: { type: 'object', properties: { title: { type: 'string' }, category: { type: 'string' }, why_now: { type: 'string' }, score_total: { type: 'number' } }, required: ['title', 'why_now'] } },
    recent_topics_checked: { type: 'array', items: { type: 'string' } },
    reasoning: { type: 'string' },
  },
  required: ['chosen', 'backups', 'reasoning'],
}
const pick = await agent(`${CTX}
You are the editor choosing TODAY's single card-news topic. Candidates from four scouts (JSON):
${JSON.stringify(pool, null, 1)}
1) Read the last 14 days of topics: list content/daily/*/package.yaml (topic.title) and avoid repeating a topic or category streak (no more than 2 days in a row of the same category).
2) Merge duplicates. Score each with the rubric in docs/11 (timeliness, save_share, breadth, visual, verifiability 0-5 each; risk 0-5 where higher = riskier; total = sum of the first five minus risk). Hard-exclude red lines and anything without a plausible official source.
3) Pick 1 topic + 2 backups. Choose the style preset (info-warm default for places/events/food, info-night for night/light events, info-clean for 혜택·꿀팁·체크리스트). Keep the strongest evidence URLs (>=2, include the freshest).`,
  { label: 'select', phase: 'Select', schema: SELECT })

phase('Facts')
const FACTS = {
  type: 'object',
  properties: {
    facts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, claim: { type: 'string' }, value: { type: 'string' }, source_url: { type: 'string' },
      source_type: { type: 'string', enum: ['official', 'press', 'blog'] }, checked_at: { type: 'string' },
      status: { type: 'string', enum: ['confirmed', 'planned', 'last_year', 'unverified'] } },
      required: ['id', 'claim', 'value', 'source_url', 'source_type', 'checked_at', 'status'] } },
    items: { type: 'array', description: 'the list entries the card news will cover (e.g., 5 places), each referencing fact ids', items: { type: 'object', properties: { name: { type: 'string' }, fact_ids: { type: 'array', items: { type: 'string' } }, one_liner: { type: 'string' } }, required: ['name', 'fact_ids'] } },
    caveats: { type: 'string' },
  },
  required: ['facts', 'items'],
}
const facts = await agent(`${CTX}
Topic chosen for today: ${JSON.stringify(pick.chosen)}
Build the FACT PACK. For every entry the card news will list (3-6 entries), verify name, dates/period, hours, place/address area, price/fee/conditions, how to apply/book, from the most official source available (주최·기관·브랜드 공식 > 언론 > 블로그). Up to 24 searches.
Status rules: confirmed = official current-year info; planned = officially '예정'; last_year = only last year's info exists (label it); unverified = blog-only. Do not drop inconvenient facts — record them with the right status. checked_at = ${DATE}. Use stable ids f1, f2, ...`,
  { label: 'facts', phase: 'Facts', schema: FACTS })

phase('Produce')
const produced = await agent(`${CTX}
Write today's package. Inputs:
CHOSEN: ${JSON.stringify(pick.chosen)}
BACKUPS: ${JSON.stringify(pick.backups)}
RECENT CHECKED: ${JSON.stringify(pick.recent_topics_checked || [])}
FACT PACK: ${JSON.stringify(facts)}
Steps:
1) python doha.py daily-new ${DATE} --style ${pick.chosen.style}   (if it already exists, edit it instead)
2) Fill content/daily/${DATE}/package.yaml following the template comments and docs/11: topic (title, category, why_now, trend_evidence with source/url/note/seen_at, score), backups, recent_topics_checked, facts (copy the fact pack exactly; no new facts without sources), slides (5-8: cover → items → summary/tip → cta), each slide with headline (<=18 chars per line), sub, info lines (<=24), point (<=40), visual (a concrete photoreal or illustrated scene for ChatGPT; no logos, no readable signage, no real faces/characters), fact_ids. Non-confirmed facts must carry 예정/작년/미정/발표 전 wording on the slide. The cta slide states the info date ("${DATE} 기준, 변경될 수 있어요") and asks to save/share.
   caption: hook line (<=22 chars) → line 2 search keywords → 4-8 short ✔ lines with the key facts (same hedges) → save/share line → final line "이미지는 AI로 생성했어요. 정보는 ${DATE} 기준이에요." hashtags 3-5 (no #). alt_text 1 sentence.
3) python doha.py daily-check ${DATE} → fix until 0 errors (and resolve warnings where sensible).
4) python doha.py daily-md ${DATE}
Korean: natural, friendly 존댓말, short. Return the topic title and slide headlines.`,
  { label: 'produce', phase: 'Produce' })

phase('Review')
const review = await agent(`${CTX}
Adversarial review of content/daily/${DATE}/package.yaml and package.md. Up to 12 searches.
1) Re-verify the 5 most important facts (dates, prices, places, deadlines) against independent searches; fix values/status/hedges in package.yaml if wrong; remove any URL not seen in search results.
2) Copy: hook strength, natural Korean, no exaggeration, no fabricated experience, slide text short enough to render cleanly as image text; headlines must stand alone.
3) Prompts: each slide's visual is concrete and safe (no logos/signage text/real faces/IP characters), consistent with the style preset; the text to render is exact.
4) Re-run python doha.py daily-check ${DATE} and python doha.py daily-md ${DATE}. Set status: ready in package.yaml if 0 errors.
Return a <=120-word summary of fixes.`,
  { label: 'review', phase: 'Review' })

return { date: DATE, topic: pick.chosen.title, backups: (pick.backups || []).map(b => b.title), produced, review }
