#!/usr/bin/env python3
"""AirbnbのiCalフィードから、hota.life埋め込み用の空室カレンダーHTMLを生成する。

使い方:
    HOTA_ICAL_URL='https://www.airbnb.jp/calendar/ical/....ics?t=...' \
        python3 tools/build_calendar.py

Airbnbのカレンダーで押さえられている日はそのまま満室（×）として表示する。

iCalフィードには予約詳細URLと電話番号下4桁が含まれるため、絶対にそのまま公開しない。
このスクリプトが取り出すのは「その夜が埋まっているか」だけで、出力HTMLに
予約者情報・予約URL・ブロック理由は一切含まれない。
"""

import datetime as dt
import html
import os
import sys
import urllib.request
from calendar import Calendar

MONTHS_AHEAD = 6
FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSeqPbAYIRzZL8vsAZAhSkDYFoePuwRC-d9iFGjs8KQYEsDIng/viewform"
)
JST = dt.timezone(dt.timedelta(hours=9))
WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]


def fetch_ical(url):
    req = urllib.request.Request(url, headers={"User-Agent": "hota-calendar/1.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", errors="replace")


def unfold(text):
    """iCalの折り返し行（次行が空白始まり）を1行に戻す。"""
    lines = []
    for raw in text.splitlines():
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def parse_date(value):
    return dt.datetime.strptime(value.strip()[:8], "%Y%m%d").date()


def busy_nights(ical_text):
    """埋まっている「夜」の集合を返す。

    AirbnbのVEVENTはDTENDが排他的（チェックアウト日は含まない）ため、
    ふさがっている夜は DTSTART 〜 DTEND-1 日。
    """
    nights = set()
    start = end = None
    in_event = False
    for line in unfold(ical_text):
        if line.startswith("BEGIN:VEVENT"):
            in_event, start, end = True, None, None
        elif line.startswith("END:VEVENT"):
            if start and end:
                day = start
                while day < end:
                    nights.add(day)
                    day += dt.timedelta(days=1)
            in_event = False
        elif in_event and line.startswith("DTSTART"):
            start = parse_date(line.split(":", 1)[1])
        elif in_event and line.startswith("DTEND"):
            end = parse_date(line.split(":", 1)[1])
    return nights


def month_html(year, month, nights, today):
    cal = Calendar(firstweekday=0)  # 月曜始まり
    cells = []
    for day in cal.itermonthdates(year, month):
        if day.month != month:
            cells.append('<td class="pad"></td>')
            continue
        classes = []
        if day < today:
            classes.append("past")
            mark = ""
        elif day in nights:
            classes.append("busy")
            mark = "×"
        else:
            classes.append("open")
            mark = "○"
        if day == today:
            classes.append("today")
        cells.append(
            '<td class="%s"><span class="d">%d</span><span class="m">%s</span></td>'
            % (" ".join(classes), day.day, mark)
        )

    rows = "".join(
        "<tr>%s</tr>" % "".join(cells[i : i + 7]) for i in range(0, len(cells), 7)
    )
    head = "".join(
        '<th class="%s">%s</th>'
        % ("sat" if i == 5 else "sun" if i == 6 else "", WEEKDAY_JA[i])
        for i in range(7)
    )
    return (
        '<section class="month"><h2>%d年%d月</h2>'
        '<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></section>'
        % (year, month, head, rows)
    )


def build(nights, today, updated):
    months = []
    year, month = today.year, today.month
    for _ in range(MONTHS_AHEAD):
        months.append(month_html(year, month, nights, today))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)

    return TEMPLATE % {
        "months": "\n".join(months),
        "updated": html.escape(updated.strftime("%Y年%-m月%-d日 %H:%M")),
        "form_url": html.escape(FORM_URL, quote=True),
    }


TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>保田の家 空室カレンダー</title>
<style>
  :root {
    --ink: #3a3733;
    --muted: #8d867e;
    --line: #e6e0d8;
    --open: #4a7c59;
    --busy: #c25a4a;
    --bg: #fdfcfa;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 16px;
    background: var(--bg); color: var(--ink);
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif;
    -webkit-text-size-adjust: 100%%;
  }
  .legend {
    display: flex; flex-wrap: wrap; align-items: center; gap: 16px;
    font-size: 13px; color: var(--muted);
    padding-bottom: 12px; margin-bottom: 4px;
    border-bottom: 1px solid var(--line);
  }
  .legend b { font-weight: 600; }
  .legend .o { color: var(--open); }
  .legend .x { color: var(--busy); }
  .grid {
    display: grid; gap: 20px 24px;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    margin: 16px 0 20px;
  }
  .month h2 {
    margin: 0 0 8px; font-size: 15px; font-weight: 600; letter-spacing: .04em;
  }
  table { width: 100%%; border-collapse: collapse; table-layout: fixed; }
  th {
    font-size: 11px; font-weight: 500; color: var(--muted);
    padding-bottom: 6px;
  }
  th.sat { color: #6a8caf; }
  th.sun { color: #b8837c; }
  td {
    height: 40px; text-align: center; vertical-align: middle;
    border-top: 1px solid var(--line); padding: 2px 0;
  }
  td.pad { border-top: none; }
  .d { display: block; font-size: 11px; color: var(--muted); line-height: 1.2; }
  .m { display: block; font-size: 15px; line-height: 1.2; }
  td.open .m { color: var(--open); }
  td.busy .m { color: var(--busy); }
  td.past { opacity: .3; }
  td.past .m::after { content: "–"; color: var(--muted); }
  td.today { background: #f3efe7; border-radius: 4px; }
  .note {
    font-size: 12px; line-height: 1.7; color: var(--muted);
    border-top: 1px solid var(--line); padding-top: 12px;
  }
  .cta { margin: 4px 0 16px; }
  .cta a {
    display: inline-block; padding: 11px 26px;
    background: var(--ink); color: #fff; text-decoration: none;
    font-size: 14px; letter-spacing: .06em; border-radius: 2px;
  }
</style>
</head>
<body>
  <div class="legend">
    <span><b class="o">○</b> 空室</span>
    <span><b class="x">×</b> 満室</span>
    <span>最終更新 %(updated)s</span>
  </div>

  <div class="grid">
%(months)s
  </div>

  <div class="cta">
    <a href="%(form_url)s" target="_blank" rel="noopener">予約リクエストを送る</a>
  </div>

  <p class="note">
    ○×は「その日に宿泊する（その夜）」の空き状況です。チェックアウトのみの日は空室として表示されます。<br>
    表示は1時間ごとに自動更新しています。更新の間に他サイトで予約が入る場合があるため、
    最終的な可否はリクエスト送信後のご返信にてご確認ください。
  </p>
</body>
</html>
"""


def main():
    url = os.environ.get("HOTA_ICAL_URL")
    if not url:
        sys.exit("HOTA_ICAL_URL が未設定です。AirbnbのiCal書き出しURLを渡してください。")

    nights = busy_nights(fetch_ical(url))
    if not nights:
        # フィード取得は成功したが空、はカレンダー全面○になる事故なので止める
        sys.exit("iCalから予約が1件も取得できませんでした。URLの失効を確認してください。")

    now = dt.datetime.now(JST)
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build(nights, now.date(), now))
    print("%s を生成しました（満室: %d泊）" % (out_path, len(nights)))


if __name__ == "__main__":
    main()
