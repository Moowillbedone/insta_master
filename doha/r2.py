"""Cloudflare R2(S3 호환)에 파일을 잠깐 올려 공개 주소를 만드는 업로더 — 표준 라이브러리만으로 SigV4 서명.

Instagram 게시 API는 이미지·영상을 '공개 HTTPS 주소'로만 받는다 (research/ig-auto-publish.md §1-2, §2).
그래서 게시 직전에 JPEG·MP4를 R2에 올리고, 게시가 끝나면 지운다.

환경 변수 (값은 출력하지 않는다):
  R2_ACCOUNT_ID         Cloudflare 계정 ID → https://<계정ID>.r2.cloudflarestorage.com
  R2_ACCESS_KEY_ID      R2 API 토큰의 Access Key ID (버킷 하나에 Object Read & Write 권한만)
  R2_SECRET_ACCESS_KEY  같은 토큰의 Secret Access Key
  R2_BUCKET             버킷 이름
  R2_PUBLIC_BASE_URL    버킷의 공개 주소 (내 도메인 권장, 예: https://media.example.com). r2.dev 는 첫 시험에만
  R2_ENDPOINT           (선택·시험용) S3 엔드포인트를 바꿀 때. 예: 로컬 모의 서버 http://127.0.0.1:9000

서명: AWS Signature Version 4, region "auto", service "s3", 경로형 주소(<엔드포인트>/<버킷>/<키>).
본문 해시는 UNSIGNED-PAYLOAD 대신 실제 SHA-256 을 넣는다 (x-amz-content-sha256).
`python -m doha.r2 --self-test` 로 AWS 문서의 공개 예제 서명과 똑같이 계산되는지 확인할 수 있다.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REGION = "auto"
SERVICE = "s3"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
ENV_VARS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "R2_PUBLIC_BASE_URL")


class R2Error(Exception):
    pass


@dataclass(frozen=True)
class R2Config:
    access_key_id: str
    secret_access_key: str
    bucket: str
    endpoint: str          # https://<계정ID>.r2.cloudflarestorage.com (끝에 / 없음)
    public_base_url: str   # 끝에 / 없음

    @classmethod
    def from_env(cls) -> "R2Config":
        env = {k: os.environ.get(k, "").strip() for k in ENV_VARS + ("R2_ENDPOINT",)}
        endpoint = env["R2_ENDPOINT"].rstrip("/")
        required = [k for k in ENV_VARS if not (k == "R2_ACCOUNT_ID" and endpoint)]
        missing = [k for k in required if not env[k]]
        if missing:
            raise R2Error("R2 설정이 비어 있어요: " + ", ".join(missing)
                          + " — .env(또는 서버 비밀값)에 넣어 주세요. 값은 채팅·문서에 붙여넣지 마세요.")
        if not endpoint:
            endpoint = f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"
        public = env["R2_PUBLIC_BASE_URL"].rstrip("/")
        if not public.startswith(("https://", "http://")):
            raise R2Error("R2_PUBLIC_BASE_URL 은 https:// 로 시작하는 공개 주소여야 해요 (예: https://media.내도메인).")
        return cls(env["R2_ACCESS_KEY_ID"], env["R2_SECRET_ACCESS_KEY"], env["R2_BUCKET"], endpoint, public)


# ---------------------------------------------------------------- SigV4

def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def quote_key(key: str) -> str:
    """S3 경로 인코딩: 영문·숫자·-_.~ 와 / 만 그대로 두고 나머지는 %XX (한 번만 인코딩)."""
    return urllib.parse.quote(key, safe="/-_.~")


def _canonical_query(query: str) -> str:
    pairs = urllib.parse.parse_qsl(query, keep_blank_values=True)
    enc = [(urllib.parse.quote(k, safe="-_.~"), urllib.parse.quote(v, safe="-_.~")) for k, v in pairs]
    return "&".join(f"{k}={v}" for k, v in sorted(enc))


def signature_v4(method: str, url: str, headers: dict[str, str], payload_hash: str, *, access_key: str,
                 secret_key: str, region: str, service: str, amz_date: str) -> tuple[str, str, str]:
    """(Authorization 헤더 값, 서명, canonical request). headers 의 모든 항목을 서명한다 (host·x-amz-date 포함).

    url 의 경로는 이미 인코딩된 상태여야 한다 (quote_key). S3 는 경로를 다시 인코딩·정규화하지 않는다.
    """
    parts = urllib.parse.urlsplit(url)
    canon_headers = {k.strip().lower(): " ".join(str(v).split()) for k, v in headers.items()}
    names = sorted(canon_headers)
    signed_headers = ";".join(names)
    canonical = "\n".join([
        method.upper(),
        parts.path or "/",
        _canonical_query(parts.query),
        "".join(f"{n}:{canon_headers[n]}\n" for n in names),
        signed_headers,
        payload_hash,
    ])
    date = amz_date[:8]
    scope = f"{date}/{region}/{service}/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode("utf-8")).hexdigest()])
    k = _hmac(("AWS4" + secret_key).encode("utf-8"), date)
    k = _hmac(_hmac(_hmac(k, region), service), "aws4_request")
    signature = hmac.new(k, to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    auth = (f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}")
    return auth, signature, canonical


# ---------------------------------------------------------------- 요청

def _ssl_context():
    from doha.insights import _ssl_context as ctx  # macOS python.org 설치판 인증서 대응을 함께 쓴다

    return ctx()


def object_url(cfg: R2Config, key: str) -> str:
    return f"{cfg.endpoint}/{quote_key(cfg.bucket)}/{quote_key(key.lstrip('/'))}"


def public_url(key: str, cfg: R2Config | None = None) -> str:
    cfg = cfg or R2Config.from_env()
    return f"{cfg.public_base_url}/{quote_key(key.lstrip('/'))}"


def _request(cfg: R2Config, method: str, key: str, body: bytes = b"", extra: dict[str, str] | None = None,
             timeout: float = 120) -> int:
    url = object_url(cfg, key)
    payload_hash = hashlib.sha256(body).hexdigest() if body else EMPTY_SHA256
    amz_date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    headers = {"host": urllib.parse.urlsplit(url).netloc, "x-amz-date": amz_date,
               "x-amz-content-sha256": payload_hash, **(extra or {})}
    auth, _, _ = signature_v4(method, url, headers, payload_hash, access_key=cfg.access_key_id,
                              secret_key=cfg.secret_access_key, region=REGION, service=SERVICE, amz_date=amz_date)
    req = urllib.request.Request(url, data=body if method in ("PUT", "POST") else None, method=method)
    for k, v in headers.items():
        req.add_header(k.capitalize() if k == "host" else k, v)
    req.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            resp.read()
            return resp.status
    except urllib.error.HTTPError as e:
        detail = _s3_error(e)
        hint = {
            403: "키 권한(이 버킷에 Object Read & Write)이나 서버 시계가 맞는지 확인하세요 (SignatureDoesNotMatch·RequestTimeTooSkewed).",
            404: "R2_BUCKET 이름과 R2_ACCOUNT_ID 를 확인하세요.",
        }.get(e.code, "")
        raise R2Error(f"R2 {method} 실패: HTTP {e.code} {detail} {hint}".strip()) from None
    except urllib.error.URLError as e:
        raise R2Error(f"R2 연결 실패: {e.reason}") from None
    except TimeoutError:
        raise R2Error(f"R2 응답 시간 초과 ({timeout:.0f}초)") from None


def _s3_error(e: urllib.error.HTTPError) -> str:
    """S3 오류 XML 에서 <Code> 만 꺼낸다 (요청 서명·키 값은 출력하지 않는다)."""
    try:
        text = e.read(4096).decode("utf-8", "replace")
    except Exception:
        return ""
    start, end = text.find("<Code>"), text.find("</Code>")
    return text[start + 6:end] if 0 <= start < end else ""


def put_object(local_path: str | os.PathLike, key: str, content_type: str, *, cfg: R2Config | None = None,
               cache_control: str = "no-cache") -> str:
    """파일을 R2 에 올리고 공개 주소(R2_PUBLIC_BASE_URL + '/' + 키)를 돌려준다."""
    cfg = cfg or R2Config.from_env()
    body = Path(local_path).read_bytes()
    if not body:
        raise R2Error(f"빈 파일은 올리지 않아요: {local_path}")
    _request(cfg, "PUT", key, body, {"content-type": content_type, "cache-control": cache_control},
             timeout=max(60, len(body) / 200_000))  # 느린 회선(초당 200KB)도 견디게
    return public_url(key, cfg)


def delete_object(key: str, *, cfg: R2Config | None = None) -> None:
    """R2 에서 지운다. 이미 없으면(404) 조용히 넘어간다 (S3 DELETE 는 원래 204)."""
    cfg = cfg or R2Config.from_env()
    try:
        _request(cfg, "DELETE", key, timeout=30)
    except R2Error as e:
        if "HTTP 404" not in str(e):
            raise


def check_public_url(url: str, expected_type: str = "image/jpeg", timeout: float = 20) -> str | None:
    """Meta 가 가져가기 전에 공개 주소를 직접 열어 본다. 문제가 없으면 None, 있으면 한국어 설명.

    200 · Content-Type · 0이 아닌 크기 (research/ig-auto-publish.md §2: 9004/2207052 '가져오기 실패' 예방).
    """
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "doha-publish-check/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                size = int(resp.headers.get("Content-Length") or 0)
                if method == "GET" and not size:
                    size = len(resp.read(1))
                if ctype != expected_type:
                    return f"Content-Type 이 '{ctype or '없음'}' 이에요 (필요: {expected_type})"
                if size <= 0:
                    return "파일 크기가 0이에요"
                return None
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue  # HEAD 를 막는 서버가 있다 → GET 으로 한 번 더
            return f"HTTP {e.code} (공개 접근이 막혔거나 주소가 틀렸어요 — R2 버킷 공개 설정·R2_PUBLIC_BASE_URL 확인)"
        except (urllib.error.URLError, TimeoutError) as e:
            return f"열 수 없어요: {getattr(e, 'reason', e)}"
    return "공개 주소를 확인하지 못했어요"


# ---------------------------------------------------------------- 자체 시험 (AWS 문서 공개 예제)

_AWS_S3_KEY = ("AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
SELF_TESTS = [
    # S3 'Signature Calculations for the Authorization Header: Transferring Payload in a Single Chunk' — GET Object
    {"name": "S3 GET Object 예제", "method": "GET", "url": "https://examplebucket.s3.amazonaws.com/test.txt",
     "headers": {"Host": "examplebucket.s3.amazonaws.com", "Range": "bytes=0-9",
                 "x-amz-content-sha256": EMPTY_SHA256, "x-amz-date": "20130524T000000Z"},
     "payload": EMPTY_SHA256, "key": _AWS_S3_KEY, "region": "us-east-1", "service": "s3",
     "expect": "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"},
    # 같은 문서의 PUT Object 예제 (본문 'Welcome to Amazon S3.', 키의 $ 는 %24 로 인코딩)
    {"name": "S3 PUT Object 예제", "method": "PUT",
     "url": "https://examplebucket.s3.amazonaws.com/" + quote_key("test$file.text"),
     "headers": {"Host": "examplebucket.s3.amazonaws.com", "Date": "Fri, 24 May 2013 00:00:00 GMT",
                 "x-amz-date": "20130524T000000Z", "x-amz-storage-class": "REDUCED_REDUNDANCY",
                 "x-amz-content-sha256": hashlib.sha256(b"Welcome to Amazon S3.").hexdigest()},
     "payload": hashlib.sha256(b"Welcome to Amazon S3.").hexdigest(), "key": _AWS_S3_KEY,
     "region": "us-east-1", "service": "s3",
     "expect": "98ad721746da40c64f1a55b78f14c238d841ea1380cd77a1b5971af0ece108bd"},
    # SigV4 테스트 모음 get-vanilla (AKIDEXAMPLE, 2015-08-30)
    {"name": "SigV4 get-vanilla (AKIDEXAMPLE)", "method": "GET", "url": "https://example.amazonaws.com/",
     "headers": {"Host": "example.amazonaws.com", "X-Amz-Date": "20150830T123600Z"},
     "payload": EMPTY_SHA256, "key": ("AKIDEXAMPLE", "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"),
     "region": "us-east-1", "service": "service",
     "expect": "5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31"},
]


def self_test(verbose: bool = True) -> bool:
    ok_all = True
    for t in SELF_TESTS:
        amz_date = next(v for k, v in t["headers"].items() if k.lower() == "x-amz-date")
        _, sig, _ = signature_v4(t["method"], t["url"], t["headers"], t["payload"], access_key=t["key"][0],
                                 secret_key=t["key"][1], region=t["region"], service=t["service"], amz_date=amz_date)
        ok = sig == t["expect"]
        ok_all &= ok
        if verbose:
            print(f"  {'✓' if ok else '✗'} {t['name']}" + ("" if ok else f" — 계산 {sig[:16]}… / 기대 {t['expect'][:16]}…"))
    return ok_all


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        print("SigV4 서명 자체 시험 (AWS 문서 공개 예제):")
        sys.exit(0 if self_test() else 1)
    print("사용: python -m doha.r2 --self-test")
