import requests
from bs4 import BeautifulSoup
import csv
import copy
import time
import yagmail
import re
import logging
import sys
import os
from datetime import datetime

logger = logging.getLogger(__name__)

base_url = 'https://158sir.x.yupoo.com/albums'

my_email = '158SirDrops@gmail.com'
yag = yagmail.SMTP(my_email)
email_body_template = ['Taobao Link: [TAOBAO]', 'Yupoo Link: [YUPOO]']
email_subject_template = '🚨🚨 158Sir dropped the [ITEM] 🚨🚨'

req = requests.get(base_url)
soup = BeautifulSoup(req.text, 'html.parser')
num_return = 5

item_file = 'old.csv'
email_file = 'emails.csv'
email_header = 'email'
item_headers = ['name', 'url']
delay = 5 * 1

if not os.path.isfile(item_file):
    with open(item_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(item_headers)

# yagmail.register('mygmailusername', 'mygmailpassword')
def send_email(recipient, item, taobao, yupoo):
    subject = email_subject_template.replace('[ITEM]', item)
    body = copy.deepcopy(email_body_template)
    body[0] = body[0].replace('[TAOBAO]', taobao)
    body[1] = body[1].replace('[YUPOO]', yupoo)
    yag.send(recipient, subject, body)
    logger.info(f'Send email about item {item} to {recipient}')


def get_emails():
    emails = []
    with open(email_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0] != email_header:
                emails.append(row[0])
    if len(emails) > 0:
        logger.info(f'Loaded {len(emails)} from {email_file}')
        return emails
    else:
        logger.info(f'No emails found in {email_file}')
        return None


def broadcast(items):
    logger.info(f'Broadcasting for items {items}')
    emails = get_emails()
    if emails:
        for item in items:
            for email in emails:
                send_email(email, item['name'], item['taobao'], item['url'])
        logger.info(f'Finished broadcasting for items {items}')


def get_items():
    found = []
    for e in soup.find_all('div', attrs={'class': 'showindex__children'}):
        for i in e.find_all('a'):
            found.append({'name': i.get('title'), 'url': '/' + i.get('href').split('/')[2]})
    logger.info(f'Found {len(found)} items on 158Sirs page, only returning most recent {num_return}')
    return found[:num_return]

def save_items(items):
    to_save = []
    for item in items:
        to_save.append({'name': item['name'], 'url': item['url']})
    with open(item_file, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=item_headers)
        writer.writerows(to_save)
    logger.info(f'Wrote {len(to_save)} items to {item_file}: {to_save}')

def get_new():
    items = get_items()
    old_items = []
    new_items = []
    with open(item_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            old_items.append(row)
    for item in items:
        page = requests.get(base_url + item['url'])
        soup = BeautifulSoup(page.text, 'html.parser')
        try:
            taobao = soup.find('a', string=re.compile('https://item.taobao.com/item*')).get('href')
            if item not in old_items:
                item['taobao'] = taobao
                new_items.append(item)
        except AttributeError:
            del item
    logger.info(f'Found {len(new_items)} new items: {new_items}')
    save_items(new_items)
    return new_items


def fill_items(items):
    for item in items:
        item['url'] = base_url + item['url']
    logger.info(f'Filled out {len(items)} items: {items}')
    return items


def search():
    logger.info('---watcher.watch() starting---')
    while True:
        logger.info('Checking 158sirs page for new items')
        new_items = get_new()
        if len(new_items) > 0:
            new_items = fill_items(new_items)
            broadcast(new_items)
        else:
            logger.info('No new items found')
        logger.info(f'Cycle done, sleeping for {delay} seconds')
        time.sleep(delay)


if __name__ == '__main__':
    search()

