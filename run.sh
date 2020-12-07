#!/usr/bin/env bash
# Start the application
#Author:	Andrey Zaporozhtsev
#Reldate:	06/12/2020

if [ $# -lt 1 ]; then
  echo "Usage: $0 <DIR_FILES_PATH> <OUTPUT_FILENAME>"
  exit 1
fi


if [ -z $2 ] ; then
  OUTPUT_FILENAME='huffman_codes.csv'
else
  OUTPUT_FILENAME="$2"
fi

DIR_FILES_PATH=$(readlink -f $1)
if [ -z "$(ls -A ${DIR_FILES_PATH})" ]; then
   echo "Директория ${DIR_FILES_PATH} пустая. Нету файлов для \"обучения\""
   exit 1
fi

which docker-compose > /dev/null
if [ $? -ne 0 ]; then
    echo "Для работы приложения необходимы установленные docker, docker-compose"
	exit 1
fi

echo "" > .env
cat > .env <<EOL
OUTPUT_FILENAME=${OUTPUT_FILENAME}
DIR_FILES_PATH=${DIR_FILES_PATH}
EOL

$(sleep 5; python -m webbrowser http://localhost:5000 ) &

sudo docker-compose up 
