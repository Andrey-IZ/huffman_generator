huffman_generator

Andrey Zaporozhtsev 07/12/2020

===========

Test of asynchronous calculation of Huffman code table. 

This repository is a sample application that updates a webpage using a background thread for all users connected.
It is based on the very useful Flask-SocketIO code.

To use - please clone the repository and then set up your virtual environment using the requirements.txt file with pip and virtualenv. You can achieve this with:


    git clone git@github.com:Andrey-IZ/huffman_generator.git
    cd huffman_generator
    python3 -m venv huffman
    source huffman/bin/activate
    pip install -r requirements.txt

Start the application using web-application:
launch the browser and go to: http://localhost:5000/ 
in terminal:
<code>
./run.sh
</code>

Start the application with (CLI):
<code>
sudo docker-compose up -d rabbitmq
python huffman_generator.py <path_to_files> <output_filename>
</code>

It will generate the table
And visit http://localhost:5000 to see the table.

Задание:

Нужно реализовать настройку параметров ("обучение") кода Хаффмана на некоей
базе текстов, оформленных в виде большого количества отдельных файлов. Скажем,
всех файлов, лежащих в одном каталоге, полный путь к которому принимается в
качестве входных данных. Файлы воспринимаются как тексты над алфавитом
ASCII-символов. Процесс сбора статистики рекомендуется (не обязательно, но
рекомендцется) реализовать в многопоточном формате: запускать в отдельных тредах
некие "обработчики", каждый из которых будет в каждый момент времени работать с
одним файлом, и по завершении своей работы каким-то образом передавать свои
результаты в некую единую сущность, общую для всех обработчиков. По завершении
обработки всех файлов надо выработать, собственно, код - можно в итоге представить
его в виде какой-то таблицы, которую можно вывести в читаемом виде в файл или на
экран.
Что такое код Хаффмана - придется разобраться по любым доступным источникам.
Возможно проще это будет сделать, грубо говоря, не по википедии, а по хабрахабру.
Вероятно с этого стоит начать, и потом перечитать описание задачи снова.
Желательно покрыть тестами существенную долю важных частей проекта. Во всем
прочем - никаких явных пожеланий нет. То есть понятно, что если, скажем, очередь
обработки файлов будет реализована не полностью самостоятельно, а с помощью
какого-нибудь "настоящего" брокера очередей, это будет плюсом, но не то чтобы это
ожидалось.
