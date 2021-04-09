import sys
import logging
from datetime import datetime
import os

if not os.path.isdir('logs'):
    os.mkdir('logs')

log_file = os.getcwd() + '/' + 'logs/{:%Y_%m_%d_%H}.log'.format(datetime.now())
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