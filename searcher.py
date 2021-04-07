import requests
from bs4 import BeautifulSoup
import csv
import copy
import time
import re
import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

base_url = 'https://158sir.x.yupoo.com/albums'

my_email = '158SirDrops@gmail.com'
password = os.environ['EMAIL_PASS']
unsub_url = 'unsuburl/unsubscribe?token='
email_body_template = f'''
Taobao Link: [TAOBAO]

Yupoo Link: [YUPOO]



Unsubscribe: {unsub_url}[TOKEN]
'''
email_subject_template = '🚨🚨 158Sir dropped the [ITEM] 🚨🚨'

req = requests.get(base_url)
soup = BeautifulSoup(req.text, 'html.parser')
num_return = 5

old_items = []
email_file = 'emails.csv'
email_headers = ['email', 'token']
delay = 5 * 60

if not os.path.isfile(email_file):
    with open(email_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(email_headers)

def get_emails():
    emails = []
    with open(email_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            emails.append(row)
    if len(emails) > 0:
        logger.info(f'Loaded {len(emails)} from {email_file}')
        return emails
    else:
        logger.info(f'No emails found in {email_file}')
        return None


def broadcast(items):
    logger.info(f'Broadcasting for {len(items)} items')
    emails = get_emails()
    if emails:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(my_email, password)
        logger.info('SMTP connection opened')
        logger.info(f'Broadcasting {len(items)} items to {len(emails)} emails')
        for item in items:
            msg = MIMEMultipart()
            subject = copy.deepcopy(email_subject_template)
            msg["Subject"] = subject.replace('[ITEM]', item['name'])
            msg["From"] = my_email
            msg['To'] = ''
            for email in emails:
                body = copy.deepcopy(email_body_template)
                body = body.replace('[TAOBAO]', item['taobao']).replace('[YUPOO]', item['url'])
                body = body.replace('[TOKEN]', email['token'])
                msg.set_payload([MIMEText(body, 'plain')])
                msg.replace_header('To', email['email'])
                text = msg.as_string()
                try:
                    server.sendmail(my_email, email['email'], text)
                    logger.info(f'Send email about item {item} to {email["email"]}')
                except:
                    logger.exception(f'Error sending an email about item {item} to email {email["email"]}')

        logger.info(f'Finished broadcasting for {len(items)} items to {len(emails)} people')
        server.close()
        logger.info('SMTP connection closed')
    else:
        logger.info('No emails found')


def get_items():
    found = []
    for e in soup.find_all('div', attrs={'class': 'showindex__children'}):
        for i in e.find_all('a'):
            found.append({'name': i.get('title'), 'url': base_url + '/' + i.get('href').split('/')[2]})
    logger.info(f'Found {len(found)} items on 158Sirs page, only returning most recent {num_return}')
    return found[:num_return]

def get_new():
    global old_items
    items = get_items()
    new_items = []
    for item in items:
        page = requests.get(item['url'])
        soup = BeautifulSoup(page.text, 'html.parser')
        try:
            taobao = soup.find('a', string=re.compile('https://item.taobao.com/item*')).get('href')
            if item not in old_items:
                item['taobao'] = taobao
                new_items.append(item)
        except AttributeError:
            del item
    logger.info(f'Found {len(new_items)} new items')
    return new_items

def search():
    global old_items
    logger.info('---watcher.watch() starting---')
    old_items = get_new()
    logger.info(f'Loaded {len(old_items)} old items')
    while True:
        logger.info('Checking 158sirs page for new items')
        new_items = get_new()
        if len(new_items) > 0:
            broadcast(new_items)
        else:
            logger.info('No new items found')
        logger.info(f'Cycle done, sleeping for {delay} seconds')
        time.sleep(delay)


if __name__ == '__main__':
    #search()
    broadcast([{'name': 'unsubtest', 'url': 'yupoo/erwgt', 'taobao': 'taobao/1234567'}])