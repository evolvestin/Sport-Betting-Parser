import os
from selenium import webdriver


def chrome(local):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
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
