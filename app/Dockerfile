FROM python:3.9-slim
ADD . /app
WORKDIR /app

# RUN python -m pip install --upgrade pip
RUN apt-get update
RUN apt-get install -y curl 
RUN pip install -r requirements.txt
EXPOSE 5000

ENTRYPOINT ["python"]
CMD ["./gui/app.py"]
