import os
import re
import objects
import _thread
import gspread
from SQL import SQL
from time import sleep
from chrome import chrome
from telebot import TeleBot
from objects import bold, time_now
from string import ascii_uppercase
from selenium.webdriver.common.by import By
from datetime import datetime, timezone, timedelta
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
# =================================================================================================================
stamp1 = time_now()
html = {'{': '&#123;', '<': '&#60;', '}': '&#125;', '\'': '&#39;'}


def html_secure(text, reverse=None):
    for pattern, value in html.items():
        text = re.sub(pattern, value, str(text)) if reverse is None else re.sub(value, pattern, str(text))
    return text


def robo_db_creation():
    db = SQL(db_path)
    spreadsheet = gspread.service_account('google.json').open('SportBettingDB')
    users = spreadsheet.worksheet('robo').get('A1:Z50000', major_dimension='ROWS')
    raw_columns = db.create_table('main', users.pop(0), additional=True)
    users_ids, columns = db.upload('main', raw_columns, users, delta=3)
    _zero_row = db.get_row(0)
    db.close()
    return _zero_row, ['id', *users_ids], columns


db_path = 'db/database.db'
objects.environmental_files()
os.makedirs('db', exist_ok=True)
tz = timezone(timedelta(hours=3))
bot = TeleBot(os.environ['TOKEN'])
zero_row, google_rows_ids, main_columns = robo_db_creation()
Auth = objects.AuthCentre(ID_DEV=-1001312302092, DEV_TOKEN=os.environ['DEV_TOKEN'])
bets = {'П1': 'П1', 'П2': 'П2', '12': 'Победа (1 или 2)', '1X': 'Двойной исход (1X)', 'X2': 'Двойной исход (X2)'}
# =================================================================================================================


def iter_post(record):
    score = re.sub(r'\(.*?\)', '', record['score']).strip()
    play_time = datetime.fromtimestamp(record['start_time'], tz)
    bet, now, title, alt_bet, coefficient_text = record['bet'], datetime.now(tz), '⏱⏱⏱', '', ''
    percents = {n: int(re.sub(r'\D', '', str(record[f'percent_{n}'])) or '0') for n in ['1', '2', 'x']}

    if record['bet'] == '12' and percents['1'] != percents['2']:
        record['bet'] = 'П1' if percents['1'] > percents['2'] else 'П2'
        bet = record['bet']

    elif record['bet'] in ['П1', 'П2']:
        key = re.sub(r'\D', '', record['bet'])
        coefficient_text = f"КФ: {record[f'coefficient_{key}']}\n" if record[f'coefficient_{key}'] else ''

    elif record['bet'] in ['1X', 'X2']:
        key = re.sub(r'\D', '', record['bet'])
        win_coefficient = record[f'coefficient_{key}'] or ''
        record['bet'] = 'П1' if record['bet'] == '1X' else 'П2'
        alt_bet += f" {bold(f'({percents[key]}%)')}" if percents[key] else ''
        alt_bet += f"\n💰 Ставка: Ничья ({percents['x']}%)" if percents['x'] else ''
        coefficient_text = f"КФ {record['bet']}: {win_coefficient}\n" if win_coefficient else ''
        coefficient_text += f"КФ Ничья: {record['coefficient_x']}\n" if record['coefficient_x'] else ''

    if score != '- : -' and (play_time + timedelta(hours=2.5)) < now:
        split = [int(re.sub(r'\D', '', element) or '0') for element in score.split(':')]
        if len(split) == 2:
            if bet == 'П1':
                title = '✅✅✅' if split[0] > split[1] else '❌❌❌'
            elif bet == 'П2':
                title = '✅✅✅' if split[1] > split[0] else '❌❌❌'
            elif bet == '1X':
                title = '✅✅✅' if split[0] >= split[1] else '❌❌❌'
            elif bet == 'X2':
                title = '✅✅✅' if split[1] >= split[0] else '❌❌❌'
            else:
                title = '✅✅✅' if split[0] != split[1] else '❌❌❌'
        elif score == 'отм':
            score, title = 'Отменён', '⚠⚠⚠'

    text = f"{title}\n" \
           f"⚽ {record['name']}\n" \
           f"⏱ {play_time.strftime('%H:%M')}\n" \
           f"🧾 Счёт матча: {bold(score)}\n" \
           f"{coefficient_text}" \
           f"💰 Ставка: {bold(bets.get(record['bet'], 'Нет'))}{alt_bet}"
    return text


def handler(driver: chrome, old: bool = False):
    db = SQL('db/database.db')
    driver.set_window_size(1200, 1200)
    driver.get(os.environ.get('link'))
    try:
        WebDriverWait(driver, 20).until(ec.presence_of_element_located((By.TAG_NAME, 'tbody')))
    except IndexError and Exception:
        driver.save_screenshot('screen.png')
        with open('screen.png', 'rb') as file:
            Auth.bot.send_photo(-1001312302092, file)
        os.remove('screen.png')
    body = driver.find_element(By.TAG_NAME, 'tbody')

    if old:
        before = datetime.now(tz) - timedelta(days=1)
        for label in driver.find_elements(By.TAG_NAME, 'label'):
            if label.text == before.strftime('%d-%m'):
                label.click()
                break
        sleep(5)

    for tr in body.find_elements(By.TAG_NAME, 'tr'):
        coefficient_1, coefficient_2, coefficient_x = None, None, None
        odds = tr.find_elements(By.CLASS_NAME, f"{os.environ.get('tag1')}__odd")
        bet = tr.find_element(By.CLASS_NAME, f"{os.environ.get('tag1')}__bet").text
        title = tr.find_element(By.CLASS_NAME, f"{os.environ.get('tag1')}__teams").text
        percents = tr.find_elements(By.CLASS_NAME, f"{os.environ.get('tag1')}__percent")
        start_time = tr.find_element(By.CLASS_NAME, f"{os.environ.get('tag1')}__time").text
        game_id, percent_1, percent_2, percent_x = tr.get_attribute('data-eventid'), None, None, None

        if len(percents) == 3:
            percent_1 = percents[0].text or None
            percent_x = percents[1].text or None
            percent_2 = percents[2].text or None

        if len(odds) == 3:
            coefficient_1 = odds[0].text if odds[0].text != '0.00' else None
            coefficient_x = odds[1].text if odds[1].text != '0.00' else None
            coefficient_2 = odds[2].text if odds[2].text != '0.00' else None

        tds = tr.find_elements(By.TAG_NAME, 'td')
        for td in tds:
            score = td.get_attribute('data-res')
            if score:
                record = db.get_row(game_id)
                if record:
                    if record['score'] != score or \
                            record['percent_1'] != percent_1 or \
                            record['percent_x'] != percent_x or \
                            record['percent_2'] != percent_2 or \
                            record['coefficient_1'] != coefficient_1 or \
                            record['coefficient_x'] != coefficient_x or \
                            record['coefficient_2'] != coefficient_2:
                        db.update('main', game_id, {
                            'name': title,
                            'score': score,
                            'percent_1': percent_1,
                            'percent_x': percent_x,
                            'percent_2': percent_2,
                            'coefficient_1': coefficient_1,
                            'coefficient_x': coefficient_x,
                            'coefficient_2': coefficient_2})
                else:
                    if old is False:
                        now, update = datetime.now(tz), {}
                        posting = True if score == '- : -' else None
                        play_time = datetime.fromisoformat(f"{now.strftime('%Y-%m-%d')} {start_time}:00+03:00")
                        record = {
                            'bet': bet,
                            'id': game_id,
                            'ended': None,
                            'score': score,
                            'post_id': None,
                            'percent_1': percent_1,
                            'percent_x': percent_x,
                            'percent_2': percent_2,
                            'name': html_secure(title),
                            'coefficient_1': coefficient_1,
                            'coefficient_x': coefficient_x,
                            'coefficient_2': coefficient_2,
                            'start_time': play_time.timestamp(),
                            'post_update': zero_row['post_update']}
                        db.create_row(record, google_update=False)
                        try:
                            coefficient = None
                            if bet in ['1X', 'X2']:
                                coefficient = coefficient_1 if bet == '1X' else coefficient_2
                            elif bet == '12' and percent_1 != percent_2:
                                coefficient = coefficient_1 if percents['1'] > percents['2'] else coefficient_2
                            elif bet in ['П1', 'П2']:
                                coefficient = coefficient_1 if bet == 'П1' else coefficient_2
                            fl_coefficient = float(coefficient) if coefficient else 0
                            posting = posting if fl_coefficient >= 1.4 else None
                        except IndexError and Exception:
                            pass

                        if posting:
                            try:
                                text = iter_post(record)
                                post = bot.send_message(os.environ['channel_id'], text,
                                                        disable_web_page_preview=True, parse_mode='HTML')
                                update = {'post_id': post.id, 'post_update': time_now(), 'post_status': '👀'}
                                sleep(60)
                            except IndexError and Exception:
                                Auth.dev.executive(None)
                        db.update('main', game_id, update)
    db.close()


def post_ender():
    while True:
        try:
            db = SQL(db_path)
            records = db.get_expired(datetime.now(tz) - timedelta(hours=2.5))
            print(f"Заканчиваем посты: {[i['post_id'] for i in records]}") if len(records) > 0 else None
            for record in records:
                db.update('main', record['id'], {'ended': '🔒', 'post_update': 1262293200})
            db.close()
            sleep(60)
        except IndexError and Exception:
            Auth.dev.thread_except()


def auto_reboot():
    reboot = None
    while True:
        try:
            sleep(30)
            date = datetime.now(tz)
            if date.strftime('%H') == '01' and date.strftime('%M') == '59':
                reboot = True
                while date.strftime('%M') == '59':
                    sleep(1)
                    date = datetime.now(tz)
            if reboot:
                reboot = None
                text, _ = Auth.logs.reboot()
                Auth.dev.printer(text)
        except IndexError and Exception:
            Auth.dev.thread_except()


def parser():
    counter = 0
    while True:
        try:
            driver = chrome(os.environ.get('local'))
        except IndexError and Exception:
            driver = None
            Auth.dev.thread_except()

        try:
            counter += 1
            handler(driver, old=counter % 4 == 0) if driver else None
            driver.close() if driver else None
            sleep(300)
        except IndexError and Exception:
            try:
                driver.close() if driver else None
            except IndexError and Exception:
                pass
            Auth.dev.thread_except()


def post_updater():
    while True:
        try:
            db = SQL(db_path)
            records = db.get_posts()
            print(f"Обновляем посты: {[i['post_id'] for i in records]}") if len(records) > 0 else None
            for record in records:
                update = {'post_update': time_now(), 'post_status': '👀'}
                try:
                    bot.edit_message_text(chat_id=os.environ['channel_id'],
                                          text=iter_post(record), message_id=record['post_id'],
                                          disable_web_page_preview=True, parse_mode='HTML')
                except IndexError and Exception as error:
                    update = {}
                    if 'exactly the same' not in str(error) and 'message to edit not found' not in str(error):
                        Auth.dev.executive(None)
                    else:
                        update = {'post_update': time_now(), 'post_status': '👀'}
                        if 'message to edit not found' in str(error):
                            update.update({'post_status': '🔇'})

                if update:
                    db.update('main', record['id'], update)
                    print(f"Пост обновлен: {record['post_id']} ({record['id']})")
                sleep(25)
            db.close()
            sleep(5)
        except IndexError and Exception:
            Auth.dev.thread_except()


def google_update():
    global google_rows_ids
    while True:
        try:
            sleep(2)
            db = SQL(db_path)
            records = db.get_updates()
            if len(records) > 0:
                client = gspread.service_account('google.json')
                worksheet = client.open('SportBettingDB').worksheet('robo')
                for record in records:
                    del record['updates']
                    if str(record['id']) in google_rows_ids:
                        text = 'обновлена'
                        row = google_rows_ids.index(str(record['id'])) + 1
                    else:
                        text = 'добавлена'
                        row = len(google_rows_ids) + 1
                        google_rows_ids.append(str(record['id']))
                    google_row = f'A{row}:{ascii_uppercase[len(record)-1]}{row}'

                    try:
                        user_range = worksheet.range(google_row)
                    except IndexError and Exception as error:
                        if 'exceeds grid limits' in str(error):
                            worksheet.add_rows(1000)
                            user_range = worksheet.range(google_row)
                            sleep(5)
                        else:
                            raise error

                    for index, value, col_type in zip(range(len(record)), record.values(), main_columns):
                        value = Auth.time(value, form='iso', sep='_') if '<DATE>' in col_type else value
                        value = 'None' if value is None else value
                        user_range[index].value = value
                    worksheet.update_cells(user_range)
                    db.update('main', record['id'], {'updates': 0}, True)
                    Auth.dev.printer(f"Запись {text} {record['id']}")
                    sleep(1)
            db.close()
        except IndexError and Exception:
            Auth.dev.thread_except()


def start(stamp):
    try:
        if os.environ.get('local'):
            threads = [parser, google_update]
            Auth.dev.printer(f'Запуск бота локально за {time_now() - stamp} сек.')
        else:
            Auth.dev.start(stamp)
            threads = [parser, google_update, post_updater, post_ender]
            Auth.dev.printer(f'Бот запущен за {time_now() - stamp} сек.')

        for thread_element in threads:
            _thread.start_new_thread(thread_element, ())
        auto_reboot()
    except IndexError and Exception:
        Auth.dev.thread_except()


if os.environ.get('local'):
    start(stamp1)
