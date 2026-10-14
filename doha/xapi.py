"""X(구 트위터) API v2 최소 클라이언트 — OAuth 1.0a 사용자 컨텍스트(HMAC-SHA1, RFC 5849) 서명.

쓰는 곳: doha/xpublish.py (x-publish, x-metrics, x-targets). 표준 라이브러리만 씁니다.

환경변수 (.env 에만 두고 채팅·문서·로그에 붙여넣지 않기):
  X_API_KEY, X_API_SECRET              앱의 Consumer Key / Secret
  X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET  내 계정용 Access Token / Secret (앱 권한 'Read and write' 로 발급)
  X_API_BASE                           (테스트용) API 주소 바꾸기. 기본 https://api.x.com

할 수 있는 것 (일부러 이것만):
  upload_media(path, alt_text)   POST /2/media/upload (multipart, media_category=tweet_image, GIF 는 tweet_gif)
                                 → 대체 텍스트는 POST /2/media/metadata 로 붙임 (실패해도 게시는 계속)
  create_post(text, media_ids, reply_to)
                                 POST /2/tweets. reply_to 는 '내 스레드 이어 쓰기' 전용:
                                 이번 실행에서 내가 올린 글이거나, API로 작성자가 나인지 확인된 글에만 답글을 단다.
  get_me()                       GET /2/users/me (팔로워 수 등 public_metrics)
  get_posts_metrics(ids)         GET /2/tweets?ids=… (public_metrics, created_at)
  get_user_posts(username, max)  GET /2/users/by/username/:u → GET /2/users/:id/tweets (답글·리포스트 제외)

하지 않는 것: 남의 글에 답글·멘션·인용, 좋아요, 팔로우, DM, 스크래핑 (research/x-automation-api.md '운영에 바로 쓰는 결론').

비밀값은 어떤 메시지에도 넣지 않는다. 오류 메시지는 _redact 로 한 번 더 걸러 낸다.

    python -m doha.xapi        # 서명 함수 자체 시험 (Twitter 문서·OAuth 1.0 명세의 공개 예제와 비교)
"""
from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import http.client
import json
import mimetypes
import os
import re
import secrets
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_BASE = "https://api.x.com"
KST = timezone(timedelta(hours=9))
ENV_NAMES = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")
POST_ID_RE = re.compile(r"^\d{1,25}$")
IMAGE_MAX_BYTES = 5 * 1024 * 1024        # X 이미지 한도로 널리 알려진 값 (공식 문서 재확인 필요)
USER_AGENT = "doha-kit/1.0"


class XApiError(Exception):
    """사람이 읽을 한국어 메시지. status: HTTP 코드(없으면 None), transient: 나중에 다시 시도하면 될 수 있는 오류."""

    def __init__(self, message: str, status: int | None = None, reset_at: datetime | None = None,
                 transient: bool = False, maybe_sent: bool = False):
        super().__init__(_redact(message))
        self.status = status
        self.reset_at = reset_at
        self.transient = transient
        # 요청은 보냈는데 응답을 못 받음 (시간 초과·연결 끊김): 글이 실제로 올라갔을 수도 있다 → 자동 재시도 금지
        self.maybe_sent = maybe_sent


# ---------------------------------------------------------------- OAuth 1.0a (RFC 5849)

def pct(value) -> str:
    """RFC 3986 퍼센트 인코딩 (RFC 5849 §3.6): 영문·숫자·'-._~' 만 그대로, 나머지는 UTF-8 바이트를 %XX(대문자)로."""
    return urllib.parse.quote(str(value), safe="-._~")


def base_string_uri(url: str) -> str:
    """서명 기준 URL (RFC 5849 §3.4.1.2): 스킴·호스트 소문자, 기본 포트(80/443) 생략, 쿼리·프래그먼트 제외."""
    parts = urllib.parse.urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    netloc = host if port is None or (scheme, port) in (("http", 80), ("https", 443)) else f"{host}:{port}"
    return f"{scheme}://{netloc}{parts.path or '/'}"


def signature_base_string(method: str, url: str, params: list[tuple[str, str]]) -> str:
    """서명 기준 문자열 (RFC 5849 §3.4.1). params 는 쿼리 + oauth_* (+ x-www-form-urlencoded 본문) 의 (이름, 값) 목록.

    RFC 5849 §3.4.1.1 예제 (realm·oauth_signature 는 제외, 같은 이름 a3 두 번):

    >>> signature_base_string("POST", "http://example.com/request?b5=%3D%253D&a3=a&c%40=&a2=r%20b", [
    ...     ("b5", "=%3D"), ("a3", "a"), ("c@", ""), ("a2", "r b"), ("c2", ""), ("a3", "2 q"),
    ...     ("oauth_consumer_key", "9djdj82h48djs9d2"), ("oauth_token", "kkk9d7dh3k39sjv7"),
    ...     ("oauth_signature_method", "HMAC-SHA1"), ("oauth_timestamp", "137131201"),
    ...     ("oauth_nonce", "7d8f3e4a")])  # doctest: +NORMALIZE_WHITESPACE
    'POST&http%3A%2F%2Fexample.com%2Frequest&a2%3Dr%2520b%26a3%3D2%2520q%26a3%3Da%26b5%3D%253D%25253D%26c%2540%3D%26c2%3D%26oauth_consumer_key%3D9djdj82h48djs9d2%26oauth_nonce%3D7d8f3e4a%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D137131201%26oauth_token%3Dkkk9d7dh3k39sjv7'
    """
    pairs = sorted((pct(k), pct(v)) for k, v in params)
    normalized = "&".join(f"{k}={v}" for k, v in pairs)
    return "&".join([method.upper(), pct(base_string_uri(url)), pct(normalized)])


def hmac_sha1_signature(base_string: str, consumer_secret: str, token_secret: str = "") -> str:
    key = f"{pct(consumer_secret)}&{pct(token_secret or '')}".encode("ascii")
    digest = hmac.new(key, base_string.encode("ascii"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def oauth1_params(consumer_key: str, token: str, nonce: str | None = None, timestamp: int | str | None = None) -> dict:
    return {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce or secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(timestamp if timestamp is not None else int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }


def oauth1_signature(method: str, url: str, params: list[tuple[str, str]], consumer_secret: str,
                     token_secret: str) -> str:
    """HMAC-SHA1 서명. 'Creating a signature' (X/Twitter 개발자 문서) 예제:

    >>> oauth1_signature("POST", "https://api.twitter.com/1.1/statuses/update.json", [
    ...     ("status", "Hello Ladies + Gentlemen, a signed OAuth request!"), ("include_entities", "true"),
    ...     ("oauth_consumer_key", "xvz1evFS4wEEPTGEFPHBog"),
    ...     ("oauth_nonce", "kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg"),
    ...     ("oauth_signature_method", "HMAC-SHA1"), ("oauth_timestamp", "1318622958"),
    ...     ("oauth_token", "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb"), ("oauth_version", "1.0")],
    ...     "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw", "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE")
    'hCtSmYh+iHYCEqBWrE7C7hYmtUk='

    OAuth Core 1.0 부록 A.5 예제 (GET, 쿼리 파라미터):

    >>> oauth1_signature("GET", "http://photos.example.net/photos", [
    ...     ("file", "vacation.jpg"), ("size", "original"), ("oauth_consumer_key", "dpf43f3p2l4k3l03"),
    ...     ("oauth_token", "nnch734d00sl2jdk"), ("oauth_signature_method", "HMAC-SHA1"),
    ...     ("oauth_timestamp", "1191242096"), ("oauth_nonce", "kllo9940pd9333jh"), ("oauth_version", "1.0")],
    ...     "kd94hf93k423kf44", "pfkkdhi9sl3r4s00")
    'tR3+Ty81lMeYAr/Fid0kMTYa/WM='
    """
    return hmac_sha1_signature(signature_base_string(method, url, params), consumer_secret, token_secret)


def oauth1_header(method: str, url: str, params: list[tuple[str, str]] | None, consumer_key: str,
                  consumer_secret: str, token: str, token_secret: str, nonce: str | None = None,
                  timestamp: int | str | None = None) -> str:
    """Authorization 헤더 값. params: 쿼리(+폼 본문) 파라미터. JSON·multipart 본문은 서명에 넣지 않는다 (RFC 5849 §3.4.1.3)."""
    oauth = oauth1_params(consumer_key, token, nonce, timestamp)
    oauth["oauth_signature"] = oauth1_signature(method, url, list(params or []) + list(oauth.items()),
                                                consumer_secret, token_secret)
    return "OAuth " + ", ".join(f'{pct(k)}="{pct(v)}"' for k, v in sorted(oauth.items()))


def self_test() -> bool:
    """공개 예제 값으로 서명 함수를 확인한다. 하나라도 다르면 AssertionError."""
    import doctest
    import sys

    module = sys.modules[__name__]
    result = doctest.testmod(module, verbose=False)
    assert result.failed == 0, f"서명 자체 시험 실패 {result.failed}건"
    header = oauth1_header("POST", "https://api.twitter.com/1.1/statuses/update.json",
                           [("include_entities", "true"),
                            ("status", "Hello Ladies + Gentlemen, a signed OAuth request!")],
                           "xvz1evFS4wEEPTGEFPHBog", "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
                           "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb",
                           "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE",
                           nonce="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", timestamp=1318622958)
    assert 'oauth_signature="hCtSmYh%2BiHYCEqBWrE7C7hYmtUk%3D"' in header, header
    assert header.startswith('OAuth oauth_consumer_key="xvz1evFS4wEEPTGEFPHBog", oauth_nonce='), header
    return True


# ---------------------------------------------------------------- 비밀값 가리기

def _redact(text: str) -> str:
    text = str(text or "")
    for name in ENV_NAMES:
        value = os.environ.get(name, "").strip()   # from_env 와 같은 값 (앞뒤 공백·줄바꿈 제거)
        if value and len(value) >= 6:
            text = text.replace(value, "***")
    return re.sub(r'(oauth_(?:signature|token|consumer_key|nonce)=)"?[^",\s&]+"?', r"\1***", text)


@functools.cache
def _ssl_context() -> ssl.SSLContext:
    """운영체제 인증서 저장소(truststore) → 기본값 + certifi 순 (insights.py 와 같은 규칙)."""
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        pass
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except ImportError:
        pass
    return ctx


def _multipart(fields: list[tuple[str, str]], files: list[tuple[str, str, str, bytes]]) -> tuple[bytes, str]:
    """(본문, Content-Type). files: (필드 이름, 파일 이름, MIME, 바이트)."""
    boundary = "----dohaform" + secrets.token_hex(12)
    out = bytearray()
    for name, value in fields:
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n").encode()
        out += str(value).encode("utf-8") + b"\r\n"
    for name, filename, mime, data in files:
        safe_name = re.sub(r'[^A-Za-z0-9._-]', "_", filename) or "media"
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{safe_name}\"\r\n"
                f"Content-Type: {mime}\r\n\r\n").encode()
        out += data + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def _first_error_detail(body: dict) -> str:
    if not isinstance(body, dict):
        return ""
    errors = body.get("errors") or []
    first = errors[0] if errors and isinstance(errors[0], dict) else {}
    detail = body.get("detail") or first.get("message") or first.get("detail") or body.get("title") or ""
    return str(detail)[:300]


# ---------------------------------------------------------------- 클라이언트

class XClient:
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str,
                 base_url: str | None = None, timeout: float = 30, nonce: str | None = None,
                 timestamp: int | None = None):
        self._ck, self._cs, self._tk, self._ts = api_key, api_secret, access_token, access_token_secret
        self.base = (base_url or os.environ.get("X_API_BASE") or DEFAULT_BASE).rstrip("/")
        self.timeout = timeout
        self._fixed_nonce, self._fixed_timestamp = nonce, timestamp   # 시험용 (서명 재현)
        self.reads = 0            # 읽은 리소스 수 (게시물·사용자) — 비용 추정용
        self.post_reads = 0       # 그중 남의 게시물 (x-targets 예산)
        self.user_reads = 0       # 그중 사용자 조회
        self.writes = 0           # 만든 글 수
        self.media_uploads = 0
        self._own_ids: set[str] = set()
        self._me: dict | None = None

    def __repr__(self) -> str:   # 비밀값이 repr 로 새지 않게
        return f"XClient(base={self.base!r})"

    @classmethod
    def from_env(cls, **kwargs) -> "XClient":
        missing = [n for n in ENV_NAMES if not os.environ.get(n, "").strip()]
        if missing:
            raise XApiError(
                f"X API 키가 없어요: {', '.join(missing)}. .env 에 넣어 주세요 (값은 채팅·문서에 붙여넣지 않기). "
                "발급: X 개발자 콘솔 → 앱 → Keys and tokens, 앱 권한은 'Read and write'.")
        return cls(*(os.environ[n].strip() for n in ENV_NAMES), **kwargs)

    # ---- HTTP

    def _request(self, method: str, path: str, query: dict | None = None, json_body: dict | None = None,
                 multipart: tuple[bytes, str] | None = None, timeout: float | None = None) -> dict:
        url = self.base + path
        query = {k: str(v) for k, v in (query or {}).items() if v is not None}
        full = url + ("?" + urllib.parse.urlencode(query, quote_via=urllib.parse.quote, safe="-._~") if query else "")
        headers = {
            "Authorization": oauth1_header(method, url, list(query.items()), self._ck, self._cs, self._tk, self._ts,
                                           nonce=self._fixed_nonce, timestamp=self._fixed_timestamp),
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        data = None
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        elif multipart is not None:
            data, headers["Content-Type"] = multipart
        req = urllib.request.Request(full, data=data, headers=headers, method=method)
        kwargs = {"timeout": timeout or self.timeout}
        if full.startswith("https://"):
            kwargs["context"] = _ssl_context()
        try:
            with urllib.request.urlopen(req, **kwargs) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise self._http_error(e) from None
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            reason = getattr(e, "reason", e)
            hint = ""
            if "CERTIFICATE_VERIFY_FAILED" in str(reason):
                hint = " 인증서 확인 실패예요. macOS python.org 설치판이면 'Install Certificates.command' 를 한 번 실행하세요."
            # urllib 는 연결·전송 단계 오류만 URLError 로 감싼다. 연결 거부·주소 못 찾음·인증서 오류는 요청이 서버에
            # 닿기 전 → 확실히 안 올라감. URLError 가 아닌 오류(응답 대기·읽기 중 끊김·SSL 오류 등)와 시간 초과·연결
            # 끊김은 서버가 이미 처리했을 수 있다.
            maybe_sent = method == "POST" and (not isinstance(e, urllib.error.URLError) or isinstance(
                reason, (TimeoutError, ConnectionResetError, ConnectionAbortedError, BrokenPipeError,
                         http.client.HTTPException)))
            raise XApiError(f"X API 연결 실패({type(reason).__name__}): {reason or '응답 없음'}.{hint} "
                            "인터넷 연결을 확인하고 잠시 뒤 다시 시도하세요.",
                            transient=True, maybe_sent=maybe_sent) from None
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            # 2xx 인데 본문이 깨짐: POST 면 이미 처리됐을 수 있다 → 자동 재시도 금지
            raise XApiError(f"X API 응답을 읽지 못했어요 ({path}).", maybe_sent=method == "POST") from None

    def _http_error(self, e: urllib.error.HTTPError) -> XApiError:
        status = e.code
        try:
            body = json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            body = {}
        detail = _first_error_detail(body)
        tail = f" (X 응답: {detail})" if detail else ""
        if status == 401:
            return XApiError(
                "인증 실패(401): X_API_KEY·X_API_SECRET·X_ACCESS_TOKEN·X_ACCESS_TOKEN_SECRET 를 확인하세요. "
                "앱 권한을 'Read and write' 로 바꿨다면 Access Token 을 다시 발급해야 해요." + tail, status)
        if status == 402:
            return XApiError(
                "결제 필요(402): X API 크레딧이 부족하거나 결제 수단이 없어요. X 개발자 콘솔에서 크레딧을 충전한 뒤 "
                "다시 실행하세요 (자동 충전은 꺼 두기)." + tail, status)
        if status == 403:
            return XApiError(
                "거부됨(403): X 가 이 요청을 막았어요. 같은 글 반복(중복 게시), 다른 사람 글에 답글, 앱 권한('Read and write'), "
                "계정 제한 여부를 확인하세요." + tail, status)
        if status == 429:
            reset_at = None
            raw = e.headers.get("x-rate-limit-reset") if e.headers else None
            try:
                reset_at = datetime.fromtimestamp(int(raw), KST) if raw else None
            except (TypeError, ValueError):
                reset_at = None
            when = f"{reset_at:%m-%d %H:%M} KST 이후" if reset_at else "15분쯤 뒤"
            return XApiError(f"요청 한도 초과(429): {when} 다시 시도하세요." + tail, status, reset_at, transient=True)
        if status >= 500:
            return XApiError(f"X 서버 오류({status}): 잠시 뒤 다시 시도하세요." + tail, status, transient=True)
        if status == 400:
            return XApiError("요청 형식 오류(400)." + tail, status)
        if status == 404:
            return XApiError("찾을 수 없음(404): 삭제됐거나 비공개인 글·계정일 수 있어요." + tail, status)
        return XApiError(f"X API 오류(HTTP {status})." + tail, status)

    # ---- 읽기

    def get_me(self) -> dict:
        """{'id','username','name','public_metrics':{followers_count,…}, 'verified', 'verified_type'}"""
        if self._me is None:
            r = self._request("GET", "/2/users/me",
                              {"user.fields": "public_metrics,verified,verified_type,created_at"})
            self._me = r.get("data") or {}
            self.reads += 1
            if not self._me.get("id"):
                raise XApiError("내 계정 정보를 받지 못했어요 (GET /2/users/me).")
        return self._me

    def get_posts_metrics(self, ids: list[str]) -> dict[str, dict]:
        """{x_id: {'created_at', 'public_metrics': {...}}}. 삭제된 글은 빠진다. 없는 지표는 키가 없을 수 있다."""
        out: dict[str, dict] = {}
        ids = [str(i) for i in ids if POST_ID_RE.match(str(i))]
        for start in range(0, len(ids), 100):
            chunk = ids[start:start + 100]
            r = self._request("GET", "/2/tweets", {"ids": ",".join(chunk), "tweet.fields": "public_metrics,created_at"})
            for item in r.get("data") or []:
                out[str(item.get("id"))] = item
            self.reads += len(r.get("data") or [])
        return out

    def lookup_user_id(self, username: str) -> str:
        username = username.lstrip("@").strip()
        if not USERNAME_RE.match(username):
            raise XApiError(f"사용자 이름 형식이 아니에요: {username!r}")
        user = self._request("GET", f"/2/users/by/username/{username}").get("data") or {}
        self.reads += 1
        self.user_reads += 1
        uid = str(user.get("id") or "")
        if not POST_ID_RE.match(uid):
            raise XApiError(f"@{username} 계정을 찾지 못했어요.")
        return uid

    def get_user_posts(self, username: str, max_posts: int = 3, user_id: str | None = None) -> list[dict]:
        """최근 원본 글 (답글·리포스트 제외). API 최소 단위가 5개라 5개를 받고 앞의 max_posts 개만 돌려준다.

        user_id 를 알면(캐시) 사용자 조회 1회를 아낀다."""
        username = username.lstrip("@").strip()
        if not USERNAME_RE.match(username):
            raise XApiError(f"사용자 이름 형식이 아니에요: {username!r}")
        uid = str(user_id or "") if POST_ID_RE.match(str(user_id or "")) else self.lookup_user_id(username)
        r = self._request("GET", f"/2/users/{uid}/tweets",
                          {"max_results": 5, "exclude": "replies,retweets",
                           "tweet.fields": "created_at,public_metrics,author_id"})
        data = r.get("data") or []
        self.reads += len(data)
        self.post_reads += len(data)
        for item in data:
            item["username"] = username
            item["author_id"] = item.get("author_id") or uid
        return data[:max_posts]

    # ---- 쓰기

    def upload_media(self, path: str | Path, alt_text: str = "") -> str:
        """이미지 1장 업로드 → media id. 대체 텍스트는 붙이기를 시도하고, 실패해도 id 는 돌려준다."""
        path = Path(path)
        if not path.is_file():
            raise XApiError(f"이미지 파일이 없어요: {path}")
        data = path.read_bytes()
        if len(data) > IMAGE_MAX_BYTES:
            raise XApiError(f"이미지가 5MB 를 넘어요 ({len(data) / 1048576:.1f}MB): {path.name}. JPEG 로 줄여 주세요.")
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        category = "tweet_gif" if mime == "image/gif" else "tweet_image"
        body = _multipart([("media_category", category), ("media_type", mime)],
                          [("media", path.name, mime, data)])
        r = self._request("POST", "/2/media/upload", multipart=body, timeout=max(self.timeout, 120))
        media_id = str((r.get("data") or {}).get("id") or r.get("media_id_string") or "")
        if not media_id:
            raise XApiError(f"이미지 업로드 응답에 id 가 없어요: {path.name}")
        self.media_uploads += 1
        if alt_text:
            try:
                self._request("POST", "/2/media/metadata",
                              json_body={"id": media_id, "metadata": {"alt_text": {"text": alt_text[:1000]}}})
            except XApiError as e:
                print(f"  주의: 대체 텍스트를 붙이지 못했어요 ({path.name}) — 게시는 계속합니다. {e}")
        return media_id

    def _verify_own(self, post_id: str) -> None:
        """답글 대상이 내 글인지 API 로 확인 (지난 실행에서 올린 스레드를 이어 쓸 때)."""
        me = self.get_me()
        r = self._request("GET", f"/2/tweets/{post_id}", {"tweet.fields": "author_id"})
        self.reads += 1
        author = str((r.get("data") or {}).get("author_id") or "")
        if author != str(me.get("id")):
            raise XApiError("다른 사람의 글에는 자동으로 답글을 달지 않아요. 답글은 내 스레드를 이어 쓸 때만 씁니다.")
        self._own_ids.add(str(post_id))

    def create_post(self, text: str, media_ids: list[str] | None = None, reply_to: str | None = None) -> str:
        """글 하나 게시 → 새 글 id. 재시도하지 않는다 (중복 게시 방지)."""
        body: dict = {"text": text}
        if media_ids:
            body["media"] = {"media_ids": [str(m) for m in media_ids][:4]}
        if reply_to:
            reply_to = str(reply_to)
            if not POST_ID_RE.match(reply_to):
                raise XApiError(f"답글 대상 id 형식이 아니에요: {reply_to!r}")
            if reply_to not in self._own_ids:
                self._verify_own(reply_to)
            body["reply"] = {"in_reply_to_tweet_id": reply_to}
        r = self._request("POST", "/2/tweets", json_body=body)
        post_id = str((r.get("data") or {}).get("id") or "")
        if not POST_ID_RE.match(post_id):
            raise XApiError("게시 응답에 글 id 가 없어요. X 앱에서 실제로 올라갔는지 확인하세요.", maybe_sent=True)
        self._own_ids.add(post_id)
        self.writes += 1
        return post_id


if __name__ == "__main__":
    self_test()
    print("OAuth 1.0a 서명 자체 시험 통과 (Twitter 'Creating a signature' 예제, OAuth Core 1.0 부록 A.5, RFC 5849 §3.4.1.1)")
