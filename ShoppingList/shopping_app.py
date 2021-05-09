from flask import Flask, render_template, make_response, request
from flask_pymongo import PyMongo
import json

app = Flask(__name__, static_folder="files/static", template_folder="files/templates")
app.config["MONGO_URI"] = "<HIDDEN>"
mongo = PyMongo(app)

PORT = 4300

# NOTE:
# This script queries MongoDB and serves two endpoints which will be accessed by frontend.
# Namely /api/updated and /api/list
@app.route("/api/updated", methods=["GET"])
def show_timestamp():
    timestamp = mongo.db.itemsToBuy.find({"name": "_TIMESTAMP_"})[0]["lastUpdated"]

    response = app.response_class(
            response=json.dumps({"timestamp": timestamp}),
            status=200,
            mimetype='application/json'
        )
 
    return response

@app.route("/api/list", methods=["GET"])
def return_list():
    timestamp = mongo.db.itemsToBuy.find({"name": "_TIMESTAMP_"})[0]["lastUpdated"]
    
    records = mongo.db.itemsToBuy.find()
    items_to_render = [
        {"name": record["name"], "count": int(record["count"])} for record in records if record["name"] != "_TIMESTAMP_"
        ]

    response = app.response_class(
            response=json.dumps(items_to_render),
            status=200,
            mimetype='application/json'
        )

    return response

# NOTE:
# Since index.html is nothing but a reference to a bunch of JS files,
# might as well serve it as a static file using `send_from_directory()`
# Though there's not obvious benefit in doing that. 
@app.route("/")
def display_shopping_list():
    return render_template("index.html")

if __name__ == "__main__":
    print("ShoppingList app running on port {}".format(PORT))
    app.run(port=PORT, host="0.0.0.0")
 