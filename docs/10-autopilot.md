# 자동 운영 런북 (오토파일럿)

- 기준일: 2026-10-14 (KST)
- 한 줄 요약: **사람은 하루 1번 채팅에 "승인"이라고 답합니다. 계획·검수·게시·지표 기록은 Claude 루틴 3개가 합니다.** 댓글은 Claude가 초안만 쓰고 사람이 앱에서 직접 답니다.
- 무엇이 바뀌었나: [07-automation.md](07-automation.md)와 README의 "자동 게시 안 함" 원칙은 2026-10-14 사용자 결정으로 **X 원본 글과 (조건을 채운) 인스타그램 이미지 게시물에 한해** "하루 1번 사람 승인 → 정해진 시각에 자동 게시"로 바뀝니다. 댓글·DM·좋아요·팔로우·스크래핑은 여전히 자동화하지 않습니다 ([09-x-playbook.md](09-x-playbook.md) §7).
- 콘텐츠 규칙은 [09-x-playbook.md](09-x-playbook.md), 대기열 파일 형식은 [content/x/README.md](../content/x/README.md)를 따릅니다.

**신뢰도 표시**: [확인] 공식 출처 · [보도] 언론 · [주장] 업체·블로그 · [미확인] 확인 못 함 · (해석) 판단 · (운영 규칙) 우리가 정한 규칙 · (키트 동작) 코드 기준

> **아직 실제 API로 시험하지 않았습니다.** 이 키트를 만든 환경에서는 api.x.com, graph.instagram.com, R2, api.openai.com이 막혀 있어 X·Instagram·R2 호출은 모의 서버와 서명 자체 시험으로만 확인했습니다. 첫 실제 게시는 §3-6 순서대로 사람이 지켜보는 시간에 합니다.

---

## 0. 한눈에 보는 하루

| 시각 (KST) | 누가 | 무엇 |
|---|---|---|
| **20:40** | 계획 루틴 | 내일 X 대기열(글 3개) + 댓글 초안 + 인스타 내일 게시물 준비 → 검수 → 미리보기 → 커밋·푸시 → **채팅으로 승인 요청** |
| 밤~다음 날 08:00 | **사람** | 미리보기를 보고 같은 채팅에 "승인" (일부만, 고쳐 달라, 쉬자도 가능) |
| 승인 직후 | 같은 세션 | `x-approve` (+ 인스타 승인 기록) → 커밋·푸시 |
| 08:12 · 12:12 · 19:12 · 22:12 | 게시 루틴 | `git pull` → `x-publish --due` (+ 인스타 B안이면 `ig-publish`) → 커밋·푸시 → 짧은 보고 |
| 아무 때나 5~10분 | **사람** | 댓글 초안 링크 눌러 직접 게시, 내 글 답글에 답하기, (인스타 A안이면) 앱에서 예약 |
| 월 09:10 | 주간 지표 루틴 | `x-metrics`·`insights`·`metrics` → 주간 보고 → 인증 팔로워 수를 물어봄 |

**승인하지 않으면 아무것도 올라가지 않습니다.** `x-publish`는 `x-approve`가 남긴 지문(approved_hash)이 지금 내용과 같은 글만 올립니다. 승인 뒤 글이나 이미지를 고치면 게시를 거부합니다 (키트 동작).

---

## 1. 운영 스위치

루틴은 매번 `git pull` 뒤 이 표와 `config.yaml`을 읽고 따릅니다. 바꾸고 싶으면 채팅에서 "○○을 바꿔 줘"라고 하면 Claude가 고치고 커밋·푸시합니다.

| 스위치 | 지금 값 | 어디서 바꾸나 | 설명 |
|---|---|---|---|
| X 게시 방식 | `api` | `config.yaml` `x.publish_mode` | `api`: 승인된 글을 시각에 자동 게시 / `manual`: 시각에 앱 링크만 보냄. 고르는 기준은 [09](09-x-playbook.md) §8 |
| X 하루 글 수·시각 | 3개 · 08:10/12:10/19:10/22:10 중 | `config.yaml` `x.posts_per_day`, `x.slots` | 시각을 바꾸면 게시 루틴 cron도 같이 바꿈 (§5-2) |
| 댓글 초안 | 하루 5개, 대상 계정 없음 | `config.yaml` `x.reply_drafts_per_day`, `x.reply_targets` | 대상 계정은 사람이 고름 ([09](09-x-playbook.md) §6) |

아래 세 줄은 루틴이 그대로 읽습니다. 값만 바꾸고 형식은 유지하세요.

```
인스타그램 게시 방식: app
인스타 이미지 자동 생성: off
IG 토큰 마지막 발급·갱신일: 없음
```

- `인스타그램 게시 방식`: `app`(A안, 기본) | `api`(B안). `api`는 §6-2 시험을 통과한 뒤에만 바꿉니다.
- `인스타 이미지 자동 생성`: `off` | `on`. `on`이면 계획 루틴이 사진 없는 인스타 게시물에 `generate`를 실행합니다(게시물당 최대 $1). 얼굴 일관성을 위해 `brand/doha.yaml`의 `face_reference`를 등록하고, OpenAI 설정(§3-1)을 마친 뒤 켭니다.
- `IG 토큰 마지막 발급·갱신일`: `2026-10-20`처럼 날짜만 적습니다(토큰 값은 절대 적지 않음). 주간 루틴이 46일(만료 14일 전, [research/ig-auto-publish.md](research/ig-auto-publish.md) 운영 결론)이 지나면 갱신하라고 알립니다 (§7).

---

## 2. 하루 흐름 자세히

### 2-1. 계획 세션 (매일 20:40)

D는 내일 날짜입니다. 루틴 프롬프트는 §5-1에 있습니다.

1. 저장소 동기화 (브랜치 `claude/instagram-ad-monetization-yzk0vx`).
2. **X 대기열**: `python doha.py x-new D`로 뼈대를 만들고(이미 있으면 덮어쓰지 않음, 키트 동작) 글 3개를 [09](09-x-playbook.md) §3~§5 규칙으로 씁니다.
   - 인스타 일정(D, D+1 게시물)과 주제를 맞추되 캡션을 옮기지 않고 새로 씁니다.
   - 최근 14일 `content/x/*.yaml`을 읽어 주제·문장이 겹치지 않게 합니다. 스레드는 이틀에 1개, A vs B 질문은 주 2회 이하.
   - 이미지가 준비된 인스타 게시물이면 `media`·`alt`를 채우고 `ai_image: true`.
3. **댓글 초안** (대상 계정이 있을 때만): `python doha.py x-targets --date D` → 하루 5개까지 초안, 나머지는 `status: skipped`.
4. **검수**: `python doha.py x-check D`. 오류가 0이 될 때까지 고칩니다. 오류가 있으면 `x-approve`가 승인 자체를 거부합니다 (키트 동작). 도하 이미지(`content/posts/`·`brand/`)에 `ai_image: false`면 `[x.ai]` **오류**라 승인되지 않습니다 (키트 동작, AI 이미지 표시).
5. **인스타 준비** (D와 D+1 게시물):
   - 이미지 자동 생성이 `on`이고 사진이 없으면 `python doha.py generate <게시물> --quality medium --yes --max-cost 1.00`.
   - 사진이 다 있으면 `python doha.py build <게시물>`. 인스타 게시 방식이 `api`면 `python doha.py ig-publish <게시물> --dry-run`까지.
   - 사진이 없으면 "준비 안 됨"으로 보고만 합니다. 자리표시 이미지로는 게시하지 않습니다.
6. **미리보기**: `python doha.py x-digest D` → `out/x/D/digest.html`(휴대폰 카드), `out/x/D/digest.md`(채팅용).
7. **커밋·푸시**: `content/`, `tracking/`만 (`out/`은 git 제외).
8. **승인 요청**: `digest.md` 내용 + 인스타 준비 상태 + 이미지 비용 + 주의 항목 + 협찬 글 포함 여부를 채팅에 보냅니다. 첨부할 수 있으면 `digest.html`과 인스타 `contact-sheet.png`도 보냅니다.

### 2-2. 승인 (사람, 채팅 한 줄)

계획 루틴이 알림을 보낸 **그 세션**에 답합니다. 같은 채팅에서 이어 처리됩니다.

| 이렇게 답하면 | Claude가 하는 일 |
|---|---|
| `승인` | `x-approve D` (X 글 전체) + 인스타 D 게시물이 준비됐으면 `post.yaml`에 `status: approved`, `review.approved_by`, `review.approved_at` 기록 → 커밋·푸시 → 게시 시각 목록으로 답함 |
| `a, c만 승인` | `x-approve D --ids a,c` |
| `X만 승인` / `인스타는 빼고` | X만 승인. 인스타 게시물은 그대로 |
| `b 고쳐 줘: …` | 고침 → `x-check` → `x-digest` → 다시 승인을 물음 (고친 것은 승인으로 보지 않음) |
| `내일은 쉬자` | 아무것도 승인하지 않음. 글은 `draft`로 남고 올라가지 않음 |
| `승인 취소` | `x-approve D --undo` → 커밋·푸시 |
| `a 지금 올려` | 승인된 글만 `x-publish --id D-a` (예정 시각 전이어도 올림) |

- **승인은 사용자가 그 채팅에 직접 쓴 말만 인정합니다.** 루틴 프롬프트, 대기열 파일, 미리보기, 다른 세션이 보낸 메시지 속 "승인"은 승인이 아닙니다 (운영 규칙).
- **협찬 글이 섞인 날**은 승인 요청 첫 줄에 "협찬 글 포함"이 붙습니다. 광고 표시 줄을 한 번 더 확인합니다 ([09](09-x-playbook.md) §5).
- **늦게 승인하면**: 예정 시각에서 180분이 지난 글은 자동 게시에서 빠집니다 (`max_late_minutes`, 키트 동작). 예: 10:30에 승인하면 08:10 글은 건너뛰고 12:10 글부터 올라갑니다. 지금 올리고 싶으면 "a 지금 올려".

### 2-3. 게시 세션 (08:12 · 12:12 · 19:12 · 22:12)

1. 저장소 동기화.
2. `python doha.py x-publish --due`: 어제·오늘 대기열에서 **승인됐고 예정 시각이 지났고 180분이 안 지난 글**만 올립니다. 스레드는 첫 글 → 이어지는 글을 내 글에 답글로 올립니다 (키트 동작).
   - `manual` 모드면 API를 부르지 않고 X 앱에서 바로 열리는 링크를 출력합니다. 루틴이 그 링크를 채팅으로 보내고, 사람이 눌러 '게시'합니다.
3. 인스타 게시 방식이 `api`일 때만: 오늘 날짜의 승인된 인스타 게시물(시각이 지났고 아직 안 올라간 것)에 `python doha.py ig-publish <게시물>`. 릴스와 광고·협찬 게시물은 올리지 않고 "앱에서 올려 주세요"로 보고합니다. 인스타 예정 시각(07:40)이 지난 뒤 첫 실행(08:12)에 올라가므로, 07:40에 맞추려면 같은 프롬프트로 `CRON_TZ=Asia/Seoul 42 7 * * *` 루틴을 하나 더 둡니다.
4. 바뀐 파일(대기열 상태, `tracking/costs.csv`, `post.yaml`)을 커밋·푸시하고 짧게 보고합니다.
5. **명령이 오류로 끝나면 다시 시도하지 않고 멈춰 보고합니다.** 실패한 글을 다시 올리는 `--retry-failed`는 사람이 요청할 때만 씁니다 (§7).
   - 단, 멈추기 전에 **바뀐 대기열 파일은 꼭 커밋·푸시합니다.** 실패해도 `x-publish`는 올라간 글 id(`x_ids`), 응답이 끊긴 표시(`inflight`), `failed` 상태를 파일에 남깁니다. 루틴은 매번 새 세션이라 이 기록을 푸시하지 않으면 사라지고, 다음 세션이 같은 글을 다시 올리려 할 수 있습니다 (키트 동작).

cron 분을 :12로 둔 이유 (해석): 세션이 예정 시각보다 일찍 시작되면 그 글은 "예정"으로 남고, 다음 실행은 3~7시간 뒤라(19:12 → 22:12도 예정 19:10에서 182분) 180분 한도를 넘어 건너뜁니다. 2분 늦게 돌려 이 일을 막습니다.

### 2-4. 사람이 따로 하는 일 (하루 5~10분)

- **댓글**: `digest.html`(또는 채팅의 digest)에서 'X 앱에서 답글 열기'를 누르면 초안이 채워진 답글 창이 열립니다. 읽고 고친 뒤 직접 '게시' → 채팅에 "댓글 3개 달았어"라고 하면 Claude가 `status: done`으로 적습니다.
- **내 글에 달린 답글**과 나를 멘션한 글에는 사람이 직접 답합니다.
- **인스타 A안**: 승인한 게시물을 Instagram 앱에서 올리고 'AI 정보' 라벨, (협찬이면) 유료 파트너십 라벨을 켠 뒤 '이 게시물 예약'으로 예약합니다(1건 2~3분) ([research/ig-auto-publish.md](research/ig-auto-publish.md) §3, §5-2). 올린 뒤 게시물 주소를 채팅에 보내면 Claude가 `posted.url`을 적습니다.
  - 렌더링한 파일(`out/`)은 git에 올라가지 않습니다. 계획 세션이 채팅에 슬라이드·`caption.txt`를 첨부하지 못했다면, 내 PC에서 `git pull` → `python doha.py build <게시물>` → `out/` 폴더의 파일을 휴대폰으로 옮깁니다.
- **월 1편 Article**과 고정 글은 사람이 앱·웹에서 직접 올립니다 ([09](09-x-playbook.md) §3).

### 2-5. 주간 (월요일 09:10)

`x-metrics`로 X 지표·팔로워·OCR 거리를, `insights --followers`로 인스타 지표를, `metrics`로 월 리포트를 갱신하고 15줄 안팎으로 보고합니다. 인증 팔로워 수는 API로 받을 수 없어(키트 동작) 루틴이 채팅으로 물어봅니다. 숫자를 답하면 `tracking/x-followers.csv`에 적습니다. 보는 법은 [09](09-x-playbook.md) §9.

---

## 3. 처음 한 번: 설정 체크리스트 (사람)

### 3-1. 계정

- [ ] **X 계정** 만들기와 프로필 세팅: [09](09-x-playbook.md) §2 (2단계 인증, 이메일 인증, 소개글 AI 고지, 프로필 링크, 고정 글). 아이디를 `config.yaml` `x.handle`에 적습니다(채팅으로 알려 주면 Claude가 적음).
- [ ] **X Premium 결정**: 처음에는 없어도 됩니다. 켜는 시점은 [09](09-x-playbook.md) §1-4.
- [ ] **운영자 개인 X 계정**: 'Automated' 라벨을 켤 때 연결할 사람 계정입니다 ([09](09-x-playbook.md) §8-3).
- [ ] **X 개발자 계정** (사용량 과금)
  - 신규 개발자에게 무료 요금제와 Basic·Pro 월정액은 없고, 선불 크레딧으로 쓰는 만큼 낸다는 정리가 있습니다 [주장]. 글 1건 $0.015, 링크 포함 글 $0.20 [확인] ([research/x-automation-api.md](research/x-automation-api.md) §3-1).
  - 개발자 포털에서 프로젝트·앱을 만들고 앱 권한을 **Read and write**로 둔 뒤, **도하 계정으로 로그인한 상태에서** Consumer Key·Secret과 Access Token·Secret을 발급합니다 (키트는 OAuth 1.0a 사용자 인증을 씀, 키트 동작). 권한을 바꾼 뒤에는 Access Token을 다시 발급해야 새 권한이 붙습니다.
  - 크레딧은 처음에 소액만 넣습니다(최소 충전액은 포털에서 확인 [미확인]). 자동 충전이 있으면 끕니다. 크레딧이 떨어지면 게시 요청이 거부될 뿐 다른 일은 생기지 않습니다. 이때 응답 코드는 402로 예상하지만 조사 문서로 확인하지 못했습니다 [미확인] (§7).
- [ ] **Instagram** (인스타 지표 API나 B안을 쓸 때)
  - 크리에이터(프로페셔널) 계정 전환, 'AI 생성 프로필' 라벨 켜기: [06-account-setup.md](06-account-setup.md).
  - Meta 개발자 앱 → 'Instagram API with Instagram Login'. 권한은 `instagram_business_basic` + `instagram_business_content_publish` [확인]. 내 계정에만 쓰면 Standard Access로 충분하고 앱 리뷰가 필요 없습니다 [확인] ([research/ig-auto-publish.md](research/ig-auto-publish.md) §1-1).
  - 앱 대시보드에서 도하 계정의 **장기 토큰(60일)**을 받습니다 [확인] (ig-auto-publish.md §1-7). 받은 날짜를 §1의 'IG 토큰 마지막 발급·갱신일'에 적습니다.
  - Facebook 페이지는 필요 없습니다 (Instagram 로그인 방식).
- [ ] **Cloudflare R2** (B안에서만)
  - 버킷 1개, **내 도메인을 연결한 공개 주소**(예: `https://media.내도메인`). `r2.dev` 주소는 첫 시험에만 씁니다 [확인] ([research/ig-auto-publish.md](research/ig-auto-publish.md) §2).
  - R2 API 토큰은 **그 버킷 하나에 Object Read & Write 권한만** 줍니다 (doha/r2.py 설명).
  - 키트가 게시 직전에 JPEG를 올리고, 게시가 끝나면 지웁니다 (키트 동작).
- [ ] **OpenAI API** (이미지 자동 생성을 켤 때만)
  - 조직 인증(신분증·얼굴, Persona)을 사용자가 직접 한 번 합니다 [주장]. 실패하면 되돌리기 어려우니 이름·계정 정보를 맞춘 뒤 진행합니다 ([research/ig-auto-publish.md](research/ig-auto-publish.md) §4-1).
  - 선불 **$10**만 넣고 **자동 충전은 끕니다**. 자동 충전은 설정할 때 기본으로 켜져 있고, 크레딧은 1년 뒤 만료됩니다 [확인] (ig-auto-publish.md §4-2).

### 3-2. 환경 변수 (비밀값)

**어디에 넣나**: 클라우드 세션 제목 줄의 클라우드 환경 메뉴 → **Edit** → **Network secrets**(업데이트 전 앱에서는 'API credentials')가 있으면 거기에, 없으면 환경 변수로 넣습니다. 새로 시작하는 세션부터 적용됩니다. 내 PC에서 돌릴 때는 저장소의 `.env`에 넣습니다(git 제외).

**키·토큰을 채팅에 붙여넣지 마세요.** Claude도 값을 출력하거나 파일·커밋에 넣지 않습니다. 키트는 토큰 지문(앞 4자…뒤 4자)만 보여 줍니다 (키트 동작).

| 이름 | 무엇 | 쓰는 명령 | 언제 필요 |
|---|---|---|---|
| `X_API_KEY` | X 앱 Consumer Key | `x-publish`, `x-metrics`, `x-targets` | X 시작부터 |
| `X_API_SECRET` | X 앱 Consumer Secret | 〃 | 〃 |
| `X_ACCESS_TOKEN` | 도하 계정 Access Token (Read and write) | 〃 | 〃 |
| `X_ACCESS_TOKEN_SECRET` | 도하 계정 Access Token Secret | 〃 | 〃 |
| `IG_ACCESS_TOKEN` | Instagram 장기 토큰 (60일) | `ig-publish`, `insights` | 인스타 지표 또는 B안 |
| `IG_USER_ID` | Instagram 사용자 ID (선택, 비우면 자동 조회) | `ig-publish` | 선택 |
| `R2_ACCOUNT_ID` | Cloudflare 계정 ID | `ig-publish` | B안 |
| `R2_ACCESS_KEY_ID` | R2 API 토큰의 Access Key ID | 〃 | 〃 |
| `R2_SECRET_ACCESS_KEY` | R2 API 토큰의 Secret | 〃 | 〃 |
| `R2_BUCKET` | 버킷 이름 | 〃 | 〃 |
| `R2_PUBLIC_BASE_URL` | 버킷 공개 주소 (예: `https://media.내도메인`) | 〃 | 〃 |
| `OPENAI_API_KEY` | OpenAI API 키 | `generate` | 이미지 자동 생성 |

`DOHA_MAX_COST_USD`(이미지 생성 1회 상한, 기본 1.00)는 비밀값이 아니라 선택 설정입니다.

### 3-3. 네트워크 허용 도메인

**어디서 바꾸나**: 같은 클라우드 환경 메뉴 → **Edit** → **Network access**. 'Limited' 수준에서 **Allowed domains**에 아래 도메인을 추가하고 **Allow package managers** 체크는 그대로 둡니다. 업데이트 전 앱에서는 'Custom' 아래에 있고, 기본 패키지 관리자 목록을 포함하는 체크 칸이 있습니다. 자세한 단계: https://code.claude.com/docs/en/cloud-environments#network-access

| 도메인 | 쓰는 기능 | 필요할 때 |
|---|---|---|
| `api.x.com` | X 게시·지표·댓글 후보 (`x-publish`, `x-metrics`, `x-targets`) | **X 시작부터** |
| `graph.instagram.com` | 인스타 게시·지표·토큰 갱신 (`ig-publish`, `insights`) | 인스타 지표 API 또는 B안 |
| `<R2_ACCOUNT_ID>.r2.cloudflarestorage.com` | R2 업로드·삭제 (`ig-publish`) | B안 |
| R2 공개 도메인 (`R2_PUBLIC_BASE_URL`의 호스트, 예: `media.내도메인`) | 게시 전 공개 주소 확인 (`ig-publish`가 HEAD/GET으로 200·`image/jpeg` 확인) | B안 |
| `api.openai.com` | 이미지 생성 (`generate`) | 이미지 자동 생성 |
| `graph.facebook.com` | **지금 키트는 쓰지 않음** | Facebook 로그인 방식으로 바꿀 때만 |
| `rupload.facebook.com` | **지금 키트는 쓰지 않음** (Facebook 로그인 방식의 릴스 재개형 업로드) | 〃 |

GitHub 커밋·푸시는 세션의 git 연결로 따로 처리됩니다.

### 3-4. 설정 스크립트

같은 메뉴 → **Edit** → **Setup script**에 넣으면 새 세션마다 실행됩니다.

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium   # build·render·ig-publish(4:5 렌더)·x-digest --png 용
```

- Chromium 내려받기가 막혀 실패하면 오류에 나온 호스트를 허용 도메인에 더합니다.
- 릴스(`reel`)에는 ffmpeg가 필요합니다. 없으면 계획 세션은 `build --skip-reel`로 돌리고, 릴스는 앱에서 올립니다.
- X 대기열 명령 중 `x-new`·`x-check`·`x-approve`·`x-publish`·`x-metrics`·`x-targets`는 pyyaml만 있으면 됩니다. `x-digest`는 jinja2도 필요합니다(requirements.txt에 있음).

### 3-5. 루틴 3개 만들기

이 채팅에서 **"docs/10 §5의 루틴 3개를 만들어 줘"**라고 하면 Claude가 아래 설정으로 만듭니다.

| 루틴 | cron (KST) | 실행 방식 | 알림 |
|---|---|---|---|
| (a) 계획 | `CRON_TZ=Asia/Seoul 40 20 * * *` | 실행할 때마다 새 세션 | 휴대폰 알림 켬 (승인 요청) |
| (b) 게시 | `CRON_TZ=Asia/Seoul 12 8,12,19,22 * * *` | 실행할 때마다 새 세션 | 켬 (실패·manual 링크) |
| (c) 주간 지표 | `CRON_TZ=Asia/Seoul 10 9 * * 1` | 실행할 때마다 새 세션 | 켬 |

- 새 세션 방식이라 지난 실행의 대화에 끌려가지 않고, 매번 저장소에서 상태를 다시 읽습니다. 승인은 계획 루틴 알림이 연 세션에 답합니다.
- `x.slots`를 바꾸면 (b)의 시각도 같이 바꿉니다 (분은 슬롯 + 2분).

### 3-6. 첫 주 시험 순서

1. 서명 자체 시험 (네트워크 없이 됨): `python -m doha.xapi`, `python -m doha.r2 --self-test`.
2. 연결 확인
   - X: `python doha.py x-metrics --dry-run` — X 키 4개로 내 계정(`GET /2/users/me`)을 읽어 아이디·팔로워 수만 보여 줍니다. CSV에 쓰지 않고, 비용은 읽기 1건(약 $0.001 [주장]).
   - Instagram·R2 (지표 API나 B안을 쓸 때): `python doha.py ig-publish --check-setup` (환경 변수가 있는지(값은 안 보임), SigV4 서명 자체 시험, API 연결). X 키는 이 명령이 보지 않습니다.
3. **X 첫 글**: 계획 루틴이 만든 대기열을 승인한 뒤, 첫 글은 사람이 보는 시간에 `python doha.py x-publish --id D-a --dry-run` → `--dry-run`을 빼고 실행 → X 앱에서 글을 확인하고 'Automated' 라벨([09](09-x-playbook.md) §8-3)을 켭니다.
4. **첫 스레드**: 이어지는 글이 내 글 답글로 붙는지 확인합니다. API의 답글 제한에 자기 스레드가 걸리는지는 [미확인]입니다 ([09](09-x-playbook.md) §10). 거부되면 §7대로 처리합니다.
5. **첫 이미지 글**: 업로드·대체 텍스트·본문 끝 `AI 이미지` 표기를 앱에서 확인합니다.
6. 인스타 B안은 §6-2 시험을 따로 합니다.

---

## 4. 매달 드는 돈 (추정)

환율은 `config.yaml` `fx.usd_krw`(1,400원)로 계산했습니다.

| 항목 | 월 추정 | 계산 · 근거 |
|---|---|---|
| X API 게시 | 약 $2.3 | 하루 글 3개 + 이틀에 1번 스레드(이어지는 글 4개) ≈ 하루 5건 × 30일 × $0.015 [확인] (x-automation-api.md §3-1) |
| X API 읽기 | 약 $2.5 | `x-targets` 하루 최대 15건 × $0.005 [주장] ≈ $2.3 + `x-metrics` 주 1회 내 글 읽기 $0.001/건 [주장] |
| 링크 포함 글 | $0 | 본문 링크를 쓰지 않음. 쓰면 1건 $0.20 [확인] |
| X Premium | $0 ~ 약 $8 | 처음엔 0. Premium 월 $8 [주장], Basic 월 $3 [확인]은 OCR 자격 아님 [보도] ([09](09-x-playbook.md) §1-4) |
| OpenAI 이미지 | $0 (자동 생성 off) / 약 $4~8 (on) | 인스타 월 17개 안팎 × 5장 × medium 장당 약 $0.04~0.05 [보도]·`config.yaml` 추정 + 다시 만들기. 얼굴 기준 이미지 입력 토큰은 별도. high 확정 컷은 장당 약 $0.17 (`est_cost_usd`) |
| Cloudflare R2 | 거의 0 | 게시 후 바로 지워 저장량이 작음. 무료 구간·요금은 [미확인] (ig-auto-publish.md §2). 내 도메인 등록비는 별도 [미확인] |
| Instagram API | 조사 문서에 요금 언급 없음 | 확인 필요 |
| Claude 루틴 | 요금제 사용량에서 차감 | 하루 5회(계획 1 + 게시 4) + 주 1회 ≈ 월 155회 실행. 금액은 요금제에 따라 다름 [미확인]. 게시 루틴은 짧게 끝나도록 프롬프트를 짧게 둠 |
| **합계 (Claude·도메인 제외)** | **약 $5~13 (7천~1만 8천 원)**, Premium을 켜면 +$8 | 실제 지출은 `tracking/costs.csv`(category=x_api, 이미지 생성)에 남음 (키트 동작) |

---

## 5. 루틴 프롬프트 (그대로 붙여넣기)

세 프롬프트 모두 매번 새 세션에서 시작하는 것을 전제로 씁니다.

### 5-1. (a) 계획 루틴 — `CRON_TZ=Asia/Seoul 40 20 * * *`

```text
당신은 도하(@doha.dailyfit) 운영 키트의 '계획 세션'입니다. 저장소 insta_master에서 일합니다.
규칙은 docs/09-x-playbook.md, 절차는 docs/10-autopilot.md §1·§2-1·§2-2를 따릅니다. 모든 보고는 한국어로 짧게.

0) git fetch origin && git checkout claude/instagram-ad-monetization-yzk0vx && git pull --ff-only origin claude/instagram-ad-monetization-yzk0vx
   D = 내일 날짜(KST): TZ=Asia/Seoul date -d tomorrow +%F 로 구합니다 (서버 시계는 UTC일 수 있음).
   docs/10 §1 운영 스위치와 config.yaml 의 x: 항목을 읽습니다.
1) X 대기열: python doha.py x-new D (이미 있으면 덮어쓰지 않으니 내용을 검토해 이어서 씁니다).
   config.x.posts_per_day 개 글을 docs/09 §3~§5 대로 씁니다. 도하 말투(brand/doha.yaml), 글마다 X 가중 글자 수 280 이하,
   링크·@멘션 없음, 해시태그 0~1개, 참여 유도·체험 표현 없음. content/posts/ 의 D, D+1 인스타 게시물과 주제를 맞추되
   캡션을 옮기지 말고 새로 씁니다. 최근 14일 content/x/*.yaml 과 주제·문장이 겹치지 않게, 스레드는 이틀에 1개,
   A vs B 질문은 주 2회 이하. 이미지가 있는 인스타 게시물이면 media·alt 를 채우고 ai_image: true.
   광고·협찬 글은 사용자가 채팅으로 미리 지시한 경우에만 넣습니다.
2) config.x.reply_targets 가 비어 있지 않으면: python doha.py x-targets --date D → 후보 중
   config.x.reply_drafts_per_day 개까지 draft 를 docs/09 §6 대로 쓰고 나머지는 status: skipped.
3) python doha.py x-check D → 오류가 0이 될 때까지 고칩니다. [x.ai](도하 이미지인데 ai_image: false)는 오류이므로 ai_image: true 로 고칩니다.
4) 인스타 D, D+1 게시물(content/posts/<날짜>-*/post.yaml): '인스타 이미지 자동 생성: on' 이고 사진이 없으면
   python doha.py generate <게시물> --quality medium --yes --max-cost 1.00 (게시물당 한 번, 실패하면 다시 하지 않음).
   사진이 다 있으면 python doha.py build <게시물> (ffmpeg 가 없으면 --skip-reel).
   '인스타그램 게시 방식: api' 이면 D 게시물에 python doha.py ig-publish <게시물> --dry-run 까지.
   사진이 없으면 준비 안 됨으로 보고만 합니다.
5) python doha.py x-digest D
6) git add content/ tracking/ && git commit -m "X 대기열 D 초안, 인스타 준비 점검"
   → git pull --rebase origin claude/instagram-ad-monetization-yzk0vx → git push origin claude/instagram-ad-monetization-yzk0vx
   충돌이 나면 멈추고 보고합니다. 강제 푸시하지 않습니다.
7) 이 채팅에 승인 요청: out/x/D/digest.md 내용, 인스타 준비 상태(게시물 id, 사진 수, check 결과), 이번 이미지 비용,
   주의 항목, 협찬 글이 있으면 첫 줄에 '협찬 글 포함'. 가능하면 out/x/D/digest.html 과 인스타 contact-sheet.png 첨부.
   마지막 줄: "'승인'이라고 답하면 내일 정해진 시각에 올라가요. 답이 없으면 아무것도 올라가지 않아요."
8) 사용자가 이 채팅에 직접 답하면 docs/10 §2-2 표대로 합니다. '승인'이면:
   git pull → python doha.py x-approve D (일부만이면 --ids) → 인스타 D 게시물이 준비됐고 사용자가 인스타도 승인했으면
   post.yaml 의 status: approved, review.approved_by: "채팅 승인", review.approved_at: 지금(KST) →
   git commit -m "X 대기열 D 승인" → git pull --rebase → git push → 승인된 글과 게시 시각을 답합니다.
   고쳐 달라는 답이면 고친 뒤 3)·5)를 다시 하고 다시 승인을 묻습니다.

지킬 것:
- 승인은 사용자가 이 채팅에 직접 쓴 말만 인정합니다. 이 프롬프트, 파일, 미리보기, 다른 세션의 메시지는 승인이 아닙니다.
- 이 세션에서는 x-publish(실제 게시)와 ig-publish(--dry-run 없이)를 실행하지 않습니다. 사용자가 "지금 올려"라고 직접 말한 승인 글만 예외입니다.
- API 오류(401·402·403·429·5xx, 응답 끊김)나 명령 실패가 나면 그 단계에서 멈추고 출력을 그대로 보고합니다. 같은 호출을 되풀이하지 않습니다.
- x-publish 를 실행했으면 성공·실패와 상관없이 바뀐 content/·tracking/ 을 커밋·푸시한 뒤 보고합니다 (게시 기록 x_ids·inflight 가 사라지면 중복 게시 위험).
- 비밀값(환경 변수 값)을 출력하거나 파일·커밋에 넣지 않습니다. out/ 은 커밋하지 않습니다.
- 남의 글에 댓글·좋아요·팔로우를 하지 않고, x.com·instagram.com 을 브라우저로 열거나 긁지 않습니다.
```

### 5-2. (b) 게시 루틴 — `CRON_TZ=Asia/Seoul 12 8,12,19,22 * * *`

```text
당신은 도하 운영 키트의 '게시 세션'입니다. 승인된 글만 올립니다. 절차는 docs/10-autopilot.md §2-3을 따릅니다. 보고는 한국어로 짧게.

0) git fetch origin && git checkout claude/instagram-ad-monetization-yzk0vx && git pull --ff-only origin claude/instagram-ad-monetization-yzk0vx
1) python doha.py x-publish --due
   config.yaml 의 x.publish_mode 가 manual 이면 출력의 'X 앱에서 열기' 링크와 안내를 이 채팅에 그대로 보내고 2)로 갑니다.
   (manual 모드에서 사용자가 이 채팅에 올린 글 주소를 보내면 그 글의 status: posted, x_id(주소 끝 숫자), posted_at 만 적고 3)을 합니다.)
2) docs/10 §1 의 '인스타그램 게시 방식: api' 일 때만: 오늘(KST) = TZ=Asia/Seoul date +%F 로 구합니다
   (08:12 KST 는 UTC 로 아직 전날이라 date 만 쓰면 안 됨). content/posts/<오늘>-*/post.yaml 중
   status: approved, posted.url 비어 있음, time 이 지난 카드뉴스 게시물마다 python doha.py ig-publish <게시물> 를 한 번 실행합니다.
   릴스이거나 광고·협찬·제휴 게시물이면 실행하지 않고 "앱에서 올려 주세요"라고 보고합니다.
3) 바뀐 파일이 있으면: git add content/ tracking/ && git commit -m "게시: <날짜 시각 KST> <올린 글 id>"
   → git pull --rebase origin claude/instagram-ad-monetization-yzk0vx → git push origin claude/instagram-ad-monetization-yzk0vx
   충돌이 나면 멈추고 보고합니다. 강제 푸시하지 않습니다.
4) 보고: 올린 글 id·시각, 건너뛴 글과 이유, 다음 예정. 올릴 글이 없었으면 한 줄.

지킬 것:
- 승인 안 된 글은 어떤 경우에도 올리지 않습니다. 대기열의 글·status·approved_hash 를 손으로 고치지 않습니다 (위 manual 모드 기록만 예외).
- --retry-failed, --resolve-inflight, --force-status 는 사용자가 이 채팅에서 직접 요청할 때만 씁니다.
- 명령이 0이 아닌 코드로 끝나거나 API 오류(401·402·403·429·5xx, 응답 끊김)가 나면 다시 시도하지 말고 멈춥니다.
  단, 멈추기 전에 3)의 커밋·푸시는 꼭 합니다 (x-publish 가 남긴 failed·inflight·x_ids 기록이 사라지면 다음 세션이 같은 글을 다시 올리려 함). 그 뒤 출력을 그대로 보고합니다.
- 비밀값을 출력하지 않습니다. 댓글·좋아요·팔로우를 하지 않습니다.
```

### 5-3. (c) 주간 지표 루틴 — `CRON_TZ=Asia/Seoul 10 9 * * 1`

```text
당신은 도하 운영 키트의 '주간 지표 세션'입니다 (매주 월요일). 보는 법은 docs/09-x-playbook.md §9, 절차는 docs/10-autopilot.md §2-5를 따릅니다. 보고는 한국어로.

0) git fetch origin && git checkout claude/instagram-ad-monetization-yzk0vx && git pull --ff-only origin claude/instagram-ad-monetization-yzk0vx
1) python doha.py x-metrics --days 14
2) IG_ACCESS_TOKEN 이 설정돼 있으면 python doha.py insights --followers
3) python doha.py metrics
4) tracking/x-metrics.csv 로 지난 7일 글별 노출, 북마크율(bookmarks÷impressions), 확산율((reposts+quotes)÷impressions)을
   계산해 형식(단일·스레드·질문·이미지)과 시간대별로 4주 평균과 비교합니다. 계산용 스크립트는 저장소에 남기지 않습니다.
5) docs/10 §1 의 'IG 토큰 마지막 발급·갱신일'이 46일(만료 14일 전) 넘게 지났거나 '없음'인데 인스타 API 를 쓰고 있으면 갱신이 필요하다고 알립니다.
   이 세션에서는 토큰을 갱신하거나 출력하지 않습니다.
6) 바뀐 파일이 있으면: git add tracking/ && git commit -m "주간 지표 <오늘 날짜>"
   → git pull --rebase origin claude/instagram-ad-monetization-yzk0vx → git push origin claude/instagram-ad-monetization-yzk0vx
   충돌이 나면 멈추고 보고합니다.
7) 보고 (15줄 안팎): 팔로워 증감, OCR 거리(인증 팔로워 n/500, 90일 노출 상한 n/500,000), 잘된 글 2개와 이유,
   다음 주에 바꿀 것 1~2개, 이번 달 X API·이미지 비용 합계(tracking/costs.csv).
   끝에 "X 앱에서 인증 팔로워 수를 확인해 알려 주세요"라고 묻고, 사용자가 숫자를 답하면 tracking/x-followers.csv 의
   오늘 날짜(KST, TZ=Asia/Seoul date +%F) 줄 verified_followers 칸에 적고(줄이 없으면 추가) 커밋·푸시합니다.

지킬 것: 글을 쓰거나 승인·게시하지 않습니다. API 오류가 나면 멈추고 보고합니다. 비밀값을 출력하지 않습니다.
```

---

## 6. 인스타그램: A안(기본)과 B안

근거: [research/ig-auto-publish.md](research/ig-auto-publish.md) §5-2와 운영 결론. 이 조사는 **A안을 기본으로, B안은 AI 라벨 문제를 시험으로 해결한 뒤 협찬이 아닌 이미지 게시물에만** 쓰라고 권합니다 (해석).

### 6-1. A안: 서버가 준비, 사람이 앱에서 예약 (지금)

- 계획 루틴이 이미지 생성(켠 경우)·`build`(검수 → 렌더 → 릴스 → 미리보기)까지 하고, 사람은 하루 1번 승인과 함께 미리보기를 봅니다.
- 승인한 게시물은 사람이 Instagram 앱에서 올리며 'AI 정보' 라벨, (협찬이면) 유료 파트너십 라벨을 켜고 '이 게시물 예약'(최대 75일 [보도])으로 예약합니다. 1건 2~3분입니다.
- 이유: 공식 게시 API에서 게시물 'AI 정보' 라벨을 켜는 파라미터를 찾지 못했습니다 [미확인]. 라벨 없는 AI 계정의 도달이 줄 수 있다는 글도 있습니다 [주장] (ig-auto-publish.md §1-6, §5-1).

### 6-2. B안: 승인하면 API로 게시 (조건부)

조건 (모두 만족해야 `인스타그램 게시 방식: api`로 바꿈):

- [ ] 협찬·광고·제휴가 아닌 **카드뉴스(이미지)** 게시물만. 릴스와 협찬 게시물은 계속 앱에서.
- [ ] 4:5(1080×1350) sRGB JPEG, 8MB 이하, 10장 이하 — `ig-publish`가 자동으로 맞춤 (키트 동작). 지금 피드 규격 3:4(1080×1440)는 API 규격 밖입니다 [확인] (ig-auto-publish.md §1-3).
- [ ] **AI 라벨 시험 통과**: 시험 게시물 1건을 `ig-publish`로 올린 뒤, 앱에서 'AI 정보' 라벨이 자동으로 붙었는지(키트가 JPEG에 IPTC AI 합성 메타데이터를 넣음, 효과는 [미확인]) 또는 앱의 '수정' 화면에서 라벨을 나중에 켤 수 있는지 확인합니다 [미확인]. 둘 다 안 되면 A안을 유지합니다.
- [ ] R2 내 도메인 공개 주소, 허용 도메인(§3-3), `ig-publish --check-setup` 통과.

시험 순서:

1. `python doha.py ig-publish <게시물> --dry-run` — 4:5 렌더·JPEG 변환·검사만.
2. `python doha.py ig-publish <게시물> --mock` — 내장 모의 서버로 전체 흐름 리허설 (`post.yaml`은 그대로).
3. 사람이 보는 시간에 `post.yaml`을 `status: approved`로 둔 시험 게시물 1건을 실제로 올림 → 앱에서 라벨·캡션 첫 줄·이미지 비율 확인.
4. 통과하면 §1의 `인스타그램 게시 방식`을 `api`로 바꾸고 커밋·푸시. 다음 게시 루틴부터 적용됩니다.

안전장치 (키트 동작): `status: approved`가 아니면 게시 거부, 검수 오류·자리표시 사진이면 거부, 이미 `posted.url`이 있거나 최근 게시물에 같은 캡션이 있으면 다시 올리지 않음, 광고·협찬·제휴 게시물은 `--paid-partnership` 없이는 거부.

---

## 7. 문제가 생겼을 때

원칙: **루틴은 오류가 나면 다시 시도하지 않고 멈춰 보고합니다.** 사람이 원인을 보고 "다시 해 줘"라고 할 때만 다시 시도합니다.

| 상황 | 키트가 자동으로 하는 일 | 사람이 할 일 |
|---|---|---|
| **승인하지 않음** | 아무것도 안 올라감 (글은 `draft`) | 없음. 늦게 승인하면 예정+180분이 지난 글은 건너뜀 → "a 지금 올려" |
| **X 401** (토큰 무효: 다시 발급했거나 권한·앱 상태가 바뀜) | 그 실행의 나머지 글도 멈춤. 글은 `failed` | 개발자 포털에서 토큰을 다시 발급 → 환경 변수 교체(§3-2) → 새 세션에서 "실패한 글 다시 올려" (`x-publish --due --retry-failed`, 최대 3번). 예정 시각에서 180분이 지난 글은 `--due`가 건너뛰므로 `x-publish --id <글 id>`로 올림 |
| **X 402** (크레딧 소진으로 예상 [미확인]) | 멈춤 | 크레딧 충전 → "실패한 글 다시 올려" |
| **X 429** (한도 초과) | 멈춤. 하루 3~10건은 한도와 거리가 멂 [주장] | 한 시간쯤 뒤 "다시 올려" |
| **X 403 중복** (같은 글 반복) | `failed` | 글을 고치고 `x-check` → 다시 승인 |
| **스레드 중간에 실패** (예: 자기 스레드 답글이 거부됨) | 올라간 글 id를 `x_ids`에 남김. 다시 시도하면 끊긴 곳부터 이어 씀 | "이어서 올려"(`x-publish --id <글 id> --retry-failed`, 끊긴 곳부터 이어 씀). X 앱에서 나머지를 직접 이어 붙였다면 다시 올리지 않도록 채팅으로 알려 주세요 — Claude가 대기열 파일의 그 글 `status`를 `skipped`로 바꿔 커밋합니다(전용 명령 없음, 이 경우만 손으로 수정). 계속 거부되면 스레드를 단일 글 위주로 바꿈 |
| **응답이 끊김** (시간 초과, 연결 끊김) | 올라갔는지 몰라 `inflight`를 남기고 **다시 올리지 않음** (중복 게시 방지) | X 앱 프로필에서 확인 → 올라갔으면 `x-publish --id <글 id> --resolve-inflight <글 주소나 id>`, 아니면 `--resolve-inflight none` (채팅으로 알려 주면 Claude가 실행) |
| **승인 뒤 글을 고침** | 지문이 달라 게시 거부 | `x-check` → `x-digest` → 다시 승인 |
| **Instagram 토큰 만료** (60일) | `ig-publish`·`insights` 실패 | 만료 전: 내 PC에서 `python doha.py ig-publish --refresh-token` → 새 값이 생기면 `IG_ACCESS_TOKEN` 환경 변수 교체 → 생긴 파일 삭제 → §1 날짜 갱신. 이미 만료됐으면 앱 대시보드에서 새로 발급 [확인] (ig-auto-publish.md §1-7) |
| **Instagram 이미지 못 가져감** (오류 코드 9004·2207052) | 게시 안 됨, R2 파일 정리 | R2 공개 도메인, 허용 도메인(§3-3) 확인 [확인] (ig-auto-publish.md §1-2) |
| **응답 끊긴 Instagram 게시** | 다음 실행에서 최근 게시물부터 확인하고 기록만 함 (키트 동작) | 앱에서 중복 여부 확인 |
| **OpenAI 403 (조직 인증)·잔액 부족** | `generate` 실패, 게시물은 "준비 안 됨" | 조직 인증·충전 (자동 충전은 끈 채로) |
| **이미지 생성 시간 초과** | 자동 재시도 안 함 (이중 과금 방지, 키트 동작) | 결과 확인 후 다시 실행 요청 |
| **git 푸시 충돌** | 루틴이 멈춤 | "pull 하고 다시 푸시해 줘". 강제 푸시는 하지 않음. 푸시가 끝나기 전에는 원격 대기열에 방금 올린 글이 '게시 전'으로 남아 있으니, 그 사이 다른 세션에 같은 글을 "지금 올려"라고 하지 않음 |
| **루틴이 안 돌았음** | 그 시각 글은 다음 실행에서 180분 안이면 올라가고, 아니면 건너뜀 | 루틴 상태 확인, 필요하면 "a 지금 올려" |

---

## 8. 남은 확인 사항

- [ ] 실제 API 첫 호출: X 글·스레드·이미지 업로드(OAuth 1.0a), Instagram 4:5 캐러셀, R2 공개 주소 (§3-6)
- [ ] 'Automated' 라벨 설정 경로와 적용 범위 ([09](09-x-playbook.md) §8)
- [ ] Instagram 'AI 정보' 라벨을 API 게시물에 붙이는 방법 (§6-2)
- [ ] X 개발자 크레딧 최소 충전액, R2 무료 구간, Instagram API 요금
- [ ] 계획 세션이 채팅에 파일(미리보기·슬라이드)을 첨부할 수 있는지. 안 되면 A안 파일은 내 PC에서 `build`
