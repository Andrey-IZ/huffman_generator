#!/usr/bin/env python
# coding=utf-8


import rabbitpy
import socket
import threading
import functools
import logging
import time
import os
import sys
import mimetypes
import json
import csv
import string
from pathlib import Path
from multiprocessing import cpu_count
from collections import Counter
from huffman import huffman_encode
from concurrent.futures import ThreadPoolExecutor, wait, as_completed, ALL_COMPLETED, FIRST_EXCEPTION


__author__ = 'andrey'
__date__ = "3.12.2020"
__license__ = "GPL"
__version__ = "0.1.0"

EXCHANGE = 'ex_char_prefix'
PATH = '.'
QUEUE = 'q_char_prefix_freq_map'
ROUTING_KEY = 'rk_freq_map'
HUFFMAN_CODE_FILE = 'huffman_codes.csv'
ACK_END = str('кон123').encode('utf-8')
HOST = '0.0.0.0'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(funcName) -35s : %(message)s')
LOGGER = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def main():
    args = init_args()
    mode = logging.INFO

    if args.get('verbose'):
        mode = logging.DEBUG
    LOGGER.level = mode

    wait_for_rabbitmq_start()

    generate_huffman_code(args.get('output'), args.get('DIR_FILES_PATH', '.'))


def wait_for_rabbitmq_start(): 
    is_reachable = False
    while not is_reachable:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        LOGGER.warning(f"wait for rabbitmq is running on {HOST}...")
        try:
            s.connect((HOST, 5672))
            is_reachable = True
        except socket.error:
            time.sleep(2)
        s.close()
    return is_reachable


def generate_huffman_code(output_path, dir_path_or_file_list, stats=None):
    counter = Counter()
    if stats is None:
        stats = {'done': 0, 'delayed': 0, 'exception': ''}
    # collect the statistics for the Huffman code
    try:
        with rabbitpy.Connection(f"amqp://guest:guest@{HOST}:5672/%2F") as connection:   # url='amqp://guest:guest@rabbitmq:5672/%2F'
            with connection.channel() as channel:
                rabbitpy.delete_queue(queue_name=QUEUE)

                exchange = rabbitpy.Exchange(channel, EXCHANGE)
                exchange.declare()

                queue = rabbitpy.Queue(channel, QUEUE)
                queue.declare()

                queue.bind(EXCHANGE, ROUTING_KEY)

            consumer_thread = threading.Thread(target=consumer, args=(connection,counter))
            consumer_thread.start()

            publisher_thread = threading.Thread(target=publisher, args=(connection, dir_path_or_file_list, stats))
            publisher_thread.start()

            publisher_thread.join()
            consumer_thread.join()
    except (rabbitpy.exceptions.ConnectionResetException,
            rabbitpy.exceptions.AMQPConnectionForced) as error:
        LOGGER.error('Connection error: %s', error)
    
    if stats['delayed'] == 0 and len(stats['exception']) == 0:
        code_table = _generate_code_table(counter)
        filename = save_code_to_file(output_path, code_table)
        return code_table, filename
    


def _generate_code_table(code_map):
    code = huffman_encode(code_map)
    if code:
        result_table = list()
        for ch in sorted(code):
            result_table.append((ch, ord(ch), code[ch]))
        LOGGER.warning("The Huffman codes file has been generated")
        return result_table


def save_code_to_file(filename, code_table):
    if code_table:
        Path(os.path.dirname(filename)).mkdir(parents=True, exist_ok=True)
        with open(filename, 'w', newline='') as fd:
            writer = csv.writer(fd,  delimiter='|')
            for row in code_table:
                writer.writerow(row)
            LOGGER.warning("The huffman codes has been saved to {}".format(os.path.abspath(filename)))
            return filename


def _get_stream(dir_or_files):
    if isinstance(dir_or_files, str):
        return _collect_filenames(dir_or_files)
    return _get_files_stream(dir_or_files)


def _collect_filenames(dir_path):
    for root, _,filenames in os.walk(dir_path):
        for filename in filenames:
            url = os.path.join(root, filename) 
            if os.path.exists(url):
                fd = open(url, 'rb')
                yield (fd, fd.name)


def _get_files_stream(files):
    for file in files:
        fd = file.stream
        yield (fd, file.filename)


def gather_map_worker(channel, *args):
    fd, url = args
    thread_id = threading.get_ident()
    LOGGER.debug("Working...{}".format(thread_id))
    counter = Counter()
    payload = None

    try:
        while True:
            chunk = fd.read(1024)
            if not chunk:
                break
            counter.update(chunk.decode('utf-8'))
    except Exception as e:
        raise ValueError("{} can't read: {}".format(url, e))

    
    for key in set(counter.keys()).difference(string.ascii_letters):
        del counter[key]

    payload = json.dumps(dict(counter))
    LOGGER.debug(" [x] Done.Publishing {}".format(url))
    message = rabbitpy.Message(channel, payload)
    message.publish(EXCHANGE, ROUTING_KEY)


def on_fail(exc, obj):
    LOGGER.error("Failed: {}: {}".format(exc, obj))


def task_done(future, args):
    stats,io_lock = args
    with io_lock:
        stats['delayed'] -= 1
        stats['done'] += 1
        if future.exception():
            on_fail(future.exception(), future.obj)
            stats['exception'] = future.exception().args[0]
    # if future.cancelled():
    #     LOGGER.warning('task canceled: {}'.format(future.obj))
        
    LOGGER.info("task done {}".format(stats))


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
        

def publisher(connection, path, stats):
    io_rlock = threading.RLock()
    with ThreadPoolExecutor(max_workers=cpu_count()) as thread_executor: 

        futures = []
        with connection.channel() as channel:
            for fd, url in _get_stream(path):
                
                with io_rlock:
                    stats['delayed'] += 1
                obj = (channel, fd, url)
                future = thread_executor.submit(gather_map_worker, *obj)
                future.obj = obj
                cb = functools.partial(task_done, args=(stats, io_rlock))
                future.add_done_callback(cb)
                futures.append(future)
            
            wait(futures, timeout=None, return_when=FIRST_EXCEPTION)[0]

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
    parser.add_argument('DIR_FILES_PATH', default=PATH, help='set the URL to the directory')
    parser.add_argument('-o', '--output', default=HUFFMAN_CODE_FILE, help='set the output file as CSV')

    args = sys.argv[1:]

    args = parser.parse_args(args)
    args = vars(args)

    return args


if __name__ == "__main__":
    main()
