#!/usr/bin/env python
# coding=utf-8


import rabbitpy
import threading
import functools
import logging
import os
import sys
import mimetypes
import json
import csv
import string
from multiprocessing import cpu_count
from collections import Counter
from huffman import huffman_encode
from concurrent.futures import ThreadPoolExecutor, wait, as_completed


__author__ = 'andrey.zaporozhtsev@ya.ru'
__date__ = "1.12.2020"
__license__ = "GPL"
__version__ = "0.1.0"

EXCHANGE = 'ex_char_prefix'
PATH = '.'
QUEUE = 'q_char_prefix_freq_map'
ROUTING_KEY = 'rk_freq_map'
HUFFMAN_CODE_FILE = 'huffman_codes.csv'
ACK_END = str('кон123').encode('utf-8')


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(funcName) -35s : %(message)s')
LOGGER = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def main():
    args = init_args()
    mode = logging.INFO

    if args.get('verbose'):
        mode = logging.DEBUG
    LOGGER.level = mode

    counter = Counter()
    # collect the statistics for the Huffman code
    with rabbitpy.Connection() as connection:
        with connection.channel() as channel:
            rabbitpy.delete_queue(queue_name=QUEUE)

            exchange = rabbitpy.Exchange(channel, EXCHANGE)
            exchange.declare()

            queue = rabbitpy.Queue(channel, QUEUE)
            queue.declare()

            queue.bind(EXCHANGE, ROUTING_KEY)

        consumer_thread = threading.Thread(target=consumer, args=(connection,counter))
        consumer_thread.start()

        publisher_thread = threading.Thread(target=publisher, args=(connection, args.get('DIR_PATH')))
        publisher_thread.start()

        publisher_thread.join()
        consumer_thread.join()

    generate_code(counter, args.get('output'))


def generate_code(code_map, filename):
    code = huffman_encode(code_map)

    with open(filename, 'w', newline='') as fd:
        writer = csv.writer(fd,  delimiter='|')
        for ch in sorted(code):
            writer.writerow((ch, ord(ch), code[ch]))
        print("The Huffman codes file has been created to {}".format(filename))


def collect_filenames(path):
    for root, _,filenames in os.walk(path):
        for filename in filenames:
            yield os.path.join(root, filename)


def gather_map_worker(channel, url):
    thread_id = threading.get_ident()

    LOGGER.debug("Working...{}".format(thread_id))
    counter = Counter()
    payload = None

    if os.path.exists(url) and isinstance(mimetypes.guess_type(url)[0], str) \
            and mimetypes.guess_type(url)[0].find('text') != -1:
        with open(url, 'rt') as fd:
            for line in fd.readlines():
                counter.update(line)
        
        for key in set(counter.keys()).difference(string.ascii_letters):
            del counter[key]

        payload = json.dumps(dict(counter))
        LOGGER.debug(" [x] Done.Publishing {}".format(url))
        message = rabbitpy.Message(channel, payload)
        message.publish(EXCHANGE, ROUTING_KEY)


def on_fail(exc, obj):
    LOGGER.error("Fail: {}, {}".format(exc, obj))


def task_done(future, args):
    stats,io_lock = args
    with io_lock:
        stats['delayed'] -= 1
        stats['done'] += 1
    if future.exception():
        on_fail(future.exception(), future.obj)
    LOGGER.debug("task done {}".format(stats))


def consumer(connection, counter):
    received = 0
    with connection.channel() as channel:
        for message in rabbitpy.Queue(channel, QUEUE).consume():
            payload = message.body
            if payload == ACK_END:
                message.ack()
                break
            received += 1
            counter.update(json.loads(payload))
            message.ack()
        

def publisher(connection, path):
    io_rlock = threading.RLock()
    with ThreadPoolExecutor(max_workers=cpu_count()) as thread_executor: 
        stats = {'done': 0, 'delayed': 0}

        futures = []
        with connection.channel() as channel:
            for filename in collect_filenames(path):
                filename = os.path.abspath(filename) 

                stats['delayed'] += 1

                obj = (channel, filename)
                future = thread_executor.submit(gather_map_worker, *obj)
                future.obj = obj
                cb = functools.partial(task_done, args=(stats, io_rlock))
                future.add_done_callback(cb)
                futures.append(future)
            
            wait(futures)

            message = rabbitpy.Message(channel, ACK_END)
            message.publish(EXCHANGE, ROUTING_KEY)


def init_args():
    """
    Gets dictionary arguments of command line
    :return: dict args
    """
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    description = 'huffman code generator (the most easy way)'
    epilog = '''(c) Andrew 2020. Copyright and Related Rights Regulations (2020 No. 3)'''
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter, description=description, epilog=epilog)

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='show the process in details')
    parser.add_argument('DIR_PATH', default=PATH, help='set the URL to the directory')
    parser.add_argument('-o', '--output', default=HUFFMAN_CODE_FILE, help='set the output file as CSV')

    args = sys.argv[1:]

    args = parser.parse_args(args)
    args = vars(args)

    return args


if __name__ == "__main__":
    main()
