import logging
import time
from contextlib import contextmanager
from io import StringIO
from urllib.parse import urljoin, urlparse

import aiohttp
import anyio
import pymorphy2
from aiohttp.client_exceptions import ClientError
from bs4 import BeautifulSoup

from adapters import SANITIZERS
from settings import DICTIONARIES_DIR, SITE, TIMEOUT
from text_tools import calculate_jaundice_rate, get_dictionary, split_by_words

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


@contextmanager
def timing(log_stream):
    try:
        logger.addHandler(logging.StreamHandler(stream=log_stream))
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
    return {article.h1.string: urljoin(url, article.a["href"]) for article in articles}


async def process_article(session, morph, charged_words, url, title, results):
    rate, text = None, ""
    log_stream = StringIO()

    sitename = urlparse(url).netloc
    sanitize = SANITIZERS.get(sitename)
    if sanitize:
        try:
            html = await fetch(session, url)
            text = sanitize(html, plaintext=True)
            with timing(log_stream):
                article_words = await split_by_words(morph, text)
            rate = calculate_jaundice_rate(article_words, charged_words)
            status = "OK"
        except ClientError:
            title = "URL does not exist"
            status = "FETCH_ERROR"
        except TimeoutError:
            status = "TIMEOUT"

    else:
        title = f"Статья на {sitename}"
        status = "PARSING_ERROR"

    results.append(
        f"Заголовок: {title}\nСтатус: {status}\nРейтинг: {rate}\n \
        Слов в статье: {len(text)}\n{log_stream.getvalue()}"
    )


async def main():
    morph = pymorphy2.MorphAnalyzer()
    charged_words = get_dictionary(DICTIONARIES_DIR)

    async with aiohttp.ClientSession() as session:
        articles = await parse_frontpage(session, SITE.URL)
        ratings = []
        async with anyio.create_task_group() as tg:
            for title in articles:
                tg.start_soon(
                    process_article,
                    session,
                    morph,
                    charged_words,
                    articles[title],
                    title,
                    ratings,
                )
    for rating in ratings:
        print(rating)


if __name__ == "__main__":
    anyio.run(main)
