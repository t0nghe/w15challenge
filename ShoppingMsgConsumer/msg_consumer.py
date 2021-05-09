from flask import Flask, render_template, make_response, request
from flask_pymongo import PyMongo
import pika, json

# NOTE:
# In earlier attemps to run the code, RABBIT_HOST was mistakenly set to either localhost or equivalent values.
# But since it's inside Docker, localhost refers to this very docker container. And NOT the RabbitMQ container on the docker network.
# Changed to the name of the Docker container after a lot of Googling.
RABBIT_HOST = "rabbitmq"
RABBIT_QUEUE = "items_changes"

app = Flask(__name__)
app.config["MONGO_URI"] = "<HIDDEN>"
mongo = PyMongo(app)

# NOTE:
# ifexist, buy_one_more, add_to_list, purchase_decision and remove_item take care of mundane purchasing logic.
# When something gets cheaper, buy one more. When something is removed from the shelf, remove it from shopping list.
def ifexist(name):
    count = mongo.db.itemsToBuy.find({"name": name}).count()
    if count == 1:
        return True
    else:
        return False

# NOTE:
# Operations that change data in any way, will set a new value to the additional _TIMESTAMP_ item,
# which will be used by `shopping_app` for the /api/updated.
# That why some of the following functions take an additional timestamp argument. 
def buy_one_more(name, timestamp):
    mongo.db.itemsToBuy.update({"name": "_TIMESTAMP_"},
    {
        "$set": {
            "lastUpdated": timestamp
        }
    })
    mongo.db.itemsToBuy.update({"name": name},
    {
        "$inc": {"count": 1}
    })

def add_to_list(name, timestamp):
    mongo.db.itemsToBuy.update({"name": "_TIMESTAMP_"},
    {
        "$set": {
            "lastUpdated": timestamp
        }
    })
    mongo.db.itemsToBuy.insert({
        "name": name,
        "count": 1
    })

def purchase_decision(data):
    name, price, timestamp = data["name"], float(data["price"]), data["timestamp"]
    oldPrice = float(data.get("oldPrice") or 0) 
    if ifexist(name):
        if price < oldPrice:
            buy_one_more(name, timestamp)
    else:
        add_to_list(name, timestamp)

def remove_item(data):
    name, timestamp = data["name"], data["timestamp"]
    mongo.db.itemsToBuy.update({"name": "_TIMESTAMP_"},
    {
        "$set": {
            "lastUpdated": timestamp
        }
    })
    mongo.db.itemsToBuy.remove({ "name": name })

# NOTE:
# This part is pretty much the same as the standard consumer function shown in the docs of pika.
# Since `promo_app` sends data to the queue `items_changes` as a JSON object,
# in which there is a key called `keyword` that indicates the type of the message.
#
# At some point I spent hours, if not days, to figure out why this consumer can't receive anything.
# before finally noticing the channel should be closed at the end. 
def listen():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    channel = connection.channel()

    channel.queue_declare(queue=RABBIT_QUEUE)

    def callback(ch, method, properties, body):
        data = json.loads(body.decode())
        if data["keyword"] in ["item_updated", "item_created"]:
            purchase_decision(data)
        elif data["keyword"] == "item_deleted":
            remove_item(data)

    channel.basic_consume(queue=RABBIT_QUEUE, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()
    channel.close()

if __name__ == '__main__':
    listen()