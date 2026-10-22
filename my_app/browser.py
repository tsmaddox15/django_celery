"""Opening a browser and logging in to the automation site.

Everything specific to the site is in log_in(). It currently logs in to this
project's own Django admin, as a working example.
"""

from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

LOGIN_PATH = '/admin/login/'


def new_driver():
    options = webdriver.ChromeOptions()
    if settings.SELENIUM_REMOTE_URL:
        # The selenium container. Not headless, so you can watch it at http://localhost:7900.
        return webdriver.Remote(command_executor=settings.SELENIUM_REMOTE_URL, options=options)
    # Running on the host: a local Chrome, which Selenium Manager finds or downloads.
    options.add_argument('--headless=new')
    return webdriver.Chrome(options=options)


def log_in(driver):
    driver.get(settings.AUTOMATION_SITE_URL + LOGIN_PATH)
    driver.find_element(By.NAME, 'username').send_keys(settings.AUTOMATION_SITE_USERNAME)
    driver.find_element(By.NAME, 'password').send_keys(settings.AUTOMATION_SITE_PASSWORD)
    driver.find_element(By.CSS_SELECTOR, '[type=submit]').click()
    try:
        # The site keeps you on the login form until the login succeeds.
        WebDriverWait(driver, 30).until(lambda d: LOGIN_PATH not in d.current_url)
    except TimeoutException:
        raise RuntimeError(f'login to {settings.AUTOMATION_SITE_URL} failed') from None
