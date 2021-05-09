FROM python:3.6.8-alpine
WORKDIR /app
ADD . /app
RUN pip3 install -r requirements.txt
CMD python3 msg_consumer.py