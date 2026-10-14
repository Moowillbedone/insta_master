"""X 게시·지표·댓글 후보: x-publish, x-metrics, x-targets.

  python doha.py x-publish --due              # cron 용: 게시 시각이 지난 '승인' 글만 올림 (어제·오늘 대기열)
  python doha.py x-publish --date 2026-10-20  # 그날 대기열에서 시각이 지난 승인 글
  python doha.py x-publish --id 2026-10-20-b  # 그 글 하나를 지금 바로 (승인된 글만)
  python doha.py x-publish --due --dry-run    # 무엇이 올라갈지 보기만 (API·파일 변경 없음, 키 없어도 됨)
  python doha.py x-publish --due --retry-failed   # 실패한 글 다시 시도 (스레드는 끊긴 곳부터 이어서)
  python doha.py x-publish --id 2026-10-20-b --resolve-inflight none|<글 id>
                                              # 응답 없이 끊긴 게시를 X 앱에서 확인한 결과 기록 (그 전엔 다시 올리지 않음)
  python doha.py x-metrics [--days 14]        # 내 글 지표 → tracking/x-metrics.csv, 팔로워 → tracking/x-followers.csv
  python doha.py x-targets [--date D]         # config.x.reply_targets 의 최근 글을 댓글 초안 후보로 추가 (게시는 사람이)

cron 예 (10분마다, KST 서버 기준이 아니어도 됨 — 시각 비교는 KST 로 함):
  */10 * * * * cd /경로/insta_master && .venv/bin/python doha.py x-publish --due >> out/x/publish.log 2>&1

안전장치:
  - x-approve 로 승인한 글(status: approved + approved_hash)만 올린다. 승인 뒤 글·이미지가 바뀌면 올리지 않는다.
  - 게시 직전 파일을 다시 읽어 상태를 확인하고, 'inflight' 를 먼저 적은 뒤 API 를 부른다. 그 사이 프로그램이 죽거나
    응답이 오지 않으면(시간 초과·연결 끊김) inflight 를 남긴 채 '확인 필요(failed)'로 두고, 사람이 --resolve-inflight 로
    결과를 적기 전까지 다시 올리지 않는다 → 중복 게시 없음. 연결 거부·401·402·429·5xx 처럼 확실히 안 올라간 실패만
    --retry-failed 로 다시 시도한다 (같은 글 반복은 X 도 403 으로 막음).
  - 스레드는 첫 글(이미지 포함) → 이어지는 글을 '내가 방금 올린 글'에 답글로. 중간에 실패하면 올라간 id 를 x_ids 에
    남기고, 다시 시도하면 끊긴 곳부터 이어 쓴다.
  - publish_mode: manual 이면 API 를 부르지 않고 X 앱에서 바로 열리는 링크만 보여 준다 (상태도 바꾸지 않음).
  - 게시 시각을 config.x.max_late_minutes(기본 180분) 넘게 지나면 --due 에서 건너뛴다 (--id 로는 올릴 수 있음).
  - API 비용 추정은 tracking/costs.csv 에 category=x_api 로 남긴다 (글 $0.015, 읽기 $0.005, 내 글 읽기 $0.001 — 추정).
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from doha.core import ROOT, append_csv, load_config, read_csv
from doha.xapi import XApiError, XClient
from doha.xqueue import (
    KST,
    blocking_issues,
    check_queue,
    content_hash,
    final_parts,
    find_urls,
    intent_url,
    iso,
    load_queue,
    now_kst,
    parse_date_arg,
    post_by_id,
    post_kind,
    post_status,
    post_x_ids,
    queue_files,
    queue_lock,
    queue_path,
    scheduled_at,
    tracking_dir,
    update_queue,
    weighted_length,
    xconf,
    _lst,
)

COST_FIELDS = ["date", "category", "provider", "description", "post_id",
               "amount_usd", "amount_krw", "quantity", "notes"]
METRICS_FIELDS = ["recorded_at", "date", "post_id", "x_id", "impressions", "likes", "reposts", "replies",
                  "quotes", "bookmarks"]
FOLLOWER_FIELDS = ["date", "followers", "verified_followers", "notes"]
OCR_VERIFIED_FOLLOWERS = 500           # 오리지널 콘텐츠 리워드(OCR) 기준 (research/x-revenue-sharing.md §1-3)
OCR_IMPRESSIONS_90D = 500_000
MAX_ATTEMPTS = 3
STOP_RUN_STATUSES = {401, 402, 429}    # 계정 전체 문제 → 이번 실행의 나머지 글도 멈춤
TARGET_MAX_AGE = timedelta(hours=48)


# ---------------------------------------------------------------- 공통

def log_cost(config: dict, amount_usd: float, quantity: int, description: str, post_id: str = "", notes: str = "") -> None:
    if quantity <= 0:
        return
    fx = float((config.get("fx") or {}).get("usd_krw", 0) or 0)
    append_csv(tracking_dir(config) / "costs.csv", {
        "date": now_kst().date().isoformat(), "category": "x_api", "provider": "x", "description": description,
        "post_id": post_id, "amount_usd": f"{amount_usd:.4f}", "amount_krw": round(amount_usd * fx),
        "quantity": quantity, "notes": notes,
    }, COST_FIELDS)


def _client() -> XClient | None:
    try:
        return XClient.from_env()
    except XApiError as e:
        print(e)
        return None


def _id_date(pid: str) -> date | None:
    """'2026-10-20-b' → 2026-10-20. 형식이 아니면 None, 없는 날짜(2026-13-01)면 안내하고 종료."""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})-", pid or "")
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        raise SystemExit(f"글 id 의 날짜가 올바르지 않아요: {pid!r} (예: 2026-10-20-b)") from None


def _parse_x_time(v) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(KST)
    except ValueError:
        return None


# ================================================================ x-publish

def _due(args, config: dict, xc: dict, now: datetime) -> tuple[list[tuple[date, str, datetime]], list[str]]:
    """(날짜, 글 id, 예정 시각) 목록과 안내 문장."""
    notes: list[str] = []
    if args.id:
        idd = _id_date(args.id)
        dates = [idd] if idd else [parse_date_arg(args.date)]
    elif args.due and not args.date:
        dates = [now.date() - timedelta(days=1), now.date()]
    else:
        dates = [parse_date_arg(args.date)]
    out = []
    for d in dates:
        path = queue_path(d, config)
        if not path.exists():
            if args.id or args.date:
                notes.append(f"{d} 대기열 파일이 없어요 ({path.relative_to(ROOT)}).")
            continue
        q = load_queue(path)
        for p in q.get("posts") or []:
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id"))
            if args.id and pid != args.id:
                continue
            st = post_status(p)
            retry = args.retry_failed or bool(args.id)
            if not (st == "approved" or (st == "failed" and retry)):
                if args.id:
                    notes.append(f"{pid} 은(는) {st} 상태라 올리지 않아요 (승인된 글만, 실패한 글은 다시 시도 가능).")
                continue
            if str(p.get("inflight") or "").strip():
                notes.append(f"{pid}: 올라갔는지 확인 필요 — X 앱에서 보고 "
                             f"python doha.py x-publish --id {pid} --resolve-inflight <글 id | none>")
                continue
            if st == "failed" and int(p.get("attempts") or 0) >= MAX_ATTEMPTS and not args.id:
                notes.append(f"{pid}: {MAX_ATTEMPTS}번 실패해서 자동 재시도를 멈췄어요 — 원인을 고친 뒤 x-publish --id {pid}")
                continue
            when = scheduled_at(d, p.get("slot"))
            if when is None:
                notes.append(f"{pid}: slot 형식 오류 ({p.get('slot')!r})")
                continue
            if not args.id:
                if when > now:
                    notes.append(f"{pid}: {when:%m-%d %H:%M} 예정")
                    continue
                late = (now - when).total_seconds() / 60
                if late > float(xc["max_late_minutes"]):
                    notes.append(f"{pid}: 예정 {when:%m-%d %H:%M} 에서 {int(late)}분 지나 건너뜀 — 지금 올리려면 "
                                 f"python doha.py x-publish --id {pid} (또는 slot 을 바꾸고 다시 승인)")
                    continue
            if args.id and when > now:
                notes.append(f"{pid}: 예정 시각({when:%H:%M}) 전이지만 --id 로 지금 올려요.")
            out.append((d, pid, when))
    out.sort(key=lambda x: x[2])
    return out, notes


def _preflight(q: dict, path: Path, p: dict, config: dict) -> str | None:
    """올리면 안 되는 이유 (없으면 None)."""
    pid = str(p.get("id"))
    if not str(p.get("approved_hash") or "").strip():
        return "x-approve 로 승인하지 않은 글이에요 (status 를 손으로 approved 로 바꾸지 마세요)."
    if p.get("approved_hash") != content_hash(p):
        return "승인 뒤 글·이미지가 바뀌었어요 → x-check, x-digest 로 확인하고 다시 x-approve 하세요."
    errs = blocking_issues(check_queue(q, path, config), [pid])
    if errs:
        return f"검수 오류 {len(errs)}건: " + " / ".join(f"[{e.code}] {e.message}" for e in errs[:2])
    return None


def _show_plan(d: date, p: dict, xc: dict, when: datetime) -> list[str]:
    parts = final_parts(p, xc)
    pid = str(p.get("id"))
    print(f"\n■ {pid} · {when:%m-%d %H:%M} · {'스레드 ' + str(len(parts)) + '개' if post_kind(p) == 'thread' else '단일'}")
    done = post_x_ids(p)
    for k, t in enumerate(parts):
        mark = " (이미 올라감)" if k < len(done) else ""
        print(f"  [{k + 1}] {weighted_length(t)}/{xc['max_weighted_length']}{mark}")
        for ln in t.split("\n"):
            print(f"      {ln}")
    media = [str(m) for m in _lst(p.get("media"))]
    if media:
        print(f"  이미지 {len(media)}장: {', '.join(media)}")
    return parts


def _recheck(path: Path, pid: str, k: int, allowed: tuple[str, ...]) -> str | None:
    """API 호출 직전 파일을 다시 읽어 '올려도 되는지' 확인 (손으로 고쳤거나 다른 실행이 올렸을 수 있음)."""
    q = load_queue(path)
    p = post_by_id(q, pid)
    if p is None:
        return "대기열에서 글이 사라졌어요."
    if post_status(p) not in allowed:
        return f"상태가 {post_status(p)} 로 바뀌었어요."
    if len(post_x_ids(p)) != k:
        return f"이미 {len(post_x_ids(p))}개가 올라가 있어요 (예상 {k}개)."
    if str(p.get("inflight") or "").strip():
        return f"다른 실행이 게시 중이에요 ({p.get('inflight')})."
    return None


def inflight_message(pid: str, mark: str) -> str:
    return (f"게시 도중 응답을 못 받았어요 ({mark}). 실제로 올라갔는지 몰라 자동으로 다시 올리지 않아요. "
            f"X 앱 프로필에서 확인한 뒤 — 올라갔으면: python doha.py x-publish --id {pid} --resolve-inflight <글 id>, "
            f"안 올라갔으면: python doha.py x-publish --id {pid} --resolve-inflight none")


def resolve_inflight(config: dict, xc: dict, pid: str, value: str) -> int:
    """사람이 X 앱에서 확인한 결과를 기록: none(안 올라감) 또는 올라간 글 id."""
    d = _id_date(pid)
    if d is None:
        print("--resolve-inflight 는 --id 2026-10-20-b 처럼 글 id 와 함께 쓰세요.")
        return 2
    path = queue_path(d, config)
    value = (value or "").strip()
    with queue_lock(d):
        q = load_queue(path)
        p = post_by_id(q, pid)
        if p is None:
            print(f"{d} 대기열에 {pid} 가 없어요.")
            return 1
        mark = str(p.get("inflight") or "").strip()
        if not mark:
            print(f"{pid}: 확인이 필요한 게시 기록(inflight)이 없어요.")
            return 0
        done = post_x_ids(p)
        parts = final_parts(p, xc)
        if value.lower() in ("none", "no", "0", "없음"):
            update_queue(path, posts={pid: {"inflight": "", "error": f"확인됨: {mark} 는 올라가지 않음"}})
            left = len(parts) - len(done)
            print(f"{pid}: 기록을 지웠어요. 남은 {left}개는 python doha.py x-publish --id {pid} 로 이어서 올릴 수 있어요"
                  + (" (승인 내용 그대로일 때만)." if left else "."))
            return 0
        xid = value.rsplit("/", 1)[-1].split("?")[0]   # 글 주소를 붙여 넣어도 됨
        if not re.fullmatch(r"\d{1,25}", xid):
            print(f"글 id 형식이 아니에요: {value!r} (예: 1846000000000000000 또는 https://x.com/<계정>/status/<id>)")
            return 2
        if xid in done:
            print(f"{pid}: {xid} 는 이미 기록돼 있어요.")
            update_queue(path, posts={pid: {"inflight": ""}})
            return 0
        done.append(xid)
        fields = {"x_ids": done, "x_id": done[0], "inflight": ""}
        if len(done) >= len(parts):
            fields.update({"status": "posted", "posted_at": str(p.get("posted_at") or "") or iso(now_kst()), "error": ""})
        update_queue(path, posts={pid: fields})
        if len(done) >= len(parts):
            q2 = load_queue(path)
            if all(post_status(x) in ("posted", "skipped") for x in q2.get("posts") or [] if isinstance(x, dict)):
                update_queue(path, top={"status": "done"}, quiet=True)
            print(f"{pid}: 올라간 글 {xid} 를 기록했어요 → posted")
        else:
            print(f"{pid}: 올라간 글 {xid} 를 기록했어요 ({len(done)}/{len(parts)}). 나머지는 "
                  f"python doha.py x-publish --id {pid} 로 이어서 올려요.")
    return 0


def publish_one(client: XClient, config: dict, xc: dict, d: date, pid: str) -> tuple[str, XApiError | None]:
    """→ ('posted' | 'failed' | 'skipped', 오류)."""
    path = queue_path(d, config)
    with queue_lock(d):
        q = load_queue(path)
        p = post_by_id(q, pid)
        if p is None:
            return "skipped", None
        st = post_status(p)
        if st not in ("approved", "failed"):
            print(f"  {pid}: 이미 {st} — 건너뜀")
            return "skipped", None
        attempts = int(p.get("attempts") or 0)
        if str(p.get("inflight") or "").strip():
            # 직전 실행이 API 호출 도중 죽었거나 응답을 못 받음 → 올라갔는지 모름. 표시를 남겨 두고 사람 확인을 기다린다.
            msg = inflight_message(pid, str(p.get("inflight")))
            update_queue(path, posts={pid: {"status": "failed", "error": msg}})
            print(f"  {pid}: {msg}")
            return "failed", None
        reason = _preflight(q, path, p, config)
        if reason:
            update_queue(path, posts={pid: {"status": "failed", "error": reason}})
            print(f"  {pid}: 올리지 않음 — {reason}")
            return "failed", None
        parts = final_parts(p, xc)
        done = post_x_ids(p)
        media = [str(m) for m in _lst(p.get("media"))]
        alts = [str(a or "") for a in _lst(p.get("alt"))]
        created, error, uncertain = 0, None, False
        for k in range(len(done), len(parts)):
            problem = _recheck(path, pid, k, ("approved", "failed"))
            if problem:
                print(f"  {pid}: 멈춤 — {problem}")
                return "skipped", None
            update_queue(path, posts={pid: {"inflight": f"{iso(now_kst())} {k + 1}/{len(parts)}"}}, quiet=True)
            stage = "media"
            try:
                if k == 0:
                    media_ids = [client.upload_media(ROOT / m, alts[i] if i < len(alts) else "") for i, m in enumerate(media)]
                    stage = "post"
                    new_id = client.create_post(parts[0], media_ids=media_ids or None)
                else:
                    stage = "post"
                    new_id = client.create_post(parts[k], reply_to=done[-1])
            except XApiError as e:
                error = e
                uncertain = stage == "post" and e.maybe_sent
                break
            done.append(new_id)
            created += 1
            update_queue(path, posts={pid: {"x_ids": list(done), "x_id": done[0], "inflight": ""}}, quiet=True)
            print(f"  {pid} [{k + 1}/{len(parts)}] 게시 → https://x.com/i/status/{new_id}")
        if error is not None and uncertain:
            mark = f"{iso(now_kst())} {len(done) + 1}/{len(parts)} 응답 없음"
            msg = inflight_message(pid, mark) + f" (원인: {error})"
            update_queue(path, posts={pid: {"status": "failed", "error": msg, "inflight": mark,
                                            "attempts": attempts + 1}})
            print(f"  {pid}: {msg}")
        elif error is not None:
            where = f"{len(done) + 1}/{len(parts)}번째 글" + (" 이미지 업로드에서" if stage == "media" else "에서")
            hint = ""
            if stage == "media" and error.status in (401, 403):
                hint = (" → 글 게시는 안 했어요. 이미지 업로드만 거부되면 OAuth 1.0a 로 v2 업로드가 막힌 것일 수 있어요 "
                        "(docs/09 남은 확인). 이미지를 빼고 다시 승인하거나 X 앱에서 올리세요.")
            elif stage == "post" and done and error.status == 403:
                hint = " → 내 스레드 이어 쓰기(내 글에 답글)가 막혔을 수 있어요. 나머지는 X 앱에서 이어 붙이세요 (docs/10 §7)."
            update_queue(path, posts={pid: {"status": "failed", "error": f"{where} 실패: {error}{hint}", "inflight": "",
                                            "attempts": attempts + 1}})
            print(f"  {pid}: {where} 실패 — {error}{hint}")
            if done:
                print(f"    이미 올라간 {len(done)}개는 그대로 두고, 다시 시도하면 끊긴 곳부터 이어서 올려요 "
                      f"(x-publish --id {pid} 또는 --retry-failed).")
        else:
            update_queue(path, posts={pid: {"status": "posted", "posted_at": iso(now_kst()), "error": "", "inflight": ""}})
            q2 = load_queue(path)
            if all(post_status(x) in ("posted", "skipped") for x in q2.get("posts") or [] if isinstance(x, dict)):
                update_queue(path, top={"status": "done"}, quiet=True)
                print(f"  {d} 대기열의 글을 모두 올려서 status: done")
    if created:
        has_link = any(find_urls(t) for t in parts)
        price = float(xc["cost_per_link_post_usd"] if has_link else xc["cost_per_post_usd"])
        log_cost(config, created * price, created, f"X 글 작성 {pid} ({created}건)", pid,
                 f"추정 단가 ${price}/건 (config.x.cost_per_post_usd). 미디어 업로드 과금 여부는 미확인")
    return ("failed", error) if error is not None else ("posted", None)


def cmd_publish(args) -> int:
    config = load_config()
    xc = xconf(config)
    if getattr(args, "resolve_inflight", None):
        return resolve_inflight(config, xc, args.id or "", args.resolve_inflight)
    now = now_kst()
    due, notes = _due(args, config, xc, now)
    if not due:
        upcoming = [n for n in notes if n.endswith("예정")]
        others = [n for n in notes if not n.endswith("예정")]
        print(f"[{now:%m-%d %H:%M} KST] 지금 올릴 글이 없어요." + (f" 다음: {upcoming[0]}" if upcoming else ""))
        for n in others:
            print(f"  {n}")
        return 1 if any("파일이 없어요" in n for n in others) else 0
    for n in notes:
        if not n.endswith("예정"):
            print(f"  {n}")

    if xc["publish_mode"] == "manual" or args.dry_run:
        label = "미리 보기 (--dry-run, API·파일 변경 없음)" if args.dry_run else "manual 모드 — X 앱에서 직접 게시"
        print(f"[{now:%m-%d %H:%M} KST] {label}: {len(due)}개")
        for d, pid, when in due:
            path = queue_path(d, config)
            q = load_queue(path)
            p = post_by_id(q, pid)
            parts = _show_plan(d, p, xc, when)
            reason = _preflight(q, path, p, config)
            if reason:
                print(f"  ⛔ 올리지 않을 글: {reason}")
                continue
            if xc["publish_mode"] == "manual":
                print(f"  X 앱에서 열기: {intent_url(parts[0])}")
                if _lst(p.get("media")):
                    print("  이미지는 X 앱에서 직접 첨부하세요 ('Made with AI' 표시도 켜기).")
                if len(parts) > 1:
                    print("  이어지는 글은 첫 글을 올린 뒤 그 글에 답글로 붙여 주세요.")
            else:
                done = len(post_x_ids(p))
                print(f"  → API 로 {len(parts) - done}건 게시 예정 (약 ${(len(parts) - done) * float(xc['cost_per_post_usd']):.3f})")
        if xc["publish_mode"] == "manual" and not args.dry_run:
            print("\nmanual 모드라 대기열 상태는 바꾸지 않았어요. 올린 뒤 원하면 status: posted, x_id 를 적어 두세요 (x-metrics 용).")
        return 0

    client = _client()
    if client is None:
        return 1
    print(f"[{now:%m-%d %H:%M} KST] 게시할 글 {len(due)}개")
    failed = 0
    for d, pid, when in due:
        result, err = publish_one(client, config, xc, d, pid)
        if result == "failed":
            failed += 1
            if err is not None and err.status in STOP_RUN_STATUSES:
                rest = [x[1] for x in due if x[2] > when or (x[2] == when and x[1] > pid)]
                if rest:
                    print(f"  계정 전체 문제라 이번 실행의 나머지 글({', '.join(rest)})은 다음 실행으로 미뤄요.")
                break
    if client.reads:
        log_cost(config, client.reads * float(xc["cost_per_owned_read_usd"]), client.reads,
                 "X 내 글 확인 (스레드 이어 쓰기)", notes="추정 단가 $0.001/건")
    return 1 if failed else 0


# ================================================================ x-metrics

def _latest_by_xid(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        xid = (r.get("x_id") or "").strip()
        if xid and (xid not in out or (r.get("recorded_at") or "") >= (out[xid].get("recorded_at") or "")):
            out[xid] = r
    return out


def _num(v) -> int | None:
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def print_ocr_progress(config: dict, followers, new_rows: list[dict], today: date) -> None:
    tdir = tracking_dir(config)
    frows = read_csv(tdir / "x-followers.csv")
    verified = next((_num(r.get("verified_followers")) for r in reversed(frows) if _num(r.get("verified_followers")) is not None), None)
    rows = read_csv(tdir / "x-metrics.csv") + new_rows
    latest = _latest_by_xid(rows)
    since = today - timedelta(days=90)
    heads = 0
    total = 0
    for r in latest.values():
        try:
            d = date.fromisoformat((r.get("date") or "")[:10])
        except ValueError:
            continue
        if d < since or "#" in (r.get("post_id") or ""):
            continue   # 90일 밖, 또는 스레드의 이어지는 글(답글 — OCR 노출에서 빠짐)
        n = _num(r.get("impressions"))
        if n is not None:
            total += n
            heads += 1
    print("\n수익화(오리지널 콘텐츠 리워드) 기준까지 — Premium 구독·계정 3개월·2단계 인증은 별도 조건")
    if verified is not None:
        print(f"  인증 팔로워 {verified:,} / {OCR_VERIFIED_FOLLOWERS} ({min(100, verified * 100 // OCR_VERIFIED_FOLLOWERS)}%) "
              "— x-followers.csv 에 직접 적은 값")
    else:
        f = _num(followers)
        print(f"  인증 팔로워 ? / {OCR_VERIFIED_FOLLOWERS} — API 로는 인증 팔로워 수를 받을 수 없어요. "
              f"전체 팔로워 {f if f is not None else '?'}명이 최대치예요."
              " X 앱에서 확인해 tracking/x-followers.csv 의 verified_followers 에 적으면 여기 반영돼요.")
    print(f"  최근 90일 노출 {total:,} / {OCR_IMPRESSIONS_90D:,} ({min(100, total * 100 // OCR_IMPRESSIONS_90D)}%, 원글 {heads}개)"
          " — 상한값: API 노출수는 '인증 사용자의 홈 타임라인' 노출만 따로 세지 못해요. 실제 적격 노출은 이보다 적어요.")


def cmd_metrics(args) -> int:
    config = load_config()
    xc = xconf(config)
    now = now_kst()
    today = now.date()
    since = today - timedelta(days=args.days)
    src: list[tuple[date, str, str]] = []   # (날짜, post_id 표시, x_id)
    for d, path in queue_files(config):
        if d < since or d > today:
            continue
        try:
            q = load_queue(path)
        except SystemExit as e:
            print(f"  {path.name}: {e}")
            continue
        for p in q.get("posts") or []:
            if not isinstance(p, dict):
                continue
            for k, xid in enumerate(post_x_ids(p)):
                src.append((d, str(p.get("id")) + (f"#{k + 1}" if k else ""), xid))
    client = _client()
    if client is None:
        return 1
    try:
        metrics = client.get_posts_metrics([x for _, _, x in src]) if src else {}
        me = client.get_me()
    except XApiError as e:
        print(f"X API 요청 실패: {e}")
        return 1
    tdir = tracking_dir(config)
    mpath, fpath = tdir / "x-metrics.csv", tdir / "x-followers.csv"
    existing = {((r.get("x_id") or "").strip(), (r.get("recorded_at") or "")[:10]) for r in read_csv(mpath)}
    new_rows, written = [], 0
    if not src:
        print(f"최근 {args.days}일 안에 게시된 X 글이 없어요 (content/x/*.yaml 의 x_id 기준).")
    for d, pid, xid in src:
        item = metrics.get(xid)
        if item is None:
            print(f"  {pid} ({xid}): 지표 없음 — 삭제됐거나 보호된 글일 수 있어요.")
            continue
        pm = item.get("public_metrics") or {}
        row = {
            "recorded_at": iso(now), "date": d.isoformat(), "post_id": pid, "x_id": xid,
            "impressions": pm.get("impression_count", ""), "likes": pm.get("like_count", ""),
            "reposts": pm.get("retweet_count", ""), "replies": pm.get("reply_count", ""),
            "quotes": pm.get("quote_count", ""), "bookmarks": pm.get("bookmark_count", ""),
        }
        new_rows.append(row)
        print(f"  {pid:<18} 노출 {row['impressions'] if row['impressions'] != '' else '?':>7} · 좋아요 {row['likes']} · "
              f"리포스트 {row['reposts']} · 답글 {row['replies']} · 인용 {row['quotes']} · 북마크 {row['bookmarks']}")
        if not args.dry_run and (xid, today.isoformat()) not in existing:
            append_csv(mpath, row, METRICS_FIELDS)
            written += 1
    pmx = me.get("public_metrics") or {}
    followers = pmx.get("followers_count", "")
    print(f"\n@{me.get('username', '?')} 팔로워 {followers}명")
    if not args.dry_run:
        if today.isoformat() not in {(r.get("date") or "").strip() for r in read_csv(fpath)}:
            append_csv(fpath, {"date": today.isoformat(), "followers": followers, "verified_followers": "",
                               "notes": "x-metrics 자동 기록 (인증 팔로워 수는 X 앱에서 확인해 직접 입력)"}, FOLLOWER_FIELDS)
        log_cost(config, client.reads * float(xc["cost_per_owned_read_usd"]), client.reads, "X 지표 읽기",
                 notes="내 글 읽기 추정 단가 $0.001/건")
        print(f"기록: {mpath.relative_to(ROOT) if mpath.is_relative_to(ROOT) else mpath} {written}줄 (같은 날 같은 글은 한 번만)")
    else:
        print("(--dry-run: CSV 에 쓰지 않음)")
    print_ocr_progress(config, followers, new_rows if args.dry_run else [], today)
    return 0


# ================================================================ x-targets

def _user_cache_path() -> Path:
    return ROOT / "out" / "x" / ".cache" / "user_ids.json"


def _load_user_cache() -> dict:
    try:
        return json.loads(_user_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_user_cache(cache: dict) -> None:
    path = _user_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_targets(args) -> int:
    config = load_config()
    xc = xconf(config)
    now = now_kst()
    d = parse_date_arg(args.date)
    path = queue_path(d, config)
    if not path.exists():
        print(f"{d} 대기열이 없어요. 먼저 python doha.py x-new {d}")
        return 1
    targets = xc["reply_targets"]
    if not targets:
        print("config.yaml 의 x.reply_targets 가 비어 있어요. 댓글을 달고 싶은 계정(@ 없이)을 사람이 직접 골라 넣으세요.\n"
              "  (패션·직장인·한국 브랜드 계정 5~10개. 자동으로 계정을 찾거나 댓글을 달지는 않아요.)")
        return 0
    budget = int(xc["max_targets_reads"])
    per_account = 3
    start = d.toordinal() % len(targets)          # 날마다 다른 계정부터 → 며칠에 걸쳐 고르게
    order = targets[start:] + targets[:start]
    seen = set()
    for fd, fp in queue_files(config):
        if abs((fd - d).days) <= 7:
            try:
                for r in load_queue(fp).get("replies") or []:
                    if isinstance(r, dict) and r.get("target_url"):
                        seen.add(str(r["target_url"]).strip())
            except SystemExit:
                pass
    client = _client()
    if client is None:
        return 1
    cache = _load_user_cache()
    new_items, old, dup, checked = [], 0, 0, []
    for user in order:
        if client.post_reads + 5 > budget:   # 한 번에 5개씩 읽힌다 (API 최소 단위)
            break
        try:
            posts = client.get_user_posts(user, per_account, user_id=cache.get(user.lower()))
        except XApiError as e:
            print(f"  @{user}: {e}")
            if e.status in STOP_RUN_STATUSES:
                break
            if e.status == 404:
                cache.pop(user.lower(), None)
            continue
        checked.append(user)
        if posts:
            cache[user.lower()] = str(posts[0].get("author_id") or cache.get(user.lower()) or "")
        for t in posts:
            created = _parse_x_time(t.get("created_at"))
            if created is not None and now - created > TARGET_MAX_AGE:
                old += 1
                continue
            url = f"https://x.com/{t.get('username') or user}/status/{t.get('id')}"
            if url in seen:
                dup += 1
                continue
            seen.add(url)
            new_items.append({"target_url": url, "target_author": t.get("username") or user,
                              "target_text": str(t.get("text") or "").strip(), "draft": "", "status": "todo"})
    _save_user_cache({k: v for k, v in cache.items() if v})
    if client.reads:
        log_cost(config, client.reads * float(xc["cost_per_read_usd"]), client.reads,
                 f"X 댓글 후보 읽기 ({', '.join('@' + u for u in checked)})",
                 notes=f"게시물 {client.post_reads} + 사용자 조회 {client.user_reads}, 추정 단가 ${xc['cost_per_read_usd']}/건")
    print(f"확인한 계정: {', '.join('@' + u for u in checked) or '없음'} (읽기 {client.reads}건, 예산 게시물 {budget}건)")
    if old or dup:
        print(f"  건너뜀: 48시간 지난 글 {old}개, 이미 후보에 있는 글 {dup}개")
    if not new_items:
        print("새 댓글 후보가 없어요.")
        return 0
    if args.dry_run:
        for it in new_items:
            print(f"  + @{it['target_author']}: {it['target_text'][:60]}")
        print("(--dry-run: 대기열에 쓰지 않음)")
        return 0
    with queue_lock(d):
        update_queue(path, add_replies=new_items)
    print(f"{path.relative_to(ROOT)} replies 에 후보 {len(new_items)}개를 추가했어요 (draft 는 비어 있음).")
    print(f"다음: draft 채우기(대가·멘션·링크 없이, 원글에 실제로 보탬이 되는 한두 문장) → x-check {d} → x-digest {d}\n"
          "      댓글은 사람이 digest 의 'X 앱에서 답글 열기'로 직접 올리고, 올린 뒤 status: done.")
    return 0


# ================================================================ CLI

def add_arguments(parser, command_name: str = "x-publish") -> None:
    if command_name == "x-publish":
        parser.add_argument("--date", help="대기열 날짜 (기본 오늘)")
        parser.add_argument("--due", action="store_true", help="cron 용: 어제·오늘 대기열에서 시각이 지난 승인 글")
        parser.add_argument("--id", help="이 글 하나만 지금 (예: 2026-10-20-b)")
        parser.add_argument("--dry-run", action="store_true", help="올릴 글만 보여 주기 (API·파일 변경 없음)")
        parser.add_argument("--retry-failed", action="store_true", help=f"실패한 글도 다시 시도 (최대 {MAX_ATTEMPTS}번, 스레드는 이어서)")
        parser.add_argument("--resolve-inflight", metavar="X_ID|none",
                            help="--id 와 함께: 응답 없이 끊긴 게시를 X 앱에서 확인한 결과 (올라간 글 id 또는 none)")
    elif command_name == "x-metrics":
        parser.add_argument("--days", type=int, default=14, help="최근 며칠 안에 올린 글 (기본 14)")
        parser.add_argument("--dry-run", action="store_true", help="CSV 에 쓰지 않고 보기만")
    elif command_name == "x-targets":
        parser.add_argument("--date", help="후보를 넣을 대기열 날짜 (기본 오늘)")
        parser.add_argument("--dry-run", action="store_true", help="대기열에 쓰지 않고 보기만 (API 읽기 비용은 발생)")


def run(args) -> int:
    cmd = getattr(args, "command", "x-publish")
    if cmd == "x-metrics":
        return cmd_metrics(args)
    if cmd == "x-targets":
        return cmd_targets(args)
    return cmd_publish(args)
