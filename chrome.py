import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
user_agent = 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' \
             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36'


def chrome(local):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(user_agent)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    preferences = {'directory_upgrade': True,
                   'safebrowsing.enabled': True,
                   'download.default_directory': os.path.abspath(os.curdir)}
    chrome_options.add_experimental_option('prefs', preferences)
    if local:
        return webdriver.Chrome(executable_path='chromedriver.exe', options=chrome_options)
    else:
        chrome_options.add_argument('--headless')
        from webdriver_manager.chrome import ChromeDriverManager
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
