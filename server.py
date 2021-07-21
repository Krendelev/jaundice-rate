from functools import partial

import aiohttp
import anyio
import pymorphy2
from aiohttp import web

from process_article import process_article
from settings import DICTIONARIES_DIR, URL_LIMIT
from text_tools import get_dictionary


def check_parameter(parameter):
    if not parameter:
        return "pass urls list in request"

    if len(parameter.split(",")) > URL_LIMIT:
        return f"too many urls in request, should be {URL_LIMIT} or less"

    return None


async def handle(request):
    parameter = request.query.get("urls")

    if error := check_parameter(parameter):
        return web.json_response({"error": error}, status=400)
        
    urls = parameter.split(",")

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
