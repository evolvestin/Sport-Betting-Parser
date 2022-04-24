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
# =================================================================================================================
stamp1 = time_now()


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
    now, title = datetime.now(tz), '⏱⏱⏱'
    score = re.sub(r'\(.*?\)', '', record['score']).strip()
    play_time = datetime.fromtimestamp(record['start_time'], tz)
    coefficient_text = f"КФ: {record['coefficient']}\n" if record['coefficient'] else ''
    if score != '- : -' and (play_time + timedelta(hours=2.5)) < now:
        split = [int(re.sub(r'\D', '', element)) or 0 for element in score.split(':')]
        if len(split) == 2:
            if record['bet'] == 'П1':
                title = '✅✅✅' if split[0] > split[1] else '❌❌❌'
            elif record['bet'] == 'П2':
                title = '✅✅✅' if split[1] > split[0] else '❌❌❌'
            elif record['bet'] == '1X':
                title = '✅✅✅' if split[1] >= split[0] else '❌❌❌'
            elif record['bet'] == 'X2':
                title = '✅✅✅' if split[1] >= split[0] else '❌❌❌'
            else:
                title = '✅✅✅' if split[0] != split[1] else '❌❌❌'

    text = f"{title}\n" \
           f"⚽ {record['name']}\n" \
           f"⏱ {play_time.strftime('%H:%M')}\n" \
           f"🧾 Счёт матча: {bold(score)}\n" \
           f"{coefficient_text}" \
           f"💰 Ставка: {bold(bets.get(record['bet'], 'Нет'))}"
    return text


def post_updater():
    while True:
        try:
            db = SQL(db_path)
            records = db.get_posts()
            print(f"Начало обновления постов: {[i['id'] for i in records]}") if len(records) > 0 else None
            for record in records:
                update = True
                try:
                    bot.edit_message_text(chat_id=os.environ['channel_id'],
                                          text=iter_post(record), message_id=record['post_id'],
                                          disable_web_page_preview=True, parse_mode='HTML')
                except IndexError and Exception as error:
                    if 'exactly the same' not in str(error):
                        update = False
                        Auth.dev.executive(None)
                if update:
                    db.update('main', record['id'], {'post_update': time_now()})
                sleep(60)
            print('Конец обновления постов') if len(records) > 0 else None
            sleep(30)
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
        except IndexError and Exception:
            Auth.dev.thread_except()


def parser():
    while True:
        try:
            db = SQL('db/database.db')
            driver = chrome(os.environ.get('local'))
            driver.set_window_size(1200, 1200)
            driver.get(os.environ.get('link'))
            body = driver.find_element(By.TAG_NAME, 'tbody')
            for tr in body.find_elements(By.TAG_NAME, 'tr'):
                game_id, coefficient = tr.get_attribute('data-eventid'), None
                bet = tr.find_element(By.CLASS_NAME, f"{os.environ.get('tag1')}__bet").text
                title = tr.find_element(By.CLASS_NAME, f"{os.environ.get('tag1')}__teams").text
                start_time = tr.find_element(By.CLASS_NAME, f"{os.environ.get('tag1')}__time").text

                if bet in ['П1', 'П2']:
                    odds = tr.find_elements(By.CLASS_NAME, f"{os.environ.get('tag1')}__odd")
                    if len(odds) == 3:
                        if bet == 'П1':
                            coefficient = odds[0].text
                        else:
                            coefficient = odds[2].text
                        if coefficient == '0.00':
                            coefficient = None

                tds = tr.find_elements(By.TAG_NAME, 'td')
                for td in tds:
                    score = td.get_attribute('data-res')
                    if score:
                        record = db.get_row(game_id)
                        if record:
                            if record['score'] != score or record['coefficient'] != coefficient:
                                db.update('main', game_id, {'score': score, 'coefficient': coefficient})
                        else:
                            now = datetime.now(tz)
                            play_time = datetime.fromisoformat(f"{now.strftime('%Y-%m-%d')} {start_time}:00+03:00")
                            record = {
                                'bet': bet,
                                'id': game_id,
                                'name': title,
                                'score': score,
                                'post_id': None,
                                'coefficient': coefficient,
                                'start_time': play_time.timestamp(),
                                'post_update': zero_row['post_update']}
                            db.create_row(record)

                            if score == '- : -':
                                text = iter_post(record)
                                try:
                                    post = bot.send_message(os.environ['channel_id'], text,
                                                            disable_web_page_preview=True, parse_mode='HTML')
                                    db.update('main', game_id, {'post_id': post.id, 'post_update': time_now()})
                                    sleep(60)
                                except IndexError and Exception:
                                    Auth.dev.executive(None)
            driver.close()
            db.close()
            sleep(300)
        except IndexError and Exception:
            Auth.dev.thread_except()


def start(stamp):
    try:
        if os.environ.get('local'):
            threads = [parser]
            Auth.dev.printer(f'Запуск бота локально за {time_now() - stamp} сек.')
        else:
            Auth.dev.start(stamp)
            threads = [parser, google_update, post_updater]
            Auth.dev.printer(f'Бот запущен за {time_now() - stamp} сек.')

        for thread_element in threads:
            _thread.start_new_thread(thread_element, ())
        auto_reboot()
    except IndexError and Exception:
        Auth.dev.thread_except()


if os.environ.get('local'):
    start(stamp1)
