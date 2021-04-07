import copy
import csv
import logging
import os
import re
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import requests
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
log_file = 'logs/{:%Y_%m_%d_%H}.log'.format(datetime.now())

base_url = 'https://158sir.x.yupoo.com/albums'

my_email = '158SirDrops@gmail.com'
password = os.environ['EMAIL_PASS']
unsub_url = '/unsubscribe?token='
email_body_template = f'''
Taobao Link: [TAOBAO]

Yupoo Link: [YUPOO]



Unsubscribe: [UNSUB][TOKEN]
'''
email_subject_template = '🚨🚨 158Sir dropped the [ITEM] 🚨🚨'

num_return = 11
old_items = []
email_file = 'emails.csv'
email_headers = ['email', 'token']
delay = 5 * 60
log_upload_delay = 60 * 60
uploading_users = False

on_heroku = True if os.environ.get('on_heroku') == 'True' else False
bucket = '158sir-drops'
key = os.environ.get('AWS_ACCESS_KEY_ID')
secret = os.environ.get('AWS_SECRET_ACCESS_KEY')
s3 = boto3.client('s3')


def upload_logs():
    upload_log_file = log_file if on_heroku else log_file.split('.')[0] + '-local.log'
    try:
        with open(log_file, 'rb') as f:
            s3.upload_fileobj(f, bucket, upload_log_file)
        logger.info(f'Uploaded {upload_log_file} to S3 bucket {bucket}')
    except:
        logger.exception(f'Upload of {upload_log_file} to S3 bucket {bucket} failed')


def upload_users():
    global uploading_users
    uploading_users = True
    upload_file = email_file if on_heroku else email_file.split('.')[0] + '-local.csv'
    try:
        with open(email_file, 'rb') as f:
            s3.upload_fileobj(f, bucket, upload_file)
        logger.info(f'Uploaded {upload_file} to S3 bucket {bucket}')
    except:
        logger.exception(f'Upload of {upload_file} to S3 bucket {bucket} failed')
    backup_file = 'backups/' + email_file.split('.')[0] \
                  + '-' + datetime.now().strftime('%m.%d.%Y-%H:%M:%S') + '.' + email_file.split('.')[1]
    try:
        with open(email_file, 'rb') as f:
            s3.upload_fileobj(f, bucket, backup_file)
        logger.info(f'Uploaded backup {backup_file} to S3 bucket {bucket}')
    except:
        logger.exception(f'Upload of backup {backup_file} to S3 bucket {bucket} failed')
    uploading_users = False


def download_users():
    download_file = email_file if on_heroku else email_file.split('.')[0] + '-local.csv'
    tmp_file = email_file.split('.')[0] + '.tmp'
    try:
        with open(tmp_file, 'wb') as f:
            s3.download_fileobj(bucket, download_file, f)
        logger.info(
            f'Downloaded {download_file} from S3 bucket {bucket} to {tmp_file}')
        if os.path.isfile(email_file):
            os.remove(email_file)
        os.rename(tmp_file, email_file)
        logger.info(f'Replaced temp file {tmp_file} with {email_file}')
    except ClientError:
        os.remove(tmp_file)
        logger.info(f'File {download_file} not found on S3 bucket {bucket}')
        if not os.path.isfile(email_file):
            with open(email_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(email_headers)
                logger.info(f'{email_file} created with header {email_headers}')
    except:
        os.remove(tmp_file)
        logger.exception(
            f'Error downloading file {download_file} from S3 bucket {bucket}')


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
                body = body.replace('[TAOBAO]', item['taobao']).replace('[YUPOO]', item['url']).replace('[UNSUB]',
                                                                                                        unsub_url)
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
    req = requests.get(base_url)
    soup = BeautifulSoup(req.text, 'html.parser')
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
    old_urls = [x['url'] for x in old_items]
    for item in items:
        page = requests.get(item['url'])
        soup = BeautifulSoup(page.text, 'html.parser')
        try:
            taobao = soup.find('a', string=re.compile('https://item.taobao.com/item*')).get('href')
            if item['url'] not in old_urls:
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
    last_log_upload = time.time()
    while True:
        logger.info('Checking 158sirs page for new items')
        new_items = get_new()
        if len(new_items) > 0:
            broadcast(new_items)
        else:
            logger.info('No new items found')
        if time.time() - last_log_upload > log_upload_delay:
            upload_logs()
            last_log_upload = time.time()
        logger.info(f'Cycle done, sleeping for {delay} seconds')
        time.sleep(delay)


if __name__ == '__main__':
    import sys

    log_file = 'logs/{:%Y_%m_%d_%H}.log'.format(datetime.now())
    log_format = u'%(asctime)s | %(levelname)-8s | %(message)s'
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    printer = logging.StreamHandler(sys.stdout)
    printer.setLevel(logging.DEBUG)
    printer.setFormatter(formatter)
    root_logger.addHandler(printer)

    search()
    # broadcast([{'name': 'bigtest', 'url': 'http://yupolink.net', 'taobao': 'https://tao.com'}, {'name': 'bigtest2', 'url': 'http://yupolink.net', 'taobao': 'https://tao.com'}])
