from flask import Flask, flash, request, redirect, render_template
from flask_socketio import SocketIO, emit
from concurrent.futures import ThreadPoolExecutor
import asyncio
from threading import Thread, Event, Lock
import os,sys,inspect
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir) 
from huffman_generator import generate_huffman_code, wait_for_rabbitmq_start


app = Flask(__name__)

app.secret_key = 'gdQE9Z44gr4pFPoPj6hWJw'
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024
app.config['OUTPUT_FILENAME'] = os.path.join(os.getcwd(), 'output', 
                                    os.environ.get('OUTPUT_FILENAME','huffman_codes.csv'))
app.config['DIR_FILES_PATH'] = os.environ.get('DIR_FILES_PATH', '')

STATS = {'done': 0, 'delayed': 0, 'exception': ''}
CODES_TABLE = None

socketio = SocketIO(app, async_mode='threading', logger=True, engineio_logger=True)

socketio_thread_log = None
thread_calculation = None
socketio_thread_event = Event()
thread_lock = Lock()


def background_calculation(*args):
    global CODES_TABLE
    CODES_TABLE = generate_huffman_code(*args)
    socketio_thread_event.set()
    global socketio_thread_log
    socketio_thread_log = None


def background_task():
    global STATS
    while not socketio_thread_event.is_set():
        if STATS['delayed'] > 0:
            socketio.emit('update_stats', STATS, namespace='/stats')
        socketio.sleep(0.3)


def huffman_calculation(dir_or_files):
    try:
        global thread_calculation
        if thread_calculation is None:
            global STATS
            global CODES_TABLE
            thread_calculation = Thread(target=background_calculation, 
                                        args=(app.config.get('OUTPUT_FILENAME'), 
                                        dir_or_files,
                                        STATS))

            thread_calculation.setDaemon(True)
            thread_calculation.start()
            thread_calculation.join()
            if not CODES_TABLE[0]:
                flash('Ошибка: коды не были рассчитаны')
                return redirect('/')

            file_path = CODES_TABLE[1] if CODES_TABLE[1] else ''
            return render_template('codes.html', code_table=CODES_TABLE[0],
                                                 save_path=file_path)

    except Exception as e:
        print("Errors: {}".format(e))
        flash(e)
    
    return redirect('/')
    

def allowed_filesize(filesize):
    return int(filesize) <= app.config["MAX_CONTENT_LENGTH"]


@app.errorhandler(413)
def too_large(e):
    return "File is too large", 413


@app.route('/')
def index():
    return render_template('index.html', dir_path_to_files=app.config.get('DIR_FILES_PATH'))


@app.route('/by_files', methods=['POST'])
def start_files_handling():
    if request.method == 'POST':

        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        files = request.files.getlist('files[]')

        if "filesize" in request.cookies:

            if not allowed_filesize(request.cookies["filesize"]):
                print("Размер файлов превышен")
                return redirect(request.url)
            
            for file in files:
                if file and file.filename == '':
                    flash('Файлы не выбраны')
                    return redirect(request.url)

            flash('Начинаем расчет кодов...')
        return huffman_calculation(files)

@app.route('/by_dir', methods=['POST'])
def start_dir_handling():
    if request.method == 'POST':
        return huffman_calculation('/files')
    return redirect('/')


@socketio.on('connect', namespace='/stats')
def test_connect():
    global socketio_thread_log
    print('SocketIO: Client connected')

    with thread_lock:
        if socketio_thread_log is None:
            print("SocketIO: Starting Thread")
            socketio_thread_log = socketio.start_background_task(background_task)


@socketio.on('disconnect', namespace='/stats')
def test_disconnect():
    print('SocketIO: Client disconnected')


@socketio.on_error('/stats')
def error_handler_stats(e):
    print("Error socketio: {}".format(e))


if __name__ == "__main__":
    wait_for_rabbitmq_start()
    socketio.run(app,
                host='0.0.0.0',
                port=5000,
                debug=False)