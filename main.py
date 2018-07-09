from flask import Flask, request, make_response, redirect
from flask_pymongo import PyMongo as pymongo
import json

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/myapp_py"
mongo = pymongo(app)

@app.route("/")
def hello():
    return "Hello world!"

@app.route("/register/", methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        pass
    else:
        pass


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
            #return redirect("http://qppepdp.koreacentral.cloudapp.azure.com:8000/register/", code=302)
            res = make_response("register please")
            res.mimetype = "text/plain"
            return res
            #mongo.db.accounts.insert_one({"token" : token})

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
            #return redirect("http://qppepdp.koreacentral.cloudapp.azure.com:8000/register/", code=302)
            #mongo.db.accounts.insert_one({"token" : token})
            res = make_response("register please")
            res.mimetype = "text/plain"
            return res

        return make_response("I got your GET", 200)

if (__name__ == '__main__'):
    app.run(host='0.0.0.0', port = 8000, debug=True)
