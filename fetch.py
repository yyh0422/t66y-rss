#!/usr/bin/env python3
"""抓取草榴社区技术讨论区（達蓋爾的旗幟，fid=16）最新帖子，生成 RSS 2.0。

用法: python3 fetch.py [输出路径，默认 ./feed.xml]
每 30 分钟跑一次即可。单次只请求一个列表页，请勿调高频率。
"""
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from xml.sax.saxutils import escape

BASE = "https://t66y.com"
SECTION_URL = f"{BASE}/thread0806.php?fid=16"
FEED_TITLE = "草榴社区 - 達蓋爾的旗幟（技术讨论区）"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TZ8 = timezone(timedelta(hours=8))


def fetch() -> str:
    req = urllib.request.Request(SECTION_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", errors="replace")
    # 站点输出的引号是反斜杠转义的，先归一化
    return raw.replace('\\"', '"').replace("\\'", "'")


def parse(data: str):
    items = []
    rows = re.findall(r'<tr class="tr3 t_one tac">(.*?)</tr>', data, re.S)
    for row in rows:
        m = re.search(r'<h3><a href="(/htm_data/[^"]+\.html)"[^>]*>(.*?)</a></h3>', row, re.S)
        if not m:
            continue
        href, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if not title:
            continue
        link = BASE + href

        author = ""
        am = re.search(r'class="bl">([^<>]{1,30})</a>', row)
        if am:
            author = am.group(1).strip()

        # 最后回复时间（unix 时间戳），没有就用原帖时间
        pub_ts = None
        lm = re.search(r'read\.php\?tid=\d+[^"\']*["\'][^>]*data-timestamp="(\d+)"', row)
        if lm:
            pub_ts = int(lm.group(1))
        else:
            om = re.search(r'data-timestamp="(\d+)s?"', row)
            if om:
                pub_ts = int(om.group(1))
        pub_date = format_datetime(datetime.fromtimestamp(pub_ts, TZ8)) if pub_ts else ""

        desc_parts = []
        if author:
            desc_parts.append(f"作者：{author}")
        desc_parts.append(f"原帖：{link}")
        desc = "\n".join(desc_parts).replace("]]>", "]]&gt;")
        items.append({
            "title": title,
            "link": link,
            "guid": link,
            "pubDate": pub_date,
            "description": desc,
        })
    # 去重保序
    seen, uniq = set(), []
    for it in items:
        if it["guid"] not in seen:
            seen.add(it["guid"])
            uniq.append(it)
    return uniq


def build_rss(items) -> str:
    now = format_datetime(datetime.now(TZ8))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "<channel>",
        f"<title>{escape(FEED_TITLE)}</title>",
        f"<link>{escape(SECTION_URL)}</link>",
        f"<description>{escape(FEED_TITLE)} 最新帖子（自建抓取，每 30 分钟更新）</description>",
        f"<lastBuildDate>{now}</lastBuildDate>",
        "<language>zh-cn</language>",
    ]
    for it in items:
        parts.append("<item>")
        parts.append(f"<title>{escape(it['title'])}</title>")
        parts.append(f"<link>{escape(it['link'])}</link>")
        parts.append(f"<guid isPermaLink=\"true\">{escape(it['guid'])}</guid>")
        if it["pubDate"]:
            parts.append(f"<pubDate>{it['pubDate']}</pubDate>")
        parts.append(f"<description><![CDATA[{it['description']}]]></description>")
        parts.append("</item>")
    parts += ["</channel>", "</rss>", ""]
    return "\n".join(parts)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "feed.xml"
    data = fetch()
    items = parse(data)
    if not items:
        raise SystemExit("解析到 0 个帖子，页面结构可能变了，放弃写入以免清空旧 feed")
    rss = build_rss(items)
    with open(out, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"OK: {len(items)} items -> {out}")


if __name__ == "__main__":
    main()
