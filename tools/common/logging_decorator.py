import logging
from functools import wraps
from time import time
from typing import Any

logging.basicConfig(level=logging.INFO)


def logging_decorator(func) -> Any:
    """decorator
    :param func: 対象関数
    :returns: ラップした関数
    """

    @wraps(func)
    def __decorator(*args, **kwargs) -> object:
        """横断的 ログ出力
        :param args: 引数
        :param kwargs: キーワード変数
        :returns: funcの実行結果
        """

        logging.info("### Start " + func.__name__ + " ###")
        start = time()
        result = func(*args, **kwargs)
        end = time()
        logging.info(func.__name__ + " : %f sec" % (end - start))
        logging.info("### End " + func.__name__ + " ###")
        return result

    return __decorator
