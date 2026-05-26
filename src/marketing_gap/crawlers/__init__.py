"""Built-in data collection layer.

The marketing-gap-analyzer ships with first-party crawlers for the most common
Chinese social platforms used in competitive marketing analysis:

- :mod:`marketing_gap.crawlers.weibo`        — first-level comments via the
  ``weibo.com/ajax/statuses/buildComments`` endpoint (cookie required).
- :mod:`marketing_gap.crawlers.bilibili`     — wraps `MediaCrawler`_ to
  fetch B-station post comments.
- :mod:`marketing_gap.crawlers.xiaohongshu`  — wraps `MediaCrawler`_ to
  fetch RED-Note search results and detail comments.

All crawlers normalise their output into the user-comment schema consumed by
:mod:`marketing_gap.extractors.user`::

    {
      "source":   "微博评论" | "B站评论" | "小红书评论",
      "post_id":  "<unique comment id>",
      "note_id":  "<parent note / video / weibo id>",
      "content":  "<comment text>",
      "like":     <int, optional>,
      "url":      "<best-effort permalink, optional>"
    }

.. _MediaCrawler: https://github.com/NanmiCoder/MediaCrawler
"""

from .base import (
    CrawlerError,
    CookieFile,
    append_records,
    load_cookie_header,
    write_records,
)

__all__ = [
    "CrawlerError",
    "CookieFile",
    "append_records",
    "load_cookie_header",
    "write_records",
]
