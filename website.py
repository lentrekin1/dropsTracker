from flask import Flask, render_template, request, flash, redirect
import re
import csv
import os
import sys
from datetime import datetime
from validate_email import validate_email
import logging
import threading
import searcher

if not os.path.isdir('logs'):
    os.mkdir('logs')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ERTHGFwt5y64r3wefDGTHYT@#WEFBT54rwesdfghYTRDEFGBHJk,KJHgfNJ<KuTRGDFSwert'
email_file = 'emails.csv'
header = 'email'

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

search_thread = threading.Thread(target=searcher.search, args=())
search_thread.start()

if not os.path.isfile(email_file):
    with open(email_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)

def add_email(email):
    with open(email_file, 'r', encoding='utf=8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0] == email:
                logger.info(f'Email {email} already found in {email_file}, silently rejecting')
                return
    with open(email_file, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([email])
        logger.info(f'Wrote email {email} to {email_file}')


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'email' in request.form:
            logger.info(f'User from IP {request.remote_addr} submitted email {request.form["email"]} using a POST request')
            if validate_email(email_address=request.form['email'], check_dns=False, check_smtp=False):
                logger.info(f'Email {request.form["email"]} passed validate_email(), adding to {email_file}')
                add_email(request.form.get('email'))
                flash('Email added successfully')
            else:
                logger.info(f'Email {request.form["email"]} failed validate_email(), rejecting')
                flash('Please enter a valid email')
        else:
            logger.info(f'User from IP {request.remote_addr} submitted a form that did not have an email in it: {request.form.to_dict(flat=False)}')
        return redirect('/')
    logger.info(f'User from IP {request.remote_addr} connected to the site using a GET request')
    return render_template('home.html')


if __name__ == '__main__':
    app.run(port=80)
