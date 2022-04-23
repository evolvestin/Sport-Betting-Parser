import os
from selenium import webdriver
from fake_useragent import UserAgent


def chrome(local):
    # agent = UserAgent(use_cache_server=False)
    # print('fake', agent.chrome)
    user = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument(f"user-agent={agent.chrome}")
    chrome_options.add_argument(f"user-agent={user}")
    print('fake-true', user)
    preferences = {'directory_upgrade': True,
                   'safebrowsing.enabled': True,
                   'download.default_directory': os.path.abspath(os.curdir)}
    chrome_options.add_experimental_option('prefs', preferences)
    if local:
        os.environ['CHROMEDRIVER_PATH'] = 'chromedriver.exe'
    else:
        chrome_options.binary_location = os.environ.get('GOOGLE_CHROME_BIN')
        chrome_options.add_argument('--headless')
    return webdriver.Chrome(executable_path=os.environ.get('CHROMEDRIVER_PATH'), options=chrome_options)
