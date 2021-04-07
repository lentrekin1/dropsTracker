from flask import Flask, render_template, request, flash, redirect
import re
import csv
import os
import sys
from email.utils import parseaddr
from datetime import datetime
import logging
import threading
import searcher
import random
import string

if not os.path.isdir('logs'):
    os.mkdir('logs')

log_file = 'logs\{:%Y_%m_%d_%H}.log'.format(datetime.now())
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

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ERTHGFwt5y64r3wefDGTHYT@#WEFBT54rwesdfghYTRDEFGBHJk,KJHgfNJ<KuTRGDFSwert'
email_file = 'emails.csv'
email_regex = '^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,3}$'
token_size = 30

search_thread = threading.Thread(target=searcher.search, args=())
search_thread.start()

if not os.path.isfile(email_file):
    with open(email_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(searcher.email_headers)

def add_email(email):
    with open(email_file, 'r', encoding='utf=8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['email'] == email:
                logger.info(f'Email {email} already found in {email_file}, silently rejecting')
                return
    token = ''.join(random.choices(string.ascii_letters, k=token_size))
    with open(email_file, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=searcher.email_headers)
        writer.writerow({'email': email, 'token': token})
        logger.info(f'Wrote email {email} with token {token} to {email_file}')

def save_emails(emails):
    with open(email_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=searcher.email_headers)
        writer.writeheader()
        writer.writerows(emails)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'email' in request.form:
            logger.info(f'User from IP {request.remote_addr} submitted email {request.form["email"]} using a POST request')
            if re.match(email_regex, request.form["email"]):
                logger.info(f'Email {request.form["email"]} passed validate_email(), adding to {email_file}')
                add_email(request.form["email"])
                flash('Email added successfully')
            else:
                logger.info(f'Email {request.form["email"]} failed validate_email(), rejecting')
                flash('Please enter a valid email')
        else:
            logger.info(f'User from IP {request.remote_addr} submitted a form that did not have an email in it: {request.form.to_dict(flat=False)}')
        return redirect('/')
    logger.info(f'User from IP {request.remote_addr} connected to the site using a GET request')
    return render_template('home.html')

@app.route('/unsubscribe')
def unsub():
    old_emails = searcher.get_emails()
    if old_emails:
        if request.args.get('token'):
            for email in old_emails:
                if request.args.get('token') == email['token']:
                    logger.info(f'Email address/token {email} unsubscribed from IP {request.remote_addr}')
                    old_emails = [d for d in old_emails if d.get('token') != request.args.get('token')]
                    save_emails(old_emails)
                    return 'You have been successfully unsubscribed'
            logger.info(f'IP {request.remote_addr} attempted to use an invalid token {request.args.get("token")} to unsubscribe')
        else:
            logger.info(f'IP {request.remote_addr} tried to unsubscribe without a token')
    else:
        logger.info(f'IP {request.remote_addr} attempted to unsubscribe with token {request.args.get("token")} but no emails were found')
    return redirect('/')

if __name__ == '__main__':
    app.run(port=80)
