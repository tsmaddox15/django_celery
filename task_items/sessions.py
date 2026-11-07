"""One logged-in Selenium session per worker process.

The automations worker runs prefork with --concurrency 3: three processes, each
running one task at a time. Each process keeps its own session and reuses it for
every task it runs, so there are three sessions, reused across tasks, and never
shared by two tasks at once. (This relies on the prefork pool; a threads or
gevent pool runs several tasks per process and would share the session.)
"""

import logging
import os
from contextlib import contextmanager

from celery.signals import worker_process_shutdown
from selenium.common.exceptions import WebDriverException

from my_app.browser import log_in, new_driver

logger = logging.getLogger(__name__)

# This worker process's session, already logged in.
_driver = None


def _get_driver():
    global _driver
    if _driver is not None:
        try:
            # Fails if the session is gone: the browser crashed, or the selenium
            # container closed it after 5 idle minutes.
            _driver.current_url
        except WebDriverException:
            _driver = None
    if _driver is None:
        logger.info('opening a selenium session for worker process %s', os.getpid())
        driver = new_driver()
        try:
            log_in(driver)
        except Exception:
            driver.quit()
            raise
        _driver = driver
    return _driver


@worker_process_shutdown.connect
def _discard_driver(**kwargs):
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except WebDriverException:
            pass
        _driver = None


@contextmanager
def browser_session():
    """This process's logged-in session. If the task fails, the session is
    closed, in case the browser is what broke; the next task logs in afresh."""
    driver = _get_driver()
    try:
        yield driver
    except Exception:
        _discard_driver()
        raise
