from collections import namedtuple

TIMEOUT = 3
URL_LIMIT = 10

DICTIONARIES_DIR = "charged_dict"

SITE = namedtuple("SITE", "URL TAG SELECTOR")
SITE.URL = "https://inosmi.ru"
SITE.TAG = "article"
SITE.SELECTOR = "index-main-news__article"

TEST_ADDRESS = [
    "https://inosmi.ru/politic/20210720/250151488.html",
    "https://lenta.ru/news/2021/07/20/destable/",
    "https://dvmn.org/media/filer_public/51/83/51830f54-7ec7-4702-847b-c5790ed3724c/gogol_nikolay_taras_bulba_-_bookscafenet.txt",
]
