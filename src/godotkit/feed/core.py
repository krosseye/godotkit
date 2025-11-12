import datetime
import logging
import xml.etree.ElementTree as ET
from abc import ABC
from typing import List, Optional, TypedDict

import httpx

from godotkit.constants import RSS_FETCHER_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class RSSArticle(TypedDict):
    """
    A single parsed RSS article.
    """

    title: str
    link: str
    summary: str
    author: str
    date: Optional[datetime.datetime]
    image_url: Optional[str]


class _BaseRSSFetcher(ABC):
    FEED_URL = "https://godotengine.org/rss.xml"
    DATE_FORMAT = "%a, %d %b %Y %H:%M:%S %z"
    NAMESPACE = {"dc": "http://purl.org/dc/elements/1.1/"}

    def _parse_feed(self, xml_content: bytes) -> List[RSSArticle]:
        rss_data: List[RSSArticle] = []

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.error(f"Failed to parse RSS feed: {e}")
            return []

        for item in root.findall(".//item"):
            raw_date_str = item.findtext("pubDate", default="")

            parsed_date: Optional[datetime.datetime]
            if raw_date_str:
                try:
                    parsed_date = datetime.datetime.strptime(
                        raw_date_str, self.DATE_FORMAT
                    )
                except ValueError as e:
                    logger.warning(f"Failed to parse date string '{raw_date_str}': {e}")
                    parsed_date = None
            else:
                parsed_date = None

            article_data: RSSArticle = {
                "title": item.findtext("title", default="No title"),
                "link": item.findtext("link", default="https://godotengine.org/blog/"),
                "summary": item.findtext("summary", default="No summary available"),
                "author": item.findtext(
                    "dc:creator", default="Unknown author", namespaces=self.NAMESPACE
                ),
                "date": parsed_date,
                "image_url": item.findtext("image", default=None),
            }
            rss_data.append(article_data)

        return rss_data


class RSSFetcher(_BaseRSSFetcher):
    """
    Handles fetching and parsing the Godot RSS feed synchronously.
    """

    def __init__(self):
        self.client = httpx.Client(
            timeout=RSS_FETCHER_TIMEOUT, headers={"User-Agent": USER_AGENT}
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def fetch_feed(self) -> Optional[List[RSSArticle]]:
        """
        Fetches the RSS feed from the network and parses it.

        Returns:
            A list of structured RSSArticle data.
        """
        logger.info(f"Fetching feed from network: {self.FEED_URL}...")
        try:
            response = self.client.get(self.FEED_URL)
            response.raise_for_status()

            if not response.content.strip():
                logger.warning("RSS feed is empty.")
                return []

            return self._parse_feed(response.content)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error fetching RSS feed: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Network Error fetching RSS feed: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return None


class AsyncRSSFetcher(_BaseRSSFetcher):
    """
    Handles fetching and parsing the Godot RSS feed asynchronously.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=RSS_FETCHER_TIMEOUT, headers={"User-Agent": USER_AGENT}
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def fetch_feed(self) -> Optional[List[RSSArticle]]:
        """
        Fetches the RSS feed from the network asynchronously and parses it.

        Returns:
            A list of structured RSSArticle data.
        """
        logger.info(f"Fetching feed from network: {self.FEED_URL}...")
        try:
            response = await self.client.get(self.FEED_URL)
            response.raise_for_status()

            if not response.content.strip():
                logger.warning("RSS feed is empty.")
                return []

            return self._parse_feed(response.content)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error fetching RSS feed: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Network Error fetching RSS feed: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return None
