"""
Tests del parseo de XML Atom. No hacen peticiones de red: usan un feed
de ejemplo hardcodeado con la misma forma que devuelve export.arxiv.org.
"""

from backend.crawler.arxiv_client import parse_entries

SAMPLE_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <published>2017-06-12T17:57:34Z</published>
    <updated>2023-08-02T00:41:18Z</updated>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on
    complex recurrent or convolutional neural networks...</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <link href="http://arxiv.org/abs/1706.03762v5" rel="alternate"/>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762v5" rel="related"/>
    <category term="cs.CL"/>
    <category term="cs.LG"/>
  </entry>
</feed>
"""


def test_parse_entries_extracts_all_fields():
    papers = parse_entries(SAMPLE_ATOM_FEED)
    assert len(papers) == 1

    p = papers[0]
    assert p["arxiv_id"] == "1706.03762"  # sin prefijo "arxiv:" ni versión "v5"
    assert p["title"] == "Attention Is All You Need"
    assert "Ashish Vaswani" in p["authors"]
    assert "Noam Shazeer" in p["authors"]
    assert p["categories"] == "cs.CL, cs.LG"
    assert p["pdf_url"] == "http://arxiv.org/pdf/1706.03762v5"
    assert p["published"].startswith("2017-06-12")


def test_parse_entries_handles_empty_feed():
    empty_feed = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    assert parse_entries(empty_feed) == []


def test_parse_entries_skips_entries_without_id():
    broken_feed = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Paper sin ID</title></entry>
    </feed>"""
    assert parse_entries(broken_feed) == []
