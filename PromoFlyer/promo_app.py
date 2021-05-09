from flask import Flask, render_template, make_response, request
from flask_pymongo import PyMongo
from datetime import datetime
import pika, json

app = Flask(__name__)
app.config["MONGO_URI"] = "<HIDDEN>"
mongo = PyMongo(app)

RABBIT_HOST = "rabbitmq"
RABBIT_QUEUE = "items_changes"
PORT = 3100

# NOTE:
# The following three functions prefixed `mongop_` interact with MongoDB.
# Noticeably, they are quite basic in that they do not handle return value
# from MongoDB. If and when MongoDB fails to connect or operate in the cloud, or the 
# requested operation fails, these functions wouldn't be able to know.
#
# Also worth noting is the fact that `if count == 1:` is used to test for existence of
# an item. The logic behind this isn't sound. If for some reason querying an item by 
# `name` field returns a count of 2, mongop_delete and mongop_update will be problematic.
#
# Besides, In this whole project, I used the `name` field of DB documents to identify them.
# In hindsight, `_id` seems a better way to refer to records. 
# 
# In the future when I program similar tasks, I'd try to cover all possible scenarios.
def mongop_create(name, price):
    count = mongo.db.promoItems.find({"name": name}).count()
    if count < 1:
        mongo.db.promoItems.insert({"name": name, "price": float(price)})
        return True
    else:
        return False

def mongop_update(name, price):
    rows = mongo.db.promoItems.find({"name": name})
    count = rows.count()
    if count == 1:
        old_price = rows[0]["price"]
        mongo.db.promoItems.update(
            {"name": name}, { "$set": {"price": float(price)} }
            )
        # By returning a tuple, we guarantee a True equivalent
        return (old_price, price) 
    else:
        return False

def mongop_delete(name):
    count = mongo.db.promoItems.find({"name": name}).count()
    if count == 1:
        mongo.db.promoItems.remove({"name": name})
        return True
    else:
        False

# NOTE:
# In order to attach a keyword to the data being dispatched to Rabbit,
# I added a keyword field to the dictionary/object. 
# There must be a better way to add a keyword to a message in Rabbit
# that I did not know.
def rabbit_produce(keyword, data):
    # The keyword is used in ShoppingList app.
    data['keyword'] = keyword
    data['timestamp'] = datetime.now().isoformat()
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBIT_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=RABBIT_QUEUE)
    channel.basic_publish(exchange='', routing_key=RABBIT_QUEUE, body=json.dumps(data))
    connection.close()

@app.route("/", methods=["GET"])
def serve_html():
    return render_template("index.html")

@app.route('/api/<operation>', methods=["POST", "GET", "PUT", "DELETE"])
def api(operation):
    method = request.method
    name = request.args.get('name')
    price = request.args.get('price')

    # Check if <operation> <method> combination is accepted.
    if (operation, method) not in [("create", "POST"), ("update", "PUT"), ("delete", "DELETE"), ("query", "GET")]:
        operation_error = app.response_class(
            response=json.dumps({"error": "problematic URI 'api/{}' or method '{}'".format(operation, method), "message": 'Use POST at /api/create, PUT at /api/update, DELETE at /api/delete and GET at /api/query.'}),
            status=404,
            mimetype='application/json'
        )
        return operation_error

    # Operation: create: create a record
    # Method: POST
    # Reponse: 200: If creation successful
    # 409: Conflict, if record already exists
    # 500: Other server-side error

    if operation == "create":
        if name and price:
            res = mongop_create(name, price)
            if res:
                successful = app.response_class(
                # An earlier version didn't work because misspelt
                response=json.dumps(
                    {"success": "item '{}' successfully created".format(name)}
                ), status=200, mimetype="application/json"
            )
                rabbit_produce("item_created", {"name": name, "price": price})
                return successful
            else:
                conflict = app.response_class(
                # An earlier version didn't work because misspelt
                response=json.dumps(
                    {"error": "item '{}' exists".format(name)}
                ), status=406, mimetype="application/json"
            )
                return conflict
        else:
            missing = ", ".join(
                [i for (i, j) in zip(["name", "price"], [name, price]) if j == None]
            )
            param_missing = app.response_class(
                # An earlier version didn't work because misspelt
                response=json.dumps(
                    {"error": "parameter(s) {} missing".format(missing)}
                ), status=404, mimetype="application/json"
            )
            return param_missing

    if operation == "update":
        if name and price:
            res = mongop_update(name, price)
            if res:
                rabbit_produce("item_updated", {"name": name, "price": res[1], "oldPrice": res[0]})
                successful = app.response_class(
                response=json.dumps(
                        {"success": "price of item '{}' successfully updated from {} to {}".format(name, res[0], res[1])}
                    ), status=200, mimetype="application/json"
                )
                return successful
            else:
                error = app.response_class(
                    response=json.dumps(
                        {"error": "item '{}' doesn't exist".format(name)}
                    ), status=404, mimetype="application/json"
                )
            return error

    if operation == "delete":
        if name:
            res = mongop_delete(name)
            if res:
                rabbit_produce("item_deleted", {"name": name})
                successful = app.response_class(
                response=json.dumps(
                        {"success": "item '{}' successfully deleted".format(name)}
                    ), status=200, mimetype="application/json"
                )
                return successful
            else:
                error = app.response_class(
                    response=json.dumps(
                        {"error": "item '{}' doesn't exist".format(name)}
                    ), status=404, mimetype="application/json"
                )
            return error

    if operation == "query":
        if name:
            results = mongo.db.promoItems.find({"name": name})
        else:
            results = mongo.db.promoItems.find()
        if results.count():
            results_list = []
            for i in results:
                results_list.append({
                    "name": i["name"],
                    "price": i["price"]
                })
            successful = app.response_class(
                response=json.dumps(
                    {"success": "item '{}' exists".format(name),
                    "result": json.dumps(results_list)
                    })
                , status=200, mimetype="application/json"
            )
            return successful
        else:
            error = app.response_class(
                response=json.dumps(
                    {"error": "item '{}' doesn't exist".format(name)}
                    ), status=404, mimetype="application/json"
            )
            return error


if __name__ == "__main__":
    print("PromoFlyer app running on port {}".format(PORT))
    app.run(port=PORT, host='0.0.0.0')