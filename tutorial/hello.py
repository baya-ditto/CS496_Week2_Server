from flask import Flask
from flask_pymongo import PyMongo as pymongo

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/myapp_py"
mongo = pymongo(app)

@app.route("/")
def hello():
    return "Hello world!"

app.run(host='0.0.0.0', port = 8000, debug=True)
