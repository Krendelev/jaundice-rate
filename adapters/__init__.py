from . import dvmn_org
from . import inosmi_ru
from .exceptions import ArticleNotFound

__all__ = ["SANITIZERS", "ArticleNotFound"]

SANITIZERS = {
    "inosmi.ru": inosmi_ru.sanitize,
    "dvmn.org": dvmn_org.sanitize,
}
