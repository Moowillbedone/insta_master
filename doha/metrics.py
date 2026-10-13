"""성과·수익·비용 분석 리포트 (metrics).

  python doha.py metrics                    # 이번 달 리포트 → out/reports/metrics-<오늘>.md
  python doha.py metrics --month 2026-10
  python doha.py metrics --data-dir /임시/폴더   # 테스트용 tracking 폴더 (안에 posts/ 가 있으면 게시물 메타도 거기서)

입력 (열 의미·기록 시점은 tracking/README.md):
  tracking/metrics.csv    게시물별 24h·7d(·30d) 지표. 카드뉴스와 릴스는 따로 한 줄씩
  tracking/followers.csv  팔로워 수
  tracking/revenue.csv    수익. status=paid 만 실현 수익, contracted·invoiced 는 파이프라인
  tracking/costs.csv      비용. amount_krw 가 없으면 amount_usd × config.fx.usd_krw
  content/posts/*/post.yaml  series·pillar·format·goal·hook 을 post_id 로 붙임

다른 모듈용 함수 (모두 data_dir=None 이면 실제 tracking/ 을 읽음):
  load_metrics(data_dir)          metrics.csv 행 목록 (숫자 열은 int/float, 빈 칸은 None)
  post_rates(metrics, meta, ...)  게시물(카드뉴스·릴스 각각)별 대표 기록 1줄 + 비율 + 상위/하위 표시
  summarize(month, data_dir)      리포트에 들어가는 값 전체 (JSON 직렬화 가능한 dict)
"""
from __future__ import annotations

import csv
import io
import math
import os
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from doha.core import ROOT, load_config, load_yaml

KST = timezone(timedelta(hours=9))
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DATE_RE = re.compile(r"(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})")

# 고정 스키마 (열 이름 바꾸지 않음)
SCHEMAS = {
    "metrics.csv": ["post_id", "checkpoint", "recorded_at", "format", "reach", "views", "likes", "comments",
                    "saves", "shares", "profile_visits", "follows", "link_clicks", "avg_watch_sec",
                    "completion_rate", "notes"],
    "followers.csv": ["date", "followers", "notes"],
    "revenue.csv": ["date", "type", "brand", "post_id", "gross_krw", "withholding_krw", "net_krw", "status", "notes"],
    "costs.csv": ["date", "category", "provider", "description", "post_id", "amount_usd", "amount_krw",
                  "quantity", "notes"],
}
COUNT_COLS = ("reach", "views", "likes", "comments", "saves", "shares", "profile_visits", "follows", "link_clicks")
FLOAT_COLS = ("avg_watch_sec", "completion_rate")
ENGAGEMENT_COLS = ("likes", "comments", "saves", "shares")

# 7d 를 먼저 본다: 24h 는 아직 퍼지는 중이라 게시물끼리 비교하기엔 이르다
CHECKPOINT_PREF = ("7d", "24h", "30d")

# 비율 이름 → (분자 열, 한국어)
RATES = {
    "save_rate": ("saves", "저장률"),
    "share_rate": ("shares", "공유율"),
    "follow_rate": ("follows", "팔로우율"),
    "profile_rate": ("profile_visits", "프로필 방문율"),
    "click_rate": ("link_clicks", "링크 클릭률"),
    "engagement_rate": ("engagement", "참여율"),
}
GOAL_METRIC = {"save": "save_rate", "share": "share_rate", "follow": "follow_rate",
               "click": "click_rate", "reach": "reach"}
METRIC_KO = {**{k: v[1] for k, v in RATES.items()}, "reach": "도달"}
FORMAT_KO = {"carousel": "카드뉴스", "reel": "릴스"}

REVENUE_TYPES = {"sponsorship": "협찬 게시비", "production": "제작비", "usage_rights": "사용권",
                 "affiliate": "제휴 수수료", "gifted": "현물 협찬", "other": "기타"}
REVENUE_STATUS = {"contracted": "계약", "invoiced": "청구", "paid": "입금", "cancelled": "취소"}
COST_CATEGORIES = {"image_api": "이미지 API", "subscription": "구독·툴", "ads": "광고비",
                   "outsourcing": "외주", "props": "소품·샘플", "other": "기타"}
# 엑셀에서 한글로 적어도 읽히게
ALIASES = {
    "type": {"협찬": "sponsorship", "광고": "sponsorship", "게시비": "sponsorship", "제작": "production",
             "제작비": "production", "사용권": "usage_rights", "제휴": "affiliate", "현물": "gifted", "기타": "other"},
    "status": {"계약": "contracted", "청구": "invoiced", "입금": "paid", "취소": "cancelled", "canceled": "cancelled"},
    "category": {"이미지": "image_api", "구독": "subscription", "광고": "ads", "광고비": "ads",
                 "외주": "outsourcing", "소품": "props", "기타": "other"},
}

MIN_POSTS = 3          # 상위·하위 판정에 필요한 최소 게시물 수
MIN_GROUP = 2          # 시리즈·기둥 추천에 필요한 그룹당 최소 게시물 수
TOP_RATIO, BOTTOM_RATIO = 1.3, 0.7   # 계정 중앙값 대비 배수
UNSET = "미지정"


# ── 기본 도구 ─────────────────────────────────────────────

def _today() -> date:
    return datetime.now(KST).date()


def _num(value):
    """'1,234' → 1234, '38.5%' → 38.5, '₩12,000' → 12000. 빈 칸·숫자가 아니면 None."""
    if value is None:
        return None
    s = re.sub(r"[,\s%₩원$]", "", str(value))
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    if not math.isfinite(f):
        return None
    return int(f) if f.is_integer() else f


def _parse_date(value: str) -> date | None:
    """'2026-10-05', '2026-10-05T08:00+09:00', 엑셀이 바꿔 놓는 '2026. 10. 5.' · '2026/10/05' 를 읽는다."""
    m = DATE_RE.match(str(value).strip())
    try:
        return date(*map(int, m.groups())) if m else None
    except ValueError:
        return None


def _j(word: str, pair: str) -> str:
    """받침에 맞춰 조사 붙이기: _j('시리즈', '이가') → '시리즈가', _j('콘텐츠 기둥', '이가') → '콘텐츠 기둥이'."""
    ch = word[-1:] or " "
    final = "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 != 0
    return word + (pair[0] if final else pair[1])


def _ratio(num, den):
    return num / den if num is not None and den else None


def _median(values):
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def tracking_dir(data_dir=None) -> Path:
    """data_dir > DOHA_TRACKING_DIR(테스트용, imagegen 과 같은 규칙) > config.paths.tracking."""
    if data_dir:
        return Path(data_dir)
    env = os.environ.get("DOHA_TRACKING_DIR")
    return Path(env) if env else ROOT / load_config()["paths"]["tracking"]


def _read_rows(path: Path) -> list[dict]:
    """CSV → [{열: 문자열}]. 엑셀이 붙이는 BOM, CP949 저장본도 읽는다. `_line` 은 파일의 줄 번호."""
    if not path.exists():
        return []
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp949", errors="replace")
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    for record in reader:
        row = {k.lstrip("\ufeff").strip(): (v.strip() if isinstance(v, str) else "")
               for k, v in record.items() if k}
        if not any(row.values()):
            continue
        row["_line"] = reader.line_num
        rows.append(row)
    return rows


def _file_warnings(folder: Path) -> list[str]:
    out = []
    for name, columns in SCHEMAS.items():
        path = folder / name
        if not path.exists():
            out.append(f"{name}: 파일이 없어요 (헤더만 있는 빈 파일이라도 두세요).")
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            out.append(f"{name}: UTF-8 이 아니에요(엑셀 기본 CSV?). 'CSV UTF-8' 로 다시 저장하세요.")
            text = raw.decode("cp949", errors="replace")
        header = next(csv.reader(io.StringIO(text)), [])
        missing = [c for c in columns if c not in [h.lstrip("\ufeff").strip() for h in header]]
        if missing:
            out.append(f"{name}: 열이 없어요 → {', '.join(missing)} (열 이름은 바꾸지 마세요).")
    return out


def _lines(nums: list[int], limit: int = 6) -> str:
    shown = ", ".join(str(n) for n in nums[:limit])
    return f"{shown} 외 {len(nums) - limit}줄" if len(nums) > limit else shown


# ── 데이터 읽기 ───────────────────────────────────────────

def posts_dir(data_dir=None) -> Path:
    if data_dir and (Path(data_dir) / "posts").is_dir():
        return Path(data_dir) / "posts"
    return ROOT / load_config()["paths"]["posts"]


def _load_post_meta(data_dir=None) -> tuple[dict[str, dict], list[str]]:
    meta: dict[str, dict] = {}
    errors: list[str] = []
    root = posts_dir(data_dir)
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        path = d / "post.yaml"
        if not path.is_file():
            continue
        try:
            data = load_yaml(path) or {}
        except yaml.YAMLError as e:
            errors.append(f"{d.name}/post.yaml 을 읽지 못했어요: {str(e).splitlines()[0]}")
            continue
        if not isinstance(data, dict):
            continue
        disc = data.get("disclosure") or {}
        pid = str(data.get("id") or d.name)
        meta[pid] = {
            "post_id": pid,
            "date": str(data.get("date") or ""),
            "series": str(data.get("series") or "").strip(),
            "pillar": str(data.get("pillar") or "").strip(),
            "format": str(data.get("format") or "").strip().lower(),
            "goal": str(data.get("goal") or "").strip().lower(),
            "hook": " ".join(str(data.get("hook") or "").split()),
            "paid": bool(disc.get("paid")),
            "gifted": bool(disc.get("gifted")),
            "affiliate": bool(disc.get("affiliate")),
            "brand": str(disc.get("brand") or ""),
        }
        if d.name != pid:  # 폴더 이름으로 적어도 찾게
            meta.setdefault(d.name, meta[pid])
    return meta, errors


def load_post_meta(data_dir=None) -> dict[str, dict]:
    """post_id → post.yaml 의 분석용 필드 (date, series, pillar, format, goal, hook, paid/gifted/affiliate, brand)."""
    return _load_post_meta(data_dir)[0]


def load_metrics(data_dir=None) -> list[dict]:
    """tracking/metrics.csv → 행 목록.

    숫자 열(reach, views, … completion_rate)은 int/float, 빈 칸은 None.
    checkpoint·format 은 소문자. `_line` 은 CSV 줄 번호, `_invalid` 는 숫자로 못 읽은 열 이름.
    """
    rows = []
    for row in _read_rows(tracking_dir(data_dir) / "metrics.csv"):
        invalid = []
        for col in COUNT_COLS + FLOAT_COLS:
            text = row.get(col, "")
            row[col] = _num(text)
            if row[col] is None and text:
                invalid.append(col)
        row["checkpoint"] = row.get("checkpoint", "").lower()
        row["format"] = row.get("format", "").lower()
        row["post_id"] = row.get("post_id", "")
        row["_invalid"] = invalid
        rows.append(row)
    return rows


def _normalize(kind: str, value: str) -> str:
    v = (value or "").strip()
    return ALIASES[kind].get(v, v.lower())


def load_revenue(data_dir=None) -> list[dict]:
    """revenue.csv → 행 목록. net 은 net_krw, 없으면 gross_krw − withholding_krw(빈 칸은 0)."""
    rows = []
    for row in _read_rows(tracking_dir(data_dir) / "revenue.csv"):
        gross, wh, net = (_num(row.get(c)) for c in ("gross_krw", "withholding_krw", "net_krw"))
        if net is None and gross is not None:
            net = gross - (wh or 0)
        d = _parse_date(row.get("date", ""))
        rows.append({**row, "date": d.isoformat() if d else "", "_date_raw": row.get("date", ""),
                     "type": _normalize("type", row.get("type", "")),
                     "status": _normalize("status", row.get("status", "")),
                     "gross": gross, "withholding": wh, "net": net})
    return rows


def load_costs(data_dir=None, config: dict | None = None) -> list[dict]:
    """costs.csv → 행 목록. krw 는 amount_krw, 없으면 amount_usd × config.fx.usd_krw (krw_source='fx')."""
    config = config or load_config()
    fx = float((config.get("fx") or {}).get("usd_krw") or 0)
    rows = []
    for row in _read_rows(tracking_dir(data_dir) / "costs.csv"):
        usd, krw = _num(row.get("amount_usd")), _num(row.get("amount_krw"))
        source = "krw" if krw is not None else None
        if krw is None and usd is not None and fx:
            krw, source = round(usd * fx), "fx"
        d = _parse_date(row.get("date", ""))
        rows.append({**row, "date": d.isoformat() if d else "", "_date_raw": row.get("date", ""),
                     "category": _normalize("category", row.get("category", "")),
                     "usd": usd, "krw": krw, "krw_source": source})
    return rows


# ── 게시물 성과 ───────────────────────────────────────────

def _media_format(row_format: str, meta_format: str) -> str:
    if row_format in FORMAT_KO:
        return row_format
    return meta_format if meta_format in FORMAT_KO else ""


def post_rates(metrics: list[dict] | None = None, meta: dict | None = None, *, data_dir=None,
               prefer: tuple[str, ...] = CHECKPOINT_PREF) -> list[dict]:
    """게시물별 대표 기록과 비율. 카드뉴스와 릴스는 (post_id, format) 으로 따로 센다.

    - 대표 기록: prefer 순서(7d → 24h → 30d)에서 reach 가 있는 첫 시점. 같은 (post_id, checkpoint, format)
      이 여러 줄이면 CSV 아래쪽 줄을 쓴다.
    - 비율 = 지표 ÷ reach: save_rate, share_rate, follow_rate, profile_rate, click_rate,
      engagement_rate(좋아요+댓글+저장+공유). reach 가 없으면 None.
    - 도달 있는 게시물이 3개 이상이면 각 게시물의 goal 지표(post.yaml goal, 기본 save)를 계정 중앙값과 비교해
      goal_index(배수), goal_baseline(비교한 중앙값), flag('top' ≥1.3배 / 'bottom' ≤0.7배 / '')를 단다.
      중앙값은 같은 형식 게시물이 3개 이상이면 그 형식끼리 (릴스는 저장률이 원래 낮아서),
      도달(goal=reach)은 같은 형식·같은 시점끼리 3개 이상일 때만 비교한다.
    """
    metrics = load_metrics(data_dir) if metrics is None else metrics
    meta = load_post_meta(data_dir) if meta is None else meta
    grouped: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in metrics:
        if row.get("checkpoint") not in prefer or not row.get("post_id"):
            continue
        m = meta.get(row["post_id"], {})
        grouped[(row["post_id"], _media_format(row.get("format", ""), m.get("format", "")))][row["checkpoint"]] = row

    out = []
    for (pid, fmt), by_cp in grouped.items():
        usable = [by_cp[c] for c in prefer if c in by_cp and by_cp[c].get("reach")]
        row = usable[0] if usable else next(by_cp[c] for c in prefer if c in by_cp)
        m = meta.get(pid, {})
        goal = m.get("goal") if m.get("goal") in GOAL_METRIC else "save"
        item = {
            "post_id": pid, "known": pid in meta, "format": fmt, "format_ko": FORMAT_KO.get(fmt, UNSET),
            "checkpoint": row["checkpoint"], "recorded_at": row.get("recorded_at", ""),
            "checkpoints": [c for c in prefer if c in by_cp],
            "date": m.get("date", ""), "series": m.get("series", ""), "pillar": m.get("pillar", ""),
            "goal": goal, "hook": m.get("hook", ""),
        }
        for col in COUNT_COLS + FLOAT_COLS:
            item[col] = row.get(col)
        parts = [row.get(c) for c in ENGAGEMENT_COLS if row.get(c) is not None]
        item["engagement"] = sum(parts) if parts else None
        for name, (col, _) in RATES.items():
            item[name] = _ratio(item[col], item["reach"])
        out.append(item)

    _flag(out)
    out.sort(key=lambda r: (r["date"] or r["recorded_at"][:10] or "9999", r["post_id"], r["format"]))
    return out


def _baseline(r: dict, rated: list[dict], metric: str):
    pool = [x for x in rated if x[metric] is not None]
    same = [x for x in pool if x["format"] == r["format"]]
    if metric == "reach":  # 도달은 형식·시점마다 수준이 달라 같은 조건끼리만
        pool = [x for x in same if x["checkpoint"] == r["checkpoint"]]
    elif len(same) >= MIN_POSTS:
        pool = same
    return _median(x[metric] for x in pool) if len(pool) >= MIN_POSTS else None


def _flag(rows: list[dict]) -> None:
    for r in rows:
        r["goal_metric"] = GOAL_METRIC[r["goal"]]
        r["goal_index"], r["goal_baseline"], r["flag"] = None, None, ""
    rated = [r for r in rows if r["reach"]]
    if len(rated) < MIN_POSTS:
        return
    for r in rated:
        value, base = r[r["goal_metric"]], _baseline(r, rated, r["goal_metric"])
        if value is None or not base:
            continue
        r["goal_index"], r["goal_baseline"] = round(value / base, 2), base
        r["flag"] = "top" if r["goal_index"] >= TOP_RATIO else "bottom" if r["goal_index"] <= BOTTOM_RATIO else ""


def _stats(name: str, rows: list[dict]) -> dict:
    rated = [r for r in rows if r["reach"]]
    out = {"name": name, "n": len(rows), "n_posts": len({r["post_id"] for r in rows}), "n_rated": len(rated),
           "reach": _median(r["reach"] for r in rated)}
    for rate in RATES:
        out[rate] = _median(r[rate] for r in rated)
    return out


def group_stats(rows: list[dict], field: str) -> list[dict]:
    """field(series·pillar·format_ko)별 n(카드뉴스·릴스 따로 센 수), n_posts(post_id 수), 도달·비율 중앙값.

    빈 값은 '미지정'(맨 뒤). 형식이 섞이면 릴스 쪽 저장률이 낮게 끌어내리므로, 추천은 형식별로 나눠 쓴다.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r.get(field) or UNSET].append(r)
    return sorted((_stats(k, v) for k, v in groups.items()), key=lambda g: (g["name"] == UNSET, -g["n"], g["name"]))


def recommend(groups: list[dict], overall: dict, dim_ko: str, metric: str = "save_rate", scope: str = "") -> str:
    """게시물 2개 이상인 그룹이 둘 이상일 때만 '비중을 늘리세요'. 아니면 실험을 제안한다.

    groups·overall 은 한 형식(scope, 예: '카드뉴스')의 게시물로 만든 것을 넘긴다.
    """
    named = [g for g in groups if g["name"] != UNSET]
    eligible = [g for g in named if g["n_rated"] >= MIN_GROUP and g[metric] is not None]
    label = METRIC_KO[metric]
    where = f"{scope} " if scope else ""
    if not named:
        return f"{dim_ko} 정보가 있는 {where}기록이 아직 없어요."
    if len(eligible) >= 2 and overall.get(metric):
        best = max(eligible, key=lambda g: g[metric])
        if best[metric] > overall[metric]:
            return (f"다음 2주는 {best['name']} 비중을 늘리세요 ({where}{label} 중앙값 {_pct(best[metric])} vs 전체 "
                    f"{_pct(overall[metric])}, 게시물 {best['n_rated']}개 — 표본이 작으니 2주 뒤 다시 확인).")
        return (f"{where}전체보다 {_j(label, '이가')} 뚜렷이 높은 {_j(dim_ko, '이가')} 아직 없어요. "
                "지금 비중을 유지하고 기록을 더 모으세요.")
    if len(named) == 1:
        return (f"{where}{_j(dim_ko, '이가')} '{named[0]['name']}' 하나뿐이라 비교할 수 없어요. "
                f"실험: 다음 2주에 새 {dim_ko} 하나를 {where}2편 이상 올려 {_j(label, '을를')} 비교하세요.")
    thin = [g["name"] for g in named if g["n_rated"] < MIN_GROUP]
    return (f"{dim_ko}마다 {where}게시물이 2개 이상 있어야 비교할 수 있어요. 실험: 다음 2주에 "
            f"{_j(', '.join(thin[:3]), '을를')} 각각 {where}2편 이상 올려 {_j(label, '을를')} 비교하세요.")


def growth(metrics: list[dict], meta: dict) -> list[dict]:
    """24h 와 7d 기록이 모두 있는 게시물의 7d ÷ 24h 배수 (도달·조회·저장)."""
    pairs: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in metrics:
        if row.get("checkpoint") in ("24h", "7d") and row.get("post_id"):
            fmt = _media_format(row.get("format", ""), meta.get(row["post_id"], {}).get("format", ""))
            pairs[(row["post_id"], fmt)][row["checkpoint"]] = row
    out = []
    for (pid, fmt), cps in sorted(pairs.items()):
        a, b = cps.get("24h"), cps.get("7d")
        if not a or not b:
            continue
        item = {"post_id": pid, "format": fmt, "format_ko": FORMAT_KO.get(fmt, UNSET)}
        for col in ("reach", "views", "saves"):
            item[f"{col}_24h"], item[f"{col}_7d"] = a.get(col), b.get(col)
            item[f"{col}_x"] = _ratio(b.get(col), a.get(col))
        if item["reach_x"] is not None or item["views_x"] is not None:
            out.append(item)
    return out


def followers_trend(data_dir=None, month: str | None = None) -> dict:
    """followers.csv → 날짜순 기록과 변화. 같은 날 여러 줄이면 아래쪽 값. 빈 칸 줄은 blank_rows 로만 센다."""
    points: dict[date, int] = {}
    blank, invalid = 0, []
    for row in sorted(_read_rows(tracking_dir(data_dir) / "followers.csv"),
                      key=lambda r: r.get("date", "")):
        n, d = _num(row.get("followers")), _parse_date(row.get("date", ""))
        if n is None:
            if row.get("followers"):
                invalid.append(row["_line"])
            else:
                blank += 1
            continue
        if d is None:
            invalid.append(row["_line"])
            continue
        points[d] = int(n)
    series, prev = [], None
    for d in sorted(points):
        series.append({"date": d.isoformat(), "followers": points[d],
                       "change": None if prev is None else points[d] - prev})
        prev = points[d]
    out = {"points": series, "blank_rows": blank, "invalid_lines": invalid, "latest": None, "latest_date": None,
           "first": None, "first_date": None, "change": None, "days": None, "per_week": None, "month_change": None}
    if not series:
        return out
    first, last = series[0], series[-1]
    days = (date.fromisoformat(last["date"]) - date.fromisoformat(first["date"])).days
    out.update(latest=last["followers"], latest_date=last["date"], first=first["followers"],
               first_date=first["date"], change=last["followers"] - first["followers"], days=days,
               per_week=round((last["followers"] - first["followers"]) / days * 7, 1) if days >= 7 else None)
    if month:
        inside = [p for p in series if p["date"][:7] == month]
        before = [p for p in series if p["date"][:7] < month]
        start = before[-1] if before else (inside[0] if inside else None)
        if inside and start is not inside[-1]:
            out["month_change"] = inside[-1]["followers"] - start["followers"]
    return out


# ── 돈 ────────────────────────────────────────────────────

def _month_end(month: str) -> str:
    y, m = map(int, month.split("-"))
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return (nxt - timedelta(days=1)).isoformat()


def money(month: str, revenue: list[dict], costs: list[dict], config: dict) -> dict:
    """한 달의 실현 수익(입금 완료)·파이프라인·비용·순이익·목표 진행률.

    순이익 = 실현 수익(입금액 기준) − 비용. 현물 협찬(type=gifted)은 현금이 아니라 따로 보여주고 빼고 계산.
    파이프라인은 그 달 말까지 계약·청구됐지만 아직 입금 안 된 건 전부(이전 달 포함).
    """
    goal = int((config.get("account") or {}).get("goal_monthly_net_krw") or 0)
    end = _month_end(month)
    in_month = [r for r in revenue if r["date"][:7] == month]
    realized = [r for r in in_month if r["status"] == "paid" and r["type"] != "gifted"]
    by_type: dict[str, dict] = {}
    for r in realized:
        t = by_type.setdefault(r["type"] or "other", {"label": REVENUE_TYPES.get(r["type"], r["type"] or "기타"),
                                                     "n": 0, "gross": 0, "withholding": 0, "net": 0})
        t["n"] += 1
        t["gross"] += r["gross"] or 0
        t["withholding"] += r["withholding"] or 0
        t["net"] += r["net"] or 0
    pipeline = [{"date": r["date"], "brand": r.get("brand", ""), "type": r["type"],
                 "type_ko": REVENUE_TYPES.get(r["type"], r["type"]), "status": r["status"],
                 "status_ko": REVENUE_STATUS[r["status"]], "post_id": r.get("post_id", ""),
                 "gross": r["gross"], "net": r["net"]}
                for r in revenue
                if r["status"] in ("contracted", "invoiced") and r["type"] != "gifted" and r["date"] <= end]
    gifted = [{"date": r["date"], "brand": r.get("brand", ""), "gross": r["gross"], "post_id": r.get("post_id", "")}
              for r in in_month if r["type"] == "gifted" and r["status"] != "cancelled"]

    month_costs = [c for c in costs if c["date"][:7] == month]
    by_cat: dict[str, dict] = {}
    for c in month_costs:
        if c["krw"] is None:
            continue
        k = c["category"] or "other"
        b = by_cat.setdefault(k, {"label": COST_CATEGORIES.get(k, k or "기타"), "n": 0, "krw": 0, "usd": 0.0,
                                  "fx_rows": 0})
        b["n"] += 1
        b["krw"] += c["krw"]
        b["usd"] += c["usd"] or 0
        b["fx_rows"] += c["krw_source"] == "fx"

    realized_net = sum(t["net"] for t in by_type.values())
    costs_total = sum(b["krw"] for b in by_cat.values())
    net = realized_net - costs_total
    return {
        "month": month,
        "realized_by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1]["net"])),
        "realized_gross_krw": sum(t["gross"] for t in by_type.values()),
        "withholding_krw": sum(t["withholding"] for t in by_type.values()),
        "realized_net_krw": realized_net,
        "pipeline": sorted(pipeline, key=lambda p: p["date"]),
        "pipeline_gross_krw": sum(p["gross"] or 0 for p in pipeline),
        "gifted": gifted,
        "cancelled": sum(1 for r in in_month if r["status"] == "cancelled"),
        "costs_by_category": dict(sorted(by_cat.items(), key=lambda kv: -kv[1]["krw"])),
        "costs_krw": costs_total,
        "costs_fx_rows": sum(b["fx_rows"] for b in by_cat.values()),
        "fx_usd_krw": float((config.get("fx") or {}).get("usd_krw") or 0),
        "net_krw": net,
        "goal_krw": goal,
        "progress": net / goal if goal else None,
    }


def unit_economics(revenue: list[dict], costs: list[dict], rates: list[dict]) -> dict:
    """전체 기간 기준: 게시물당 직접비(costs.post_id), 협찬 게시물의 도달 1,000당 수익(취소 제외 계약 총액)."""
    per_post: dict[str, int] = defaultdict(int)
    for c in costs:
        if c.get("post_id") and c["krw"] is not None:
            per_post[c["post_id"]] += c["krw"]
    cost_items = sorted(({"post_id": k, "krw": v} for k, v in per_post.items()), key=lambda i: -i["krw"])

    reach_by_post: dict[str, int] = defaultdict(int)
    for r in rates:
        reach_by_post[r["post_id"]] += r["reach"] or 0
    deal: dict[str, int] = defaultdict(int)
    for r in revenue:
        amount = r["gross"] if r["gross"] is not None else r["net"]
        if r.get("post_id") and r["status"] in ("contracted", "invoiced", "paid") and r["type"] != "gifted" and amount:
            deal[r["post_id"]] += amount
    sponsored = [{"post_id": pid, "revenue_krw": amt, "reach": reach_by_post.get(pid) or None,
                  "per_1k_reach_krw": round(amt / reach_by_post[pid] * 1000) if reach_by_post.get(pid) else None}
                 for pid, amt in sorted(deal.items(), key=lambda kv: -kv[1])]
    return {
        "cost_per_post": cost_items,
        "avg_cost_per_post_krw": round(statistics.mean(i["krw"] for i in cost_items)) if cost_items else None,
        "sponsored": sponsored,
    }


# ── 데이터 점검 ───────────────────────────────────────────

def quality_warnings(metrics: list[dict], meta: dict, revenue: list[dict], costs: list[dict],
                     followers: dict, folder: Path, meta_errors: list[str] | None = None) -> list[str]:
    """사람이 고칠 수 있는 문제만 한국어 한 줄씩."""
    out = _file_warnings(folder) + list(meta_errors or [])

    unknown: dict[str, list[int]] = defaultdict(list)
    no_reach, bad_cp, both_blank = [], [], []
    seen: dict[tuple, list[int]] = defaultdict(list)
    for r in metrics:
        pid = r.get("post_id", "")
        if not pid:
            out.append(f"metrics.csv {r['_line']}줄: post_id 가 비어 있어요.")
            continue
        if pid not in meta:
            unknown[pid].append(r["_line"])
        if r["reach"] is None and "reach" not in r["_invalid"]:
            no_reach.append(r["_line"])
        if r["checkpoint"] not in CHECKPOINT_PREF:
            bad_cp.append(r["_line"])
        if not r["format"] and meta.get(pid, {}).get("format") == "both":
            both_blank.append(r["_line"])
        if r["_invalid"]:
            out.append(f"metrics.csv {r['_line']}줄: 숫자가 아닌 값 → {', '.join(r['_invalid'])}")
        seen[(pid, r["checkpoint"], r["format"])].append(r["_line"])
    if unknown:
        ids = ", ".join(f"{k}({_lines(v, 3)}줄)" for k, v in list(unknown.items())[:5])
        ids += f" 외 {len(unknown) - 5}개" if len(unknown) > 5 else ""
        out.append(f"metrics.csv: post.yaml 에 없는 post_id {len(unknown)}개 → {ids}. 분석에는 넣고 시리즈·기둥은 "
                   f"'{UNSET}'. 오타면 고치고, post.yaml 이 없는 옛 게시물(ig:숏코드)이면 그대로 둬도 돼요.")
    if no_reach:
        out.append(f"metrics.csv {_lines(no_reach)}줄: reach(도달)가 비어 있어 비율을 계산하지 못했어요.")
    if bad_cp:
        out.append(f"metrics.csv {_lines(bad_cp)}줄: checkpoint 는 24h·7d·30d 중 하나여야 해요 (분석에서 뺐어요).")
    if both_blank:
        out.append(f"metrics.csv {_lines(both_blank)}줄: format=both 게시물은 carousel·reel 을 나눠 적어 주세요.")
    for (pid, cp, fmt), lines in seen.items():
        if len(lines) > 1:
            out.append(f"metrics.csv: {pid} {cp}{' ' + fmt if fmt else ''} 기록이 {len(lines)}번 있어요"
                       f"({_lines(lines)}줄). 마지막 줄을 썼어요 — 나머지는 지우세요.")

    for r in revenue:
        where = f"revenue.csv {r['_line']}줄"
        if r["status"] not in REVENUE_STATUS:
            out.append(f"{where}: status '{r['status']}' 를 모르겠어요 (contracted·invoiced·paid·cancelled).")
        if r["gross"] is None and r["net"] is None:
            out.append(f"{where}: gross_krw·net_krw 가 모두 비어 있어요.")
        if not r["date"]:
            out.append(f"{where}: date 가 비었거나 YYYY-MM-DD 형식이 아니에요 ('{r['_date_raw']}').")
        if r.get("post_id") and r["post_id"] not in meta and not r["post_id"].startswith("ig:"):
            out.append(f"{where}: post_id '{r['post_id']}' 게시물을 찾지 못했어요.")
    paid_ids = {r.get("post_id") for r in revenue}
    for pid, m in meta.items():
        if m["paid"] and pid == m["post_id"] and pid not in paid_ids:
            out.append(f"{pid}: post.yaml 은 광고(paid)인데 revenue.csv 에 이 post_id 줄이 없어요.")

    for c in costs:
        where = f"costs.csv {c['_line']}줄"
        if c["krw"] is None:
            out.append(f"{where}: amount_krw·amount_usd 가 모두 비어 있어요.")
        if not c["date"]:
            out.append(f"{where}: date 가 비었거나 YYYY-MM-DD 형식이 아니에요 ('{c['_date_raw']}').")

    if followers["invalid_lines"]:
        out.append(f"followers.csv {_lines(followers['invalid_lines'])}줄: 날짜나 팔로워 수를 읽지 못했어요.")
    if followers["blank_rows"]:
        out.append(f"followers.csv: 팔로워 수가 빈 줄 {followers['blank_rows']}개 — 앱에서 확인해 채우세요.")
    return out


# ── 전체 요약 ─────────────────────────────────────────────

def summarize(month: str | None = None, data_dir=None, today: date | None = None) -> dict:
    """리포트의 모든 값 (JSON 직렬화 가능). 미디어킷·운영 보드가 이걸 읽는다.

    주요 키:
      posts            post_rates() 결과 (게시물별 대표 기록·비율·flag)
      overall          전체 게시물 수와 도달·비율 중앙값 (n, reach, save_rate, share_rate, …)
      by_series / by_pillar / by_format   group_stats() 결과 (형식 섞음 — 간단한 표시용)
      by_series_format / by_pillar_format {"carousel": [...], "reel": [...]} 형식별 group_stats()
      overall_by_format                   {"carousel": {...}, "reel": {...}}
      recommendations  {"series": {"carousel": 문장, "reel": 문장}, "pillar": {...}}
                       카드뉴스는 저장률, 릴스는 공유율로 비교
      growth           24h→7d 배수 목록, growth_median_reach_x
      followers        followers_trend() 결과 (latest, change, points …)
      money            그 달 수익·비용·순이익·목표 진행률 — 내부용, 미디어킷에 넣지 말 것
      unit_economics   게시물당 직접비, 협찬 게시물 도달 1,000당 수익
      warnings         데이터 점검 문장 목록
    """
    today = today or _today()
    month = month or today.strftime("%Y-%m")
    config = load_config()
    folder = tracking_dir(data_dir)
    meta, meta_errors = _load_post_meta(data_dir)
    metrics = load_metrics(data_dir)
    revenue = load_revenue(data_dir)
    costs = load_costs(data_dir, config)
    rates = post_rates(metrics, meta)
    followers = followers_trend(data_dir, month)
    grow = growth(metrics, meta)
    overall = _stats("전체", rates)
    # 형식별로 나눠 비교: 카드뉴스는 저장률, 릴스는 공유율(발견·전송이 역할)
    per_format = {f: [r for r in rates if r["format"] == f] for f in FORMAT_KO}
    per_format = {f: rows for f, rows in per_format.items() if rows}
    rec_metric = {"carousel": "save_rate", "reel": "share_rate"}
    grouped = {dim: {f: group_stats(rows, dim) for f, rows in per_format.items()} for dim in ("series", "pillar")}
    overall_by_format = {f: _stats(f"전체 ({FORMAT_KO[f]})", rows) for f, rows in per_format.items()}
    recs = {dim: {f: recommend(grouped[dim][f], overall_by_format[f], dim_ko, rec_metric[f], FORMAT_KO[f])
                  for f in per_format}
            for dim, dim_ko in (("series", "시리즈"), ("pillar", "콘텐츠 기둥"))}
    try:
        data_label = str(folder.resolve().relative_to(ROOT)) + "/"
    except ValueError:
        data_label = str(folder)
    return {
        "generated_at": datetime.now(KST).isoformat(timespec="minutes"),
        "date": today.isoformat(),
        "month": month,
        "data_dir": data_label,
        "posts": rates,
        "checkpoint_counts": {cp: sum(1 for r in rates if r["checkpoint"] == cp) for cp in CHECKPOINT_PREF},
        "enough_posts": len([r for r in rates if r["reach"]]) >= MIN_POSTS,
        "overall": overall,
        "by_series": group_stats(rates, "series"),
        "by_pillar": group_stats(rates, "pillar"),
        "by_format": group_stats(rates, "format_ko"),
        "by_series_format": grouped["series"],
        "by_pillar_format": grouped["pillar"],
        "overall_by_format": overall_by_format,
        "recommendations": recs,
        "growth": grow,
        "growth_median_reach_x": _median(g["reach_x"] for g in grow),
        "followers": followers,
        "money": money(month, revenue, costs, config),
        "unit_economics": unit_economics(revenue, costs, rates),
        "warnings": quality_warnings(metrics, meta, revenue, costs, followers, folder, meta_errors),
    }


# ── 출력 ──────────────────────────────────────────────────

def _pct(v) -> str:
    if v is None:
        return "–"
    if v == 0:
        return "0%"
    return f"{v * 100:.2f}%" if abs(v) < 0.01 else f"{v * 100:.1f}%"


def _int(v) -> str:
    return "–" if v is None else f"{round(v):,}"


def _krw(v) -> str:
    return "–" if v is None else f"{round(v):,}원"


def _x(v) -> str:
    return "–" if v is None else f"{v:.1f}배"


def _cell(v) -> str:
    return str(v).replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return lines


def _bar(ratio, width: int = 20) -> str:
    filled = round(max(0.0, min(1.0, ratio or 0.0)) * width)
    return "█" * filled + "░" * (width - filled)


def _spark(values: list[int]) -> str:
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    ticks = "▁▂▃▄▅▆▇█"
    return "".join(ticks[0 if hi == lo else round((v - lo) / (hi - lo) * 7)] for v in values)


def _verdict(r: dict) -> str:
    if r["goal_index"] is None:
        return "–"
    mark = {"top": "▲ ", "bottom": "▼ "}.get(r["flag"], "")
    return f"{mark}{METRIC_KO[r['goal_metric']]} {r['goal_index']:.1f}배"


def _label(r: dict) -> str:
    return f"{r['post_id']} ({r['format_ko']})"


def render_markdown(s: dict) -> str:
    m, f, ue = s["money"], s["followers"], s["unit_economics"]
    rated = [r for r in s["posts"] if r["reach"]]
    L: list[str] = [f"# 도하 성과 리포트 — {s['month']}", "",
                    f"생성 {s['generated_at'][:16].replace('T', ' ')} KST · 데이터 `{s['data_dir']}` · "
                    f"성과는 기록된 전체 게시물, 돈은 {s['month']} 기준", ""]

    # 요약
    L.append("## 요약")
    L.append("")
    cc = s["checkpoint_counts"]
    if rated:
        L.append(f"- 게시물 {len(s['posts'])}개 분석 (7d {cc['7d']} · 24h {cc['24h']} · 30d {cc['30d']}). "
                 f"저장률 중앙값 {_pct(s['overall']['save_rate'])}, 공유율 {_pct(s['overall']['share_rate'])}, "
                 f"도달 중앙값 {_int(s['overall']['reach'])}")
    elif s["posts"]:
        L.append(f"- 게시물 {len(s['posts'])}개 기록이 있지만 reach(도달)가 비어 있어 비율을 계산하지 못했어요.")
    else:
        L.append("- 아직 분석할 성과 기록이 없어요. 게시 24시간·7일 뒤 `tracking/metrics.csv` 에 기록하세요 "
                 "(`tracking/README.md`, 토큰이 있으면 `python doha.py insights`).")
    if f["latest"] is not None:
        change = f" ({f['change']:+,}명, {f['first_date']}부터)" if f["days"] else ""
        L.append(f"- 팔로워 {f['latest']:,}명{change}")
    L.append(f"- {s['month']} 순이익 {_krw(m['net_krw'])} = 실현 수익 {_krw(m['realized_net_krw'])} − 비용 "
             f"{_krw(m['costs_krw'])} · 목표 대비 {_pct(m['progress'])}")
    if m["pipeline"]:
        L.append(f"- 미입금 파이프라인 {len(m['pipeline'])}건 {_krw(m['pipeline_gross_krw'])} (실현 수익에 넣지 않음)")
    L.append(f"- 데이터 점검 {len(s['warnings'])}건" + (" — 7장 확인" if s["warnings"] else ""))
    L.append("")

    # 1. 게시물별
    L += ["## 1. 게시물별 성과", "",
          "7d 기록을 우선 쓰고 없으면 24h. 비율 = 지표 ÷ 도달. 참여 = 좋아요+댓글+저장+공유. "
          "판정은 게시물 목표 지표(post.yaml `goal`)를 계정 중앙값과 비교한 배수 (▲ 1.3배 이상, ▼ 0.7배 이하). "
          "같은 형식이 3개 이상이면 그 형식끼리 비교하고, 도달 목표는 같은 형식·시점끼리만 비교해요.", ""]
    if s["posts"]:
        L += _table(["게시물", "형식", "시점", "도달", "조회", "저장률", "공유율", "팔로우율", "프로필 방문율", "참여율", "판정"],
                    [[r["post_id"], r["format_ko"], r["checkpoint"], _int(r["reach"]), _int(r["views"]),
                      _pct(r["save_rate"]), _pct(r["share_rate"]), _pct(r["follow_rate"]), _pct(r["profile_rate"]),
                      _pct(r["engagement_rate"]), _verdict(r)] for r in s["posts"]])
        L.append("")
        if any(r["checkpoint"] == "24h" for r in rated) and any(r["checkpoint"] != "24h" for r in rated):
            L += ["24h 기록만 있는 게시물은 도달이 낮게 보여요. 비율은 비교적 안정적이지만 7일 뒤 다시 보세요.", ""]
        reels = [r for r in s["posts"] if r["format"] == "reel" and (r["avg_watch_sec"] or r["completion_rate"])]
        if reels:
            L += ["릴스 시청", ""]
            L += _table(["게시물", "평균 시청(초)", "완료율"],
                        [[r["post_id"], r["avg_watch_sec"] if r["avg_watch_sec"] is not None else "–",
                          f"{r['completion_rate']}%" if r["completion_rate"] is not None else "–"] for r in reels])
            L.append("")
        if not s["enough_posts"]:
            L += [f"**상위·하위 판정: 데이터 부족** — 도달이 기록된 게시물이 {MIN_POSTS}개 이상 필요해요 "
                  f"(지금 {len(rated)}개).", ""]
        else:
            flagged = sorted((r for r in rated if r["flag"]), key=lambda r: -r["goal_index"])
            L.append("**상위·하위** (목표 지표, 계정 중앙값 대비)")
            L.append("")
            for r in flagged:
                metric = r["goal_metric"]
                fmt = _int if metric == "reach" else _pct
                L.append(f"- {'▲' if r['flag'] == 'top' else '▼'} {_label(r)} — {METRIC_KO[metric]} {fmt(r[metric])} "
                         f"(중앙값 {fmt(r['goal_baseline'])}의 {r['goal_index']:.1f}배)"
                         + (f" · \"{r['hook']}\"" if r["hook"] else ""))
            if not flagged:
                L.append("- 중앙값에서 크게 벗어난 게시물이 없어요.")
            L.append("")
    else:
        L += ["기록 없음.", ""]

    # 2. 묶음별
    L += ["## 2. 시리즈·기둥·형식별", ""]
    if not s["posts"]:
        L += ["게시물 기록이 쌓이면 시리즈·기둥·형식별 비교와 다음 2주 추천이 여기에 나와요.", ""]
    else:
        L += ["도달이 기록된 게시물의 중앙값. 릴스는 저장률이 원래 낮아서 형식별로 나눠 비교해요 "
              "(추천: 카드뉴스는 저장률, 릴스는 공유율).", ""]
    for title, dim in (("시리즈", "series"), ("콘텐츠 기둥", "pillar")):
        per_format = s[f"by_{dim}_format"]
        if not per_format:
            continue
        rows = []
        for f_key, groups in per_format.items():
            for g in groups + [s["overall_by_format"][f_key]]:
                name = "전체" if g is s["overall_by_format"][f_key] else g["name"]
                rows.append([name, FORMAT_KO[f_key], g["n"], _int(g["reach"]), _pct(g["save_rate"]),
                             _pct(g["share_rate"]), _pct(g["follow_rate"]), _pct(g["engagement_rate"])])
        L += [f"### {title}", ""]
        L += _table([title, "형식", "n", "도달", "저장률", "공유율", "팔로우율", "참여율"], rows)
        L.append("")
        L += [f"- {FORMAT_KO[f_key]}: {text}" for f_key, text in s["recommendations"][dim].items()]
        L.append("")
    if s["by_format"]:
        L += ["### 형식", ""]
        L += _table(["형식", "n", "도달", "저장률", "공유율", "팔로우율", "참여율"],
                    [[g["name"], g["n"], _int(g["reach"]), _pct(g["save_rate"]), _pct(g["share_rate"]),
                      _pct(g["follow_rate"]), _pct(g["engagement_rate"])] for g in s["by_format"] + [s["overall"]]])
        L.append("")

    # 3. 성장
    L += ["## 3. 24시간 → 7일 성장", ""]
    if s["growth"]:
        L += _table(["게시물", "형식", "도달 24h", "도달 7d", "도달 배수", "조회 배수", "저장 배수"],
                    [[g["post_id"], g["format_ko"], _int(g["reach_24h"]), _int(g["reach_7d"]), _x(g["reach_x"]),
                      _x(g["views_x"]), _x(g["saves_x"])] for g in s["growth"]])
        if s["growth_median_reach_x"]:
            L += ["", f"도달 배수 중앙값 {_x(s['growth_median_reach_x'])} — 24h 도달에 이 값을 곱하면 7일 도달을 "
                      "대략 가늠할 수 있어요 (게시물이 쌓일수록 정확해져요)."]
        L.append("")
    else:
        L += ["24h 와 7d 를 모두 기록한 게시물이 아직 없어요.", ""]

    # 4. 팔로워
    L += ["## 4. 팔로워 추이", ""]
    if f["points"]:
        recent = f["points"][-10:]
        L.append(f"`{_spark([p['followers'] for p in f['points']])}` 최근 {f['latest']:,}명 ({f['latest_date']})")
        L.append("")
        if f["days"]:
            per_week = f" · 주당 {f['per_week']:+,}명" if f["per_week"] is not None else ""
            L.append(f"- {f['first_date']} → {f['latest_date']} ({f['days']}일): {f['change']:+,}명{per_week}")
        if f["month_change"] is not None:
            L.append(f"- {s['month']} 변화: {f['month_change']:+,}명")
        L.append("")
        L += _table(["날짜", "팔로워", "변화"],
                    [[p["date"], f"{p['followers']:,}", "–" if p["change"] is None else f"{p['change']:+,}"]
                     for p in recent])
        L.append("")
    else:
        L += ["팔로워 수 기록이 없어요. 주 1회(예: 월요일 아침) `tracking/followers.csv` 에 적으세요.", ""]

    # 5. 돈
    L += [f"## 5. 수익·비용 ({s['month']})", "", "### 실현 수익 (status=paid, 입금 완료)", ""]
    if m["realized_by_type"]:
        L += _table(["유형", "건수", "총액", "원천징수", "입금액"],
                    [[t["label"], t["n"], _krw(t["gross"]), _krw(t["withholding"]), _krw(t["net"])]
                     for t in m["realized_by_type"].values()]
                    + [["합계", sum(t["n"] for t in m["realized_by_type"].values()), _krw(m["realized_gross_krw"]),
                        _krw(m["withholding_krw"]), _krw(m["realized_net_krw"])]])
    else:
        L.append("이번 달 입금된 수익이 없어요.")
    L.append("")
    L += ["### 파이프라인 (계약·청구, 아직 입금 전 — 순이익에 넣지 않음)", ""]
    if m["pipeline"]:
        L += _table(["날짜", "브랜드", "유형", "상태", "총액", "예상 입금액"],
                    [[p["date"] or "–", p["brand"] or "–", p["type_ko"], p["status_ko"], _krw(p["gross"]),
                      _krw(p["net"])] for p in m["pipeline"]])
    else:
        L.append("없음.")
    L.append("")
    if m["gifted"]:
        L += [f"현물 협찬 {len(m['gifted'])}건 (참고 시가 합계 {_krw(sum(g['gross'] or 0 for g in m['gifted']))}) — "
              "현금이 아니라 순이익에서 뺐어요. 세무 처리는 세무사와 확인하세요.", ""]
    if m["cancelled"]:
        L += [f"취소 {m['cancelled']}건은 계산에서 뺐어요.", ""]
    L += ["### 비용", ""]
    if m["costs_by_category"]:
        L += _table(["분류", "건수", "금액", "USD 결제분"],
                    [[b["label"], b["n"], _krw(b["krw"]), f"${b['usd']:,.2f}" if b["usd"] else "–"]
                     for b in m["costs_by_category"].values()] + [["합계", "", _krw(m["costs_krw"]), ""]])
        if m["costs_fx_rows"]:
            L += ["", f"amount_krw 가 빈 {m['costs_fx_rows']}건은 config 환율 1달러 = {m['fx_usd_krw']:,.0f}원으로 "
                      "환산했어요. 카드 청구액이 나오면 amount_krw 를 채우세요."]
    else:
        L.append("이번 달 기록된 비용이 없어요.")
    L.append("")
    L += ["### 순이익과 목표", "",
          f"순이익 **{_krw(m['net_krw'])}** = 실현 수익(입금액) {_krw(m['realized_net_krw'])} − 비용 {_krw(m['costs_krw'])}",
          "", f"`{_bar(m['progress'])}` {_pct(m['progress'])} / 목표 {_krw(m['goal_krw'])}", "",
          "> 월 목표는 사용자가 정한 목표치이며 예측이나 보장된 수익이 아니에요. 순이익은 통장 기준"
          "(원천징수 후 입금액 − 비용)이고, 종합소득세 정산 전 금액이에요.", ""]

    # 6. 단위 경제
    L += ["## 6. 단위 경제 (전체 기간)", ""]
    if ue["cost_per_post"]:
        L.append(f"게시물당 직접비 평균 {_krw(ue['avg_cost_per_post_krw'])} (costs.csv 에 post_id 가 있는 비용, "
                 f"게시물 {len(ue['cost_per_post'])}개)")
        L.append("")
        L += _table(["게시물", "직접비"], [[i["post_id"], _krw(i["krw"])] for i in ue["cost_per_post"][:10]])
    else:
        L.append("게시물별 비용 기록이 없어요 (costs.csv 의 post_id 를 채우면 계산돼요).")
    L.append("")
    if ue["sponsored"]:
        L.append("협찬 게시물 도달 1,000당 수익 (계약 총액, 취소 제외. 도달은 카드뉴스+릴스 합)")
        L.append("")
        L += _table(["게시물", "수익", "도달", "도달 1,000당"],
                    [[i["post_id"], _krw(i["revenue_krw"]), _int(i["reach"]), _krw(i["per_1k_reach_krw"])]
                     for i in ue["sponsored"]])
    else:
        L.append("post_id 가 연결된 협찬 수익이 아직 없어요.")
    L.append("")

    # 7. 점검
    L += ["## 7. 데이터 점검", ""]
    L += [f"- {w}" for w in s["warnings"]] or ["문제 없음."]
    L.append("")
    return "\n".join(L)


def terminal_summary(s: dict) -> str:
    m, f = s["money"], s["followers"]
    rated = [r for r in s["posts"] if r["reach"]]
    out = [f"성과 리포트 {s['month']} (데이터: {s['data_dir']})"]
    if rated:
        cc = s["checkpoint_counts"]
        out.append(f"- 게시물 {len(s['posts'])}개 (7d {cc['7d']} · 24h {cc['24h']}): 저장률 중앙값 "
                   f"{_pct(s['overall']['save_rate'])}, 공유율 {_pct(s['overall']['share_rate'])}")
        if s["enough_posts"]:
            flagged = sorted((r for r in rated if r["flag"]), key=lambda r: -r["goal_index"])
            for r in flagged:
                out.append(f"  {'▲' if r['flag'] == 'top' else '▼'} {_label(r)} {_verdict(r).lstrip('▲▼ ')}")
            if not flagged:
                out.append("  중앙값에서 크게 벗어난 게시물 없음")
        else:
            out.append(f"  상위·하위 판정: 데이터 부족 (도달 기록 {len(rated)}/{MIN_POSTS})")
        for f_key, text in s["recommendations"]["series"].items():
            out.append(f"- 시리즈({FORMAT_KO[f_key]}): {text}")
    elif s["posts"]:
        out.append(f"- 게시물 {len(s['posts'])}개 기록에 reach(도달)가 비어 있어 비율 계산 불가 (리포트 7장)")
    else:
        out.append("- 성과 기록 없음: 게시 24시간·7일 뒤 tracking/metrics.csv 에 기록하세요 (tracking/README.md)")
    if f["latest"] is not None:
        out.append(f"- 팔로워 {f['latest']:,}명" + (f" ({f['change']:+,}, {f['first_date']}부터)" if f["days"] else ""))
    out.append(f"- {s['month']} 순이익 {_krw(m['net_krw'])} = 실현 {_krw(m['realized_net_krw'])} − 비용 {_krw(m['costs_krw'])}")
    out.append(f"  [{_bar(m['progress'])}] {_pct(m['progress'])} / 목표 {_krw(m['goal_krw'])} (목표치이며 예측이 아님)")
    if m["pipeline"]:
        out.append(f"- 미입금 파이프라인 {len(m['pipeline'])}건 {_krw(m['pipeline_gross_krw'])}")
    if s["warnings"]:
        out.append(f"- 데이터 점검 {len(s['warnings'])}건 (리포트 7장)")
    return "\n".join(out)


# ── 명령 ──────────────────────────────────────────────────

def add_arguments(parser) -> None:
    parser.add_argument("--month", help="수익·비용을 볼 달 YYYY-MM (기본: 이번 달)")
    parser.add_argument("--out", help="리포트 폴더 (기본: out/reports)")
    parser.add_argument("--data-dir", help="(테스트용) tracking CSV 폴더. 안에 posts/ 가 있으면 게시물 메타도 거기서 읽음")


def run(args) -> int:
    month = args.month or _today().strftime("%Y-%m")
    if not MONTH_RE.match(month):
        print(f"--month 는 2026-10 처럼 YYYY-MM 으로 적어 주세요 (입력: {month}).")
        return 2
    if args.data_dir and not Path(args.data_dir).is_dir():
        print(f"데이터 폴더가 없어요: {args.data_dir}")
        return 1
    summary = summarize(month, args.data_dir)
    out_dir = Path(args.out) if args.out else ROOT / "out" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"metrics-{summary['date']}.md"
    path.write_text(render_markdown(summary), encoding="utf-8")
    print(terminal_summary(summary))
    try:
        shown = path.resolve().relative_to(ROOT)
    except ValueError:
        shown = path
    print(f"\n리포트: {shown}")
    return 0
