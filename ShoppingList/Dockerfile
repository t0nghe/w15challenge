FROM python:3.6.8-alpine
WORKDIR /app
ADD . /app
RUN pip3 install -r requirements.txt
EXPOSE 4300
CMD python3 shopping_app.py