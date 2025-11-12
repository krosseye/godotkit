import datetime
from unittest.mock import MagicMock

import httpx
import pytest

from godotkit.feed.core import AsyncRSSFetcher, RSSFetcher

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Godot Engine - News</title>
    <link>https://godotengine.org/news</link>
    <description>The latest news from the Godot Engine development.</description>
    <item>
      <title>Godot 4.2 is released!</title>
      <link>https://godotengine.org/article/godot-4-2-is-released/</link>
      <pubDate>Fri, 15 Sep 2023 12:00:00 +0000</pubDate>
      <dc:creator>Juan Linietsky</dc:creator>
      <summary>Summary of Godot 4.2 features.</summary>
      <image>https://godotengine.org/storage/app/media/blog/4.2/godot_4.2_release_banner.png</image>
    </item>
    <item>
      <title>Dev snapshot: Godot 4.3 dev 1</title>
      <link>https://godotengine.org/article/dev-snapshot-godot-4-3-dev-1/</link>
      <pubDate>Mon, 01 Jan 2024 10:00:00 +0000</pubDate>
      <dc:creator>Rémi Verschelde</dc:creator>
      <summary>First development build for Godot 4.3.</summary>
    </item>
    <item>
      <title>A post with missing author and image</title>
      <link>https://godotengine.org/article/missing-fields/</link>
      <pubDate>Tue, 02 Jan 2024 11:00:00 +0000</pubDate>
      <summary>This post has no author or image.</summary>
    </item>
    <item>
      <title>Post with invalid date</title>
      <link>https://godotengine.org/article/invalid-date/</link>
      <pubDate>Invalid Date String</pubDate>
      <dc:creator>Unknown</dc:creator>
      <summary>This post has an invalid date.</summary>
    </item>
  </channel>
</rss>
"""

EXPECTED_ARTICLES = [
    {
        "title": "Godot 4.2 is released!",
        "link": "https://godotengine.org/article/godot-4-2-is-released/",
        "summary": "Summary of Godot 4.2 features.",
        "author": "Juan Linietsky",
        "date": datetime.datetime(2023, 9, 15, 12, 0, 0, tzinfo=datetime.timezone.utc),
        "image_url": "https://godotengine.org/storage/app/media/blog/4.2/godot_4.2_release_banner.png",
    },
    {
        "title": "Dev snapshot: Godot 4.3 dev 1",
        "link": "https://godotengine.org/article/dev-snapshot-godot-4-3-dev-1/",
        "summary": "First development build for Godot 4.3.",
        "author": "Rémi Verschelde",
        "date": datetime.datetime(2024, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "image_url": None,
    },
    {
        "title": "A post with missing author and image",
        "link": "https://godotengine.org/article/missing-fields/",
        "summary": "This post has no author or image.",
        "author": "Unknown author",
        "date": datetime.datetime(2024, 1, 2, 11, 0, 0, tzinfo=datetime.timezone.utc),
        "image_url": None,
    },
    {
        "title": "Post with invalid date",
        "link": "https://godotengine.org/article/invalid-date/",
        "summary": "This post has an invalid date.",
        "author": "Unknown",
        "date": None,
        "image_url": None,
    },
]


@pytest.fixture
def mock_httpx_client(mocker):
    mock_client = mocker.MagicMock(spec=httpx.Client)
    mocker.patch("httpx.Client", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_httpx_async_client(mocker):
    mock_async_client = mocker.AsyncMock(spec=httpx.AsyncClient)
    mocker.patch("httpx.AsyncClient", return_value=mock_async_client)
    return mock_async_client


class TestRSSFetcher:
    @pytest.fixture
    def rss_fetcher(self, mock_httpx_client):
        return RSSFetcher()

    def test_fetch_feed_returns_articles_on_success(
        self, rss_fetcher, mock_httpx_client, caplog
    ):
        mock_response = MagicMock()
        mock_response.content = SAMPLE_RSS_XML.encode("utf-8")
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.get.return_value = mock_response

        with caplog.at_level("WARNING"):
            articles = rss_fetcher.fetch_feed()

        assert articles == EXPECTED_ARTICLES
        mock_httpx_client.get.assert_called_once_with(rss_fetcher.FEED_URL)
        mock_response.raise_for_status.assert_called_once()
        assert any(
            "Failed to parse date string 'Invalid Date String'" in record.message
            for record in caplog.records
        )

    def test_fetch_feed_handles_empty_feed(self, rss_fetcher, mock_httpx_client):
        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.get.return_value = mock_response

        articles = rss_fetcher.fetch_feed()

        assert articles == []
        mock_httpx_client.get.assert_called_once_with(rss_fetcher.FEED_URL)

    def test_fetch_feed_handles_http_status_error(
        self, rss_fetcher, mock_httpx_client, caplog
    ):
        mock_httpx_client.get.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=httpx.Request("GET", rss_fetcher.FEED_URL),
            response=httpx.Response(404),
        )

        with caplog.at_level("ERROR"):
            articles = rss_fetcher.fetch_feed()

        assert articles is None
        assert "HTTP Error fetching RSS feed" in caplog.text
        mock_httpx_client.get.assert_called_once_with(rss_fetcher.FEED_URL)

    def test_fetch_feed_handles_request_error(
        self, rss_fetcher, mock_httpx_client, caplog
    ):
        mock_httpx_client.get.side_effect = httpx.RequestError(
            "Connection refused", request=httpx.Request("GET", rss_fetcher.FEED_URL)
        )

        with caplog.at_level("ERROR"):
            articles = rss_fetcher.fetch_feed()

        assert articles is None
        assert "Network Error fetching RSS feed" in caplog.text
        mock_httpx_client.get.assert_called_once_with(rss_fetcher.FEED_URL)

    def test_fetch_feed_handles_xml_parse_error(
        self, rss_fetcher, mock_httpx_client, caplog
    ):
        mock_response = MagicMock()
        mock_response.content = b"This is not valid XML"
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.get.return_value = mock_response

        with caplog.at_level("ERROR"):
            articles = rss_fetcher.fetch_feed()

        assert articles == []
        assert "Failed to parse RSS feed" in caplog.text
        mock_httpx_client.get.assert_called_once_with(rss_fetcher.FEED_URL)

    def test_rss_fetcher_closes_client_on_exit(self, mock_httpx_client):
        with RSSFetcher() as fetcher:
            mock_response = MagicMock()
            mock_response.content = b""
            mock_response.raise_for_status.return_value = None
            mock_httpx_client.get.return_value = mock_response
            fetcher.fetch_feed()
        mock_httpx_client.close.assert_called_once()


class TestAsyncRSSFetcher:
    @pytest.fixture
    def async_rss_fetcher(self, mock_httpx_async_client):
        return AsyncRSSFetcher()

    @pytest.mark.asyncio
    async def test_fetch_feed_returns_articles_on_success_async(
        self, async_rss_fetcher, mock_httpx_async_client, caplog
    ):
        mock_response = MagicMock()
        mock_response.content = SAMPLE_RSS_XML.encode("utf-8")
        mock_response.raise_for_status.return_value = None
        mock_httpx_async_client.get.return_value = mock_response

        with caplog.at_level("WARNING"):
            articles = await async_rss_fetcher.fetch_feed()

        assert articles == EXPECTED_ARTICLES
        mock_httpx_async_client.get.assert_called_once_with(async_rss_fetcher.FEED_URL)
        mock_response.raise_for_status.assert_called_once()
        assert any(
            "Failed to parse date string 'Invalid Date String'" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_fetch_feed_handles_empty_feed_async(
        self, async_rss_fetcher, mock_httpx_async_client
    ):
        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None
        mock_httpx_async_client.get.return_value = mock_response

        articles = await async_rss_fetcher.fetch_feed()

        assert articles == []
        mock_httpx_async_client.get.assert_called_once_with(async_rss_fetcher.FEED_URL)

    @pytest.mark.asyncio
    async def test_fetch_feed_handles_http_status_error_async(
        self, async_rss_fetcher, mock_httpx_async_client, caplog
    ):
        mock_httpx_async_client.get.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=httpx.Request("GET", async_rss_fetcher.FEED_URL),
            response=httpx.Response(404),
        )

        with caplog.at_level("ERROR"):
            articles = await async_rss_fetcher.fetch_feed()

        assert articles is None
        assert "HTTP Error fetching RSS feed" in caplog.text
        mock_httpx_async_client.get.assert_called_once_with(async_rss_fetcher.FEED_URL)

    @pytest.mark.asyncio
    async def test_fetch_feed_handles_request_error_async(
        self, async_rss_fetcher, mock_httpx_async_client, caplog
    ):
        mock_httpx_async_client.get.side_effect = httpx.RequestError(
            "Connection refused",
            request=httpx.Request("GET", async_rss_fetcher.FEED_URL),
        )

        with caplog.at_level("ERROR"):
            articles = await async_rss_fetcher.fetch_feed()

        assert articles is None
        assert "Network Error fetching RSS feed" in caplog.text
        mock_httpx_async_client.get.assert_called_once_with(async_rss_fetcher.FEED_URL)

    @pytest.mark.asyncio
    async def test_fetch_feed_handles_xml_parse_error_async(
        self, async_rss_fetcher, mock_httpx_async_client, caplog
    ):
        mock_response = MagicMock()
        mock_response.content = b"This is not valid XML"
        mock_response.raise_for_status.return_value = None
        mock_httpx_async_client.get.return_value = mock_response

        with caplog.at_level("ERROR"):
            articles = await async_rss_fetcher.fetch_feed()

        assert articles == []
        assert "Failed to parse RSS feed" in caplog.text
        mock_httpx_async_client.get.assert_called_once_with(async_rss_fetcher.FEED_URL)

    @pytest.mark.asyncio
    async def test_async_rss_fetcher_closes_client_on_aexit_async(
        self, mock_httpx_async_client
    ):
        async with AsyncRSSFetcher() as fetcher:
            mock_response = MagicMock()
            mock_response.content = b""
            mock_response.raise_for_status.return_value = None
            mock_httpx_async_client.get.return_value = mock_response

            await fetcher.fetch_feed()

        mock_httpx_async_client.aclose.assert_called_once()
