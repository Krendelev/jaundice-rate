from functools import partial

import aiohttp
import anyio
import pymorphy2
from aiohttp import web

from process_article import process_article
from settings import DICTIONARIES_DIR, URL_LIMIT
from text_tools import get_dictionary


async def handle(request):
    try:
        param_name = next(iter(request.query))
    except StopIteration:
        pass
    urls = request.query[param_name].split(",")

    if len(urls) > URL_LIMIT:
        return web.json_response(
            {"error": f"too many urls in request, should be {URL_LIMIT} or less"},
            status=400,
        )

    async with aiohttp.ClientSession() as session:
        ratings = []
        article_processor = partial(
            process_article,
            session,
            request.app["morph"],
            request.app["charged_words"],
            results=ratings,
        )
        async with anyio.create_task_group() as tg:
            for url in urls:
                tg.start_soon(article_processor, url)

    return web.json_response(ratings)


if __name__ == "__main__":
    app = web.Application()
    app.add_routes([web.get("/", handle)])

    app["morph"] = pymorphy2.MorphAnalyzer()
    app["charged_words"] = get_dictionary(DICTIONARIES_DIR)

    web.run_app(app)
