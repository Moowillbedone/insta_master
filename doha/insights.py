"""Instagram API(Instagram 로그인 방식)로 내 계정의 게시물 지표를 가져와 tracking/metrics.csv 에 기록.

준비 (docs/07-automation.md 참고):
  1. 프로페셔널(크리에이터) 계정 전환
  2. Meta 개발자 앱에서 Instagram API with Instagram Login 설정, 본인 계정으로 장기 토큰 발급
     (본인 계정만 쓰면 Standard Access로 충분, 앱 리뷰 불필요 — research/ig-platform.md §6-4)
  3. .env 에 IG_ACCESS_TOKEN 입력 (IG_USER_ID 는 비워 두면 /me 로 조회)

동작:
  - 최근 게시물 목록을 읽고, post.yaml 의 posted.url / posted.reel_url 과 숏코드로 매칭
  - 게시 후 경과 시간으로 기록 시점(24h / 7d / 30d)을 정하고, 이미 기록된 (post_id, checkpoint, format) 은 건너뜀
  - 지표는 하나씩 요청한다. 게시물 유형마다 지원 지표가 달라서 한 번에 요청하면 전체가 실패하기 때문
  - impressions 는 2025년에 폐지됐으므로 쓰지 않는다 (views 사용)

API로 받을 수 없는 값(평균 시청 시간 등)은 비워 두고 앱 인사이트에서 직접 채운다.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from doha.core import ROOT, append_csv, list_posts, load_config, read_csv

API_HOST = "https://graph.instagram.com"
KST = timezone(timedelta(hours=9))

METRICS_FIELDS = [
    "post_id", "checkpoint", "recorded_at", "format", "reach", "views", "likes", "comments",
    "saves", "shares", "profile_visits", "follows", "link_clicks", "avg_watch_sec",
    "completion_rate", "notes",
]
# CSV 열 → API 지표 이름 (요청 순서대로 하나씩 시도)
API_METRICS = {
    "reach": "reach",
    "views": "views",
    "likes": "likes",
    "comments": "comments",
    "saves": "saved",
    "shares": "shares",
    "follows": "follows",
    "profile_visits": "profile_visits",
    "avg_watch_sec": "ig_reels_avg_watch_time",  # 밀리초로 내려옴 → 초로 변환
}
CHECKPOINTS = [  # (이름, 최소 경과, 최대 경과)
    ("24h", timedelta(hours=20), timedelta(hours=72)),
    ("7d", timedelta(days=6), timedelta(days=14)),
    ("30d", timedelta(days=28), timedelta(days=60)),
]
SHORTCODE_RE = re.compile(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")


def add_arguments(parser) -> None:
    parser.add_argument("--limit", type=int, default=30, help="최근 게시물 몇 개까지 볼지 (기본 30)")
    parser.add_argument("--dry-run", action="store_true", help="CSV에 쓰지 않고 가져온 값만 보여주기")
    parser.add_argument("--checkpoint", choices=["24h", "7d", "30d"], help="경과 시간과 상관없이 이 시점 이름으로 기록")
    parser.add_argument("--followers", action="store_true", help="팔로워 수도 tracking/followers.csv 에 기록")
    parser.add_argument("--mock-file", help="(테스트용) API 대신 읽을 JSON 파일")


def shortcode(url: str | None) -> str | None:
    if not url:
        return None
    m = SHORTCODE_RE.search(url)
    return m.group(1) if m else None


def post_index() -> dict[str, tuple[str, str]]:
    """숏코드 → (post_id, format). posted.url 은 카드뉴스, posted.reel_url 은 릴스로 본다."""
    index: dict[str, tuple[str, str]] = {}
    for post in list_posts():
        posted = post.data.get("posted") or {}
        fmt = post.data.get("format", "carousel")
        main_fmt = "reel" if fmt == "reel" else "carousel"
        if sc := shortcode(posted.get("url")):
            index[sc] = (post.id, main_fmt)
        if sc := shortcode(posted.get("reel_url")):
            index[sc] = (post.id, "reel")
    return index


class Api:
    def __init__(self, token: str, version: str = "", mock: dict | None = None):
        self.token = token
        self.version = version.strip("/")
        self.mock = mock

    def get(self, path: str, **params) -> dict:
        if self.mock is not None:
            key = path + ("?" + "&".join(f"{k}={v}" for k, v in sorted(params.items())) if params else "")
            if key in self.mock:
                value = self.mock[key]
                if isinstance(value, dict) and "error" in value:
                    raise ApiError(value["error"].get("message", "mock error"))
                return value
            raise ApiError(f"mock에 없음: {key}")
        base = f"{API_HOST}/{self.version}" if self.version else API_HOST
        query = urllib.parse.urlencode({**params, "access_token": self.token})
        req = urllib.request.Request(f"{base}/{path.lstrip('/')}?{query}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
            except Exception:
                detail = ""
            raise ApiError(f"HTTP {e.code} {detail}".strip()) from None
        except urllib.error.URLError as e:
            raise ApiError(f"연결 실패: {e.reason}") from None


class ApiError(Exception):
    pass


def media_metric(api: Api, media_id: str, metric: str):
    data = api.get(f"{media_id}/insights", metric=metric)
    for item in data.get("data", []):
        if item.get("name") == metric:
            values = item.get("values") or []
            if values:
                return values[0].get("value")
            return item.get("total_value", {}).get("value")
    return None


def pick_checkpoint(posted_at: datetime, now: datetime) -> str | None:
    age = now - posted_at
    for name, lo, hi in CHECKPOINTS:
        if lo <= age < hi:
            return name
    return None


def run(args) -> int:
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    mock = None
    if args.mock_file:
        mock = json.loads(Path(args.mock_file).read_text(encoding="utf-8"))
    elif not token:
        print("IG_ACCESS_TOKEN 이 없어요. .env.example 을 .env 로 복사해 토큰을 넣어 주세요.")
        print("토큰은 채팅이나 문서에 붙여넣지 말고 .env 에만 두세요. 발급 방법: docs/07-automation.md")
        return 1
    api = Api(token, os.environ.get("IG_API_VERSION", ""), mock)
    user = os.environ.get("IG_USER_ID", "").strip() or "me"
    tracking = ROOT / load_config()["paths"]["tracking"]
    now = datetime.now(KST)

    try:
        if args.followers:
            me = api.get(user, fields="username,followers_count,media_count")
            row = {"date": now.date().isoformat(), "followers": me.get("followers_count", ""),
                   "notes": f"API 자동 기록 (게시물 {me.get('media_count', '?')}개)"}
            print(f"팔로워 {row['followers']}명")
            if not args.dry_run:
                append_csv(tracking / "followers.csv", row, ["date", "followers", "notes"])
        listing = api.get(f"{user}/media", fields="id,media_type,media_product_type,permalink,timestamp",
                          limit=str(args.limit))
    except ApiError as e:
        print(f"Instagram API 요청 실패: {e}")
        print("토큰 만료(60일), 권한(instagram_business_basic, instagram_business_manage_insights), 프로페셔널 계정 여부를 확인하세요.")
        return 1

    index = post_index()
    existing = {(r["post_id"], r["checkpoint"], r["format"]) for r in read_csv(tracking / "metrics.csv")}
    written = 0
    for media in listing.get("data", []):
        sc = shortcode(media.get("permalink"))
        post_id, fmt = index.get(sc, (f"ig:{sc}", None))
        if fmt is None:
            fmt = "reel" if media.get("media_product_type") == "REELS" else "carousel"
        posted_at = datetime.strptime(media["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        checkpoint = args.checkpoint or pick_checkpoint(posted_at, now)
        label = f"{post_id} ({fmt}, {posted_at.astimezone(KST):%m-%d %H:%M})"
        if not checkpoint:
            print(f"· {label}: 기록 시점(24h·7d·30d) 아님 — 건너뜀")
            continue
        if (post_id, checkpoint, fmt) in existing:
            print(f"· {label}: {checkpoint} 이미 기록됨")
            continue
        row = {"post_id": post_id, "checkpoint": checkpoint, "recorded_at": now.isoformat(timespec="minutes"),
               "format": fmt}
        missing = []
        for column, metric in API_METRICS.items():
            if column == "avg_watch_sec" and fmt != "reel":
                continue
            try:
                value = media_metric(api, media["id"], metric)
            except ApiError:
                value = None
            if value is None:
                missing.append(column)
                continue
            row[column] = round(value / 1000, 1) if column == "avg_watch_sec" else value
        notes = ["API 자동 기록"]
        if post_id.startswith("ig:"):
            notes.append("post.yaml posted.url 미등록")
        if missing:
            notes.append("API 미제공: " + ",".join(missing))
        row["notes"] = " / ".join(notes)
        shown = ", ".join(f"{k}={row[k]}" for k in ("reach", "views", "saves", "shares", "follows") if k in row)
        print(f"✓ {label} {checkpoint}: {shown or '지표 없음'}")
        if not args.dry_run:
            append_csv(tracking / "metrics.csv", row, METRICS_FIELDS)
            existing.add((post_id, checkpoint, fmt))
            written += 1
    print(f"\n{written}줄 기록{' (dry-run: 기록 안 함)' if args.dry_run else ''}. 다음: python doha.py metrics")
    return 0
