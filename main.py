from flask import Flask, request, make_response, redirect, jsonify
import bson
from flask_pymongo import PyMongo as pymongo
import json

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/myapp_py"
mongo = pymongo(app)

@app.route("/")
def hello():
    return "Hello world!"

@app.route("/register/", methods=['POST'])
def register():
    # Retrieve JSON from POST
    reg_json = request.get_json(silent=True)
    if (reg_json is None):
        return make_response("JSON should be given", 400)
    
    if not "token" in reg_json.keys():
        return make_response("JSON should contain token", 400)

    # insert new user info if it does not duplicate
    cursor = mongo.db.accounts.find({"token" : reg_json["token"]})
    if cursor.count() > 0:
        return make_response("Given token is already registered", 400)

    mongo.db.accounts.insert_one(reg_json)

    # return all other user's info.
    res_array = []
    cursor = mongo.db.accounts.find({"token" : {"$ne" : reg_json["token"]}}) # contains _id too.
    for account_info in cursor:
        _id = account_info["_id"]
        assert type(_id) == bson.objectid.ObjectId
        account_info["_id"] = str(_id)
        res_array.append(account_info)

    return jsonify(res_array)


@app.route("/login/", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        print "POST received"
        token = request.args.get('token')
        if token is None:
            return make_response("Token should be given", 400)
        json = request.get_json()
        print 'token : {} end'.format(token)

        cursor = mongo.db.accounts.find({"token" : token})

        if cursor.count() > 0:
            if cursor.count() > 1:
                Exception("Token %s exists more than once" % token)
            return make_response("Token already exists", 200)
        else:
            res = make_response("register please")
            res.mimetype = "text/plain"
            return res

        return make_response("I got your POST", 200)
    else:
        token = request.args.get('token')

        if token is None:
            return make_response("Token should be given", 400)
        print 'token : {} end'.format(token)

        cursor = mongo.db.accounts.find({"token" : token})

        if cursor.count() > 0:
            if cursor.count() > 1:
                Exception("Token %s exists more than once" % token)
            return make_response("Token already exists", 200)
        else:
            res = make_response("register please")
            res.mimetype = "text/plain"
            return res

        return make_response("I got your GET", 200)


if (__name__ == '__main__'):
    app.run(host='0.0.0.0', port = 8000, debug=True)
