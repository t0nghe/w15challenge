FROM python:3.6.8-alpine
WORKDIR /app
ADD . /app
RUN pip3 install -r requirements.txt
EXPOSE 3100
CMD python3 promo_app.py