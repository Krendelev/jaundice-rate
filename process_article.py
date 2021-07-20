import logging
import time
from contextlib import contextmanager
from enum import Enum
from functools import partial
from sys import modules
from urllib.parse import urljoin, urlparse

import aiohttp
import anyio
import pymorphy2
import pytest
from aiohttp.client_exceptions import ClientError
from bs4 import BeautifulSoup

from adapters import SANITIZERS
from settings import DICTIONARIES_DIR, SITE, TEST_ADDRESSES, TIMEOUT
from text_tools import calculate_jaundice_rate, get_dictionary, split_by_words

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


class ProcessingStatus(Enum):
    OK = "OK"
    FETCH_ERROR = "FETCH_ERROR"
    PARSING_ERROR = "PARSING_ERROR"
    TIMEOUT = "TIMEOUT"


@contextmanager
def timing(logger):
    try:
        start = time.monotonic()
        yield
    finally:
        elapsed = time.monotonic() - start
        logger.info(f"Анализ закончен за {elapsed:.2f} сек")


async def fetch(session, url):
    with anyio.fail_after(TIMEOUT):
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()


async def parse_frontpage(session, url):
    html = await fetch(session, url)
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all(SITE.TAG, class_=SITE.SELECTOR)
    return [urljoin(url, article.a["href"]) for article in articles]


async def process_article(session, morph, charged_words, url, results):
    rate, text = None, ""
    sitename = urlparse(url).netloc

    try:
        html = await fetch(session, url)
        sanitize = SANITIZERS[sitename]
        text = sanitize(html, plaintext=True)
        with timing(logger):
            article_words = await split_by_words(morph, text)
        rate = calculate_jaundice_rate(article_words, charged_words)
        status = ProcessingStatus.OK

    except ClientError:
        status = ProcessingStatus.FETCH_ERROR

    except TimeoutError:
        status = ProcessingStatus.TIMEOUT

    except KeyError:
        status = ProcessingStatus.PARSING_ERROR

    results.append(
        {"status": status.value, "url": url, "score": rate, "words_count": len(text)}
    )


async def main():
    morph = pymorphy2.MorphAnalyzer()
    charged_words = get_dictionary(DICTIONARIES_DIR)

    async with aiohttp.ClientSession() as session:
        articles = await parse_frontpage(session, SITE.URL)
        ratings = []
        article_processor = partial(
            process_article,
            session,
            morph,
            charged_words,
            results=ratings,
        )
        async with anyio.create_task_group() as tg:
            for url in articles:
                tg.start_soon(article_processor, url)

    return ratings


@pytest.mark.asyncio
async def test_process_article(monkeypatch):

    async def fake_parse_frontpage(session, url):
        return TEST_ADDRESSES

    monkeypatch.setattr(modules[__name__], "parse_frontpage", fake_parse_frontpage)

    results = await main()
    results = sorted(results, key=lambda result: result["url"])

    assert results[0]["status"] == "TIMEOUT"
    assert results[1]["status"] == "OK"
    assert 1.05 < results[1]["score"] < 1.10
    assert results[2]["status"] == "PARSING_ERROR"


if __name__ == "__main__":
    anyio.run(main)
