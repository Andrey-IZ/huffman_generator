FROM python:3.9-slim
ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt
# ENV HUFFMAN_DIR_PATH="."

ENTRYPOINT ["python", "huffman_generator.py"]
CMD ["-o", "huffman_code.csv", "codes"]
