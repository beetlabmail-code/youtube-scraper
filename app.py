#!/usr/bin/env python3
"""صفحهٔ ساده برای دیدن آمار About یک کانال یوتیوب."""

from __future__ import annotations

import errno
import json
import re
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
PORT = 8765

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Cookie": "SOCS=CAI",
}

PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>اطلاعات کانال یوتیوب</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #1c1915;
      --muted: #6d655c;
      --line: #e4ddd2;
      --paper: #f6f3ee;
      --card: #fffdf9;
      --accent: #9a3412;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--paper);
      color: var(--ink);
      font-family: "Segoe UI", Tahoma, sans-serif;
    }
    main {
      width: min(560px, calc(100% - 32px));
      margin: 64px auto;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 28px;
      font-weight: 650;
    }
    p.lead {
      margin: 0 0 24px;
      color: var(--muted);
      line-height: 1.6;
    }
    form {
      display: flex;
      gap: 8px;
    }
    input {
      flex: 1;
      min-width: 0;
      height: 46px;
      padding: 0 14px;
      border: 1px solid #d9d0c4;
      border-radius: 10px;
      background: white;
      color: var(--ink);
      font: inherit;
      direction: ltr;
      text-align: left;
    }
    input:focus {
      outline: 2px solid #fdba74;
      border-color: transparent;
    }
    button {
      height: 46px;
      padding: 0 18px;
      border: 0;
      border-radius: 10px;
      background: var(--accent);
      color: white;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.6;
      cursor: wait;
    }
    #retry {
      margin-top: 8px;
      background: transparent;
      color: var(--accent);
      border: 1px solid #e7c3b4;
    }
    .status {
      min-height: 24px;
      margin: 14px 0 0;
      color: var(--muted);
    }
    .status.error { color: #9f1239; }
    article {
      margin-top: 18px;
      padding: 8px 18px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
    }
    article h2 {
      margin: 14px 0 4px;
      font-size: 18px;
    }
    dl { margin: 0; }
    .row {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 12px;
      padding: 12px 0;
      border-top: 1px solid var(--line);
    }
    dt { color: var(--muted); }
    dd {
      margin: 0;
      direction: ltr;
      text-align: left;
      font-variant-numeric: tabular-nums;
    }
    @media (max-width: 520px) {
      main { margin: 32px auto; }
      form { flex-direction: column; }
      button { width: 100%; }
      .row { grid-template-columns: 1fr; gap: 4px; }
    }
  </style>
</head>
<body>
  <main>
    <h1>اطلاعات کانال</h1>
    <p class="lead">آیدی یا آدرس پیج را وارد کن تا کشور، تاریخ عضویت، مشترک، تعداد ویدیو و بازدید نشان داده شود.</p>
    <form id="search">
      <input id="query" name="q" autocomplete="off" spellcheck="false" placeholder="@maxeninfarsi" required>
      <button id="go" type="submit">جستجو</button>
    </form>
    <p id="status" class="status" aria-live="polite"></p>
    <button id="retry" type="button" hidden>تلاش مجدد</button>
    <article id="result" hidden>
      <h2 id="title"></h2>
      <dl>
        <div class="row"><dt>آدرس</dt><dd id="url"></dd></div>
        <div class="row"><dt>کشور</dt><dd id="country"></dd></div>
        <div class="row"><dt>عضویت</dt><dd id="joined"></dd></div>
        <div class="row"><dt>مشترک</dt><dd id="subscribers"></dd></div>
        <div class="row"><dt>ویدیو</dt><dd id="videos"></dd></div>
        <div class="row"><dt>بازدید</dt><dd id="views"></dd></div>
      </dl>
    </article>
  </main>
  <script>
    const form = document.querySelector("#search");
    const query = document.querySelector("#query");
    const button = document.querySelector("#go");
    const retry = document.querySelector("#retry");
    const status = document.querySelector("#status");
    const result = document.querySelector("#result");
    const fields = ["url", "country", "joined", "subscribers", "videos", "views"];
    const maxAttempts = 5;

    function showResult(data) {
      document.querySelector("#title").textContent = data.title || "کانال";
      for (const field of fields) {
        document.querySelector("#" + field).textContent = data[field] || "—";
      }
      status.className = "status";
      status.textContent = "";
      result.hidden = false;
      retry.hidden = true;
    }

    function showFailure(message, canRetry) {
      status.className = "status error";
      status.textContent = message;
      result.hidden = true;
      retry.hidden = !canRetry;
    }

    async function lookup() {
      button.disabled = true;
      retry.hidden = true;
      result.hidden = true;
      status.className = "status";
      let lastError = "دریافت اطلاعات ممکن نشد.";
      let canRetry = true;

      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        status.textContent = attempt === 1
          ? "در حال دریافت از یوتیوب…"
          : "تلاش " + attempt + " از " + maxAttempts + "…";
        try {
          const response = await fetch("/api/channel?q=" + encodeURIComponent(query.value.trim()));
          const data = await response.json();
          if (response.ok) {
            showResult(data);
            button.disabled = false;
            return;
          }
          lastError = data.error || lastError;
          if (!data.retryable) {
            canRetry = false;
            break;
          }
        } catch (error) {
          lastError = "اتصال برقرار نشد.";
        }
        if (attempt < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 600));
        }
      }

      showFailure(lastError, canRetry);
      button.disabled = false;
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      lookup();
    });
    retry.addEventListener("click", lookup);
  </script>
</body>
</html>
"""


class ChannelError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


def fetch(url: str, data: bytes | None = None, extra: dict | None = None) -> str:
    headers = dict(HEADERS)
    if extra:
        headers.update(extra)
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise ChannelError("این کانال پیدا نشد.") from error
        raise ChannelError(f"یوتیوب پاسخ {error.code} داد.", retryable=True) from error
    except urllib.error.URLError as error:
        raise ChannelError("اتصال به یوتیوب برقرار نشد.", retryable=True) from error


def channel_url(query: str) -> str:
    text = query.strip()
    if not text:
        raise ChannelError("آیدی پیج را وارد کن.")

    text = text.split("?")[0].split("#")[0].rstrip("/")
    found = re.search(
        r"(?:https?://)?(?:www\.)?youtube\.com/"
        r"(?P<path>@[\w.-]+|channel/UC[\w-]{22}|c/[\w.-]+|user/[\w.-]+)",
        text,
        re.IGNORECASE,
    )
    if found:
        return "https://www.youtube.com/" + found.group("path")
    if re.fullmatch(r"UC[\w-]{22}", text):
        return "https://www.youtube.com/channel/" + text
    handle = text[1:] if text.startswith("@") else text
    if re.fullmatch(r"[\w.-]{3,}", handle):
        return "https://www.youtube.com/@" + handle
    raise ChannelError("آیدی یا آدرس پیج شناخته نشد.")


def loads_initial(html: str) -> dict:
    match = re.search(r"ytInitialData\s*=\s*(\{.+?\})\s*;\s*</script>", html, re.DOTALL)
    if not match:
        raise ChannelError("یوتیوب صفحهٔ آمار را برنگرداند.", retryable=True)
    return json.loads(match.group(1))


def text_of(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("content", "simpleText"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
        runs = value.get("runs")
        if isinstance(runs, list):
            joined = "".join(
                part.get("text", "") for part in runs if isinstance(part, dict)
            ).strip()
            if joined:
                return joined
    return None


def walk(node):
    if isinstance(node, dict):
        yield node
        for child in node.values():
            yield from walk(child)
    elif isinstance(node, list):
        for child in node:
            yield from walk(child)


def first_model(data: dict, key: str) -> dict | None:
    for node in walk(data):
        model = node.get(key)
        if isinstance(model, dict):
            return model
    return None


def about_from(data: dict, meta: dict | None = None) -> dict:
    source = (
        first_model(data, "aboutChannelViewModel")
        or first_model(data, "channelAboutFullMetadataRenderer")
        or {}
    )
    meta = meta or {}
    url = (
        text_of(source.get("canonicalChannelUrl"))
        or text_of(source.get("displayCanonicalChannelUrl"))
        or meta.get("vanityChannelUrl")
        or meta.get("channelUrl")
    )
    if isinstance(url, str):
        url = re.sub(r"^https?://", "", url).rstrip("/")
    title = meta.get("title") if isinstance(meta.get("title"), str) else None
    return {
        "title": title,
        "url": url,
        "country": text_of(source.get("country")),
        "joined": text_of(source.get("joinedDateText")),
        "subscribers": text_of(source.get("subscriberCountText")),
        "videos": text_of(source.get("videoCountText")),
        "views": text_of(source.get("viewCountText")),
    }


def innertube_about(html: str, channel_id: str) -> dict:
    key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
    version = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', html)
    if not key or not version:
        raise ChannelError("اطلاعات About این کانال در صفحه پیدا نشد.", retryable=True)
    body = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": version.group(1),
                "hl": "en",
                "gl": "GB",
            }
        },
        "browseId": channel_id,
        "params": "EgVhYm91dA==",
    }
    raw = fetch(
        "https://www.youtube.com/youtubei/v1/browse"
        f"?key={key.group(1)}&prettyPrint=false",
        data=json.dumps(body).encode("utf-8"),
        extra={"Content-Type": "application/json"},
    )
    return json.loads(raw)


def channel_about(query: str) -> dict:
    page = channel_url(query).rstrip("/") + "/about"
    html = fetch(page)
    data = loads_initial(html)
    meta = first_model(data, "channelMetadataRenderer") or {}
    result = about_from(data, meta)

    if not result["views"] and not result["subscribers"]:
        channel_id = meta.get("externalId")
        if not isinstance(channel_id, str):
            found = re.search(r'"browseId":"(UC[\w-]{22})"', html)
            channel_id = found.group(1) if found else None
        if not channel_id:
            raise ChannelError("آمار این کانال پیدا نشد.", retryable=True)
        result = about_from(innertube_about(html, channel_id), meta)

    if not any(result[key] for key in ("country", "joined", "subscribers", "videos", "views")):
        raise ChannelError("آمار بخش More برای این کانال پیدا نشد.", retryable=True)
    return result


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path)
        if path.path == "/":
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path.path == "/api/channel":
            query = parse_qs(path.query).get("q", [""])[0]
            try:
                payload = channel_about(query)
                self._send(
                    200,
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    "application/json; charset=utf-8",
                )
            except ChannelError as error:
                self._send(
                    400,
                    json.dumps(
                        {"error": str(error), "retryable": error.retryable},
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    "application/json; charset=utf-8",
                )
            except (json.JSONDecodeError, TimeoutError, OSError):
                self._send(
                    502,
                    json.dumps(
                        {
                            "error": "دریافت اطلاعات از یوتیوب ناقص ماند.",
                            "retryable": True,
                        },
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    "application/json; charset=utf-8",
                )
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main() -> None:
    url = f"http://{HOST}:{PORT}"
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as error:
        if getattr(error, "winerror", None) == 10048 or error.errno == errno.EADDRINUSE:
            print(f"صفحه از قبل باز است: {url}")
            webbrowser.open(url)
            return
        raise
    print(url)
    print("برای بستن این پنجره، Ctrl+C را بزن.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nبسته شد.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
