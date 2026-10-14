# content/x — X 게시 대기열

하루에 파일 하나(`YYYY-MM-DD.yaml`)씩, 그날 X에 올릴 글과 사람이 직접 달 댓글 초안을 담습니다.
운영 규칙은 [docs/09-x-playbook.md](../../docs/09-x-playbook.md), 매일 돌아가는 절차는 [docs/10-autopilot.md](../../docs/10-autopilot.md)에 있습니다.

## 하루 흐름

```
x-new D      뼈대 만들기 (있으면 덮어쓰지 않음)
  ↓          Claude 가 posts·replies 를 채움
x-check D    가중 글자 수·링크·해시태그·멘션·참여 유도·체험 표현·중복·광고 표시 검수 (오류 0 이어야 승인 가능)
x-digest D   out/x/D/digest.html (휴대폰 카드), digest.md (채팅용)  ← out/ 은 git 제외
x-approve D  사람이 채팅에 "승인" → 하루 1번 승인 (--ids a,c 일부만, --undo 취소)
x-publish    게시 루틴이 시각마다 --due 로 실행. 승인된 글만, 예정 시각이 지나고 180분 안일 때
x-metrics    주간 루틴이 지표를 tracking/x-metrics.csv, x-followers.csv 에 기록
```

모든 명령은 `python doha.py <명령>` 형식입니다. D 자리에는 `2026-10-20`, `today`, `tomorrow`를 쓸 수 있습니다.

| 명령 | 자주 쓰는 옵션 |
|---|---|
| `x-new D` | `--posts 3` |
| `x-check D` | `--all` (폴더 전체), `--allow-long` (Premium 장문: 길이 초과를 주의로), `--text "문장"` (글자 수만 재기) |
| `x-digest D` | `--png` (휴대폰 폭 캡처, Chromium 필요) |
| `x-approve D` | `--ids a,c`, `--undo` |
| `x-publish` | `--due`, `--date D`, `--id D-a`, `--dry-run`, `--retry-failed`, `--id D-a --resolve-inflight <글 id 또는 none>` |
| `x-metrics` | `--days 14`, `--dry-run` |
| `x-targets` | `--date D`, `--dry-run` (댓글 후보를 replies 에 추가. 댓글은 사람이 직접) |

## 파일 형식

```yaml
date: 2026-10-20
status: draft            # draft | approved | done            ← 도구가 바꿈
approved_at: ""          #                                     ← x-approve 가 씀
posts:
  - id: "2026-10-20-a"   # 날짜 + 글자
    slot: "08:10"        # KST, config.x.slots 중 하나
    kind: single         # single | thread
    text: "..."          # 첫 글
    thread: []           # kind: thread 일 때 이어지는 글 (각각 한 개의 글)
    media: []            # 저장소 기준 이미지 경로, 최대 4장 (예: content/posts/<id>/images/s01.png)
    alt: []              # 이미지마다 대체 텍스트
    ai_image: false      # AI 이미지면 true → 게시할 때 config.x.ai_image_note('AI 이미지')를 끝에 자동 추가
    source_post: ""      # 옮겨 온 Instagram 게시물 id (캡션을 그대로 쓰지 말고 X 용으로 새로 쓰기)
    status: draft        # draft | approved | posted | failed | skipped   ← 도구가 바꿈
    x_id: ""             #                                     ← x-publish 가 씀
    posted_at: ""
    error: ""
replies:                 # 사람이 X 앱에서 직접 달 댓글 초안
  - target_url: ""       # https://x.com/<user>/status/<id>
    target_author: ""
    target_text: ""
    draft: ""
    status: todo         # todo | done | skipped
notes: ""
```

**누가 무엇을 쓰나**

- Claude(또는 사람): `slot`, `kind`, `text`, `thread`, `media`, `alt`, `ai_image`, `source_post`, `replies[].draft`, `replies[].status`(사람이 댓글을 단 뒤 `done`), `notes`
- 도구만: `status`, `approved_at`, `x_id`, `posted_at`, `error`, 그리고 도구가 덧붙이는 `approved_hash`, `x_ids`, `inflight`, `attempts`. **손으로 고치지 않습니다.** 특히 `status`를 손으로 `approved`로 바꿔도 `approved_hash`가 없으면 게시되지 않습니다.
  - 예외 하나: 사람이 X 앱에서 **직접 올린** 글(manual 모드, 끊긴 스레드의 나머지를 앱에서 이어 붙인 경우)은 사용자가 알려 준 글 주소로 그 글의 `status: posted`, `x_id`(주소 끝 숫자), `posted_at`만 적습니다(`x-metrics`가 지표를 읽는 데 필요). `approved_hash`는 건드리지 않습니다. 응답이 끊겨 `inflight`가 남은 글은 손으로 고치지 말고 `x-publish --id <글 id> --resolve-inflight <글 주소 | none>`을 씁니다.
- 승인한 뒤 글·이미지를 고치면 게시가 거부됩니다. 고쳤으면 `x-check` → `x-digest` → 다시 `x-approve`.
- 주석은 그대로 남습니다. 도구는 상태 칸만 줄 단위로 바꿔 씁니다.

## 글쓰기 규칙 (요약)

자세한 것은 [docs/09-x-playbook.md](../../docs/09-x-playbook.md) §5.

- X 가중 글자 수 280 이하. 한글 1자 = 2, 띄어쓰기·줄바꿈 = 1 → 한국어 글은 띄어쓰기 포함 160자 안팎 (빈칸 없이 한글만이면 140자). 정확한 값은 `x-check --text "문장"`
- 링크 없음(프로필 링크 사용), 해시태그 0~1개, @멘션 없음
- 참여 유도 금지("RT하면", "댓글 달면", "맞팔", "추첨"…), 체험 지어내기 금지("입어보니"…)
- 인스타 캡션을 그대로 옮기지 않음 (`source_post`를 적으면 `x-check`가 80% 넘게 같을 때 막음)
- 광고·협찬 글: 첫 줄 `[광고 · 브랜드]` 또는 `[협찬 · 브랜드]`, 첫 두 줄 안에 가상인물 고지
- 도하 이미지(`content/posts/`·`brand/`)를 붙이면 반드시 `ai_image: true`. 빠뜨리면 `x-check`가 `[x.ai]` **오류**를 내고 `x-approve`가 승인을 거부합니다 (다른 이미지는 주의)
- 스레드는 이틀에 1개, A vs B 질문은 주 2회 이하, 글 사이 120분 이상

## 지금 들어 있는 파일

`2026-10-20.yaml`, `2026-10-21.yaml`, `2026-10-22.yaml`은 **샘플 3일치**입니다. 인스타 캘린더(10/19 네이비+카멜 컬러 공식, 10/21 트렌치 벨트 릴스, 10/23 베이지 트렌치 날씨별)에 맞춰 X용으로 새로 썼고 `x-check`를 통과합니다.

- 모두 `status: draft`라 승인 전에는 올라가지 않습니다.
- 이미지가 아직 없어 `media: []`입니다. 이미지가 생기면 계획 세션이 `media`·`alt`를 채우고 `ai_image: true`로 바꿉니다.
- `replies: []`입니다. 댓글 대상 계정(`config.yaml` `x.reply_targets`)을 사람이 고른 뒤 `x-targets`로 채웁니다.
- 실제로 쓰기 전에 계획 세션이 날씨 숫자와 인스타 일정 변경 여부를 다시 확인합니다.

## 넣지 않는 것

- 키·토큰 같은 비밀값 (환경 변수에만)
- 남의 글·이미지를 옮긴 내용 (원본만)
- `out/`의 미리보기 파일 (다시 만들 수 있어 git 제외)
