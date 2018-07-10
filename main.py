from flask import Flask, request, make_response, redirect, jsonify
from flask_pymongo import PyMongo as pymongo
import bson, json
import threading

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/myapp_py"
mongo = pymongo(app)
accounts_lock = threading.Lock()
gallery_lock = threading.Lock()

@app.route("/", methods=['GET', 'POST'])
def hello():
    j = request.get_json(silent=True)
    if j != None:
        print j, type(j) is list # if j = [1,2,3,4] (jsonarray), it becomes list!
    return "Hello world!"



class my_canvas():
    # Everytime painter exits from open_canvas, painters removed, and when painters becomes empty, canvas will be closed.
    def __init__(self, image_id, image, painters=[]):
        self.image_id = image_id
        self.image = image
        self.painters = painters

    def add_painter(self, painter):
        self.painters.append(painter)

    def add_painters(self, painters):
        self.painters.extend(painters)

#canvas_id = 0
clist_lock = threading.Lock()
canvas_list = []


# TODO: participate() (with socket),  exit()(can be replaced with handler function for socket disconnection)

@app.route("/canvas/getOpenList/", methods=['GET'])
def canvas_show_open_list():
    pass
    

@app.route("/canvas/register/", methods=['POST', 'GET'])
def canvas_register():
    # Get image_id (ObjectId of image in server) to register on open canvas
    if request.method == 'GET':
        image_id = request.args.get('image_id')
        if image_id is None:
            return make_response("image_id should be given", 400)

        # add image_id to canvas_list (allow duplicate image_id in canvas_list)
        cursor = mongo.db.gallery.find({"_id" : bson.objectid.ObjectId(image_id)})
        if (cursor.count() == 1):
            image_str = cursor.next()
        elif (cursor.count() == 0):
            # ex) app tries to upload local-cached, cloud-image into open canvas, even though another app deleted it from cloud-gallery.
            return make_response("No such image_id", 400)
            # app needs to refresh.
        else:
            Exception("image_id is not unique : %s" % image_id)
        
        # insert copy of openned image into db. # should it contain original image_id?
        db_lock.acquire()
        mongo.db.gallery.insert_one({"base64" : image_str})
        db_lock.release()

        clist_lock.acquire()
        canvas_list.append(my_canvas(image_id, image_str))
        # assumption : app has cloud gallery's image, and their image_id(ObjectId) 
        #(the app would be able to register the image because it had the image on its view)
        # Prob : What if another app register its own image? (which this app doesn't have) - ignore.
        res_json = jsonify(map(lambda x: x.image_id, canvas_list))
        clist_lock.release()

        return res_json;


    else:
        pass

# helper function for app's refresh.
# image_ids app's requiring -> available (image_ids + images) among them
def filterAvailableImageInfos(req_image_ids):
    gallery_lock.acquire()
    cursor = mongo.db.gallery.find()
    gallery_lock.release()

    image_infos = []
    for result in cursor:
        image_infos.append(result)

    return list(filter(lambda x: x["_id"] in req_image_ids, image_infos))


# refresh procedure : app -> GET /gallery/getState/ -> app -> POST /gallery/getImages/ (with req_ids) -> app
@app.route("/gallery/getState/", methods=['GET'])
def sendImageIds():
    # send cloud images & canvas image list at here.
    gallery_lock.acquire()
    cursor = mongo.db.gallery.find()
    gallery_lock.release()

    image_ids = []
    for result in cursor:
        image_ids.append(str(result["_id"]))

    clist_lock.acquire()
    openImageIds = list(map(lambda x:x.image_id, canvas_list))
    clist_lock.release()

    return jsonify({"images" : image_ids, "openImages" : openImageIds})

@app.route("/gallery/postImage", methods=['POST'])
def postImage():
    cursor = mongo.db.gallery
    image = request.json['base64']
    if image is None:
        return make_response("None image", 400)

    image_id = cursor.insert({'base64':image})

@app.route("/gallery", methods=['GET'])
def getImage():
    cursor = mongo.db.gallery
    images = cursor.find()
    result = []
    for image in images:
        result.append({"_id":str(image["_id"]), "base64":image["base64"]})
    if images is None:
        return make_response("Empty image", 400)
    return jsonify(result)

@app.route("/gallery/getImages/", methods=['POST'])
def sendImages():
    req_ids_json = request.get_json(silent=True)
    if req_ids_json is None:
        return make_response("JSON array of required_image_ids should be given", 400)

    if type(req_ids_json) != list:
        return make_response("JSON array of required_image_ids should be given2", 400)

    return jsonify(filterAvailableImageInfos(req_ids_json))
# end refresh function


@app.route("/register/", methods=['POST'])
# + idea : gather facebook profile image from app, and save it in database, too.
def register():
    # Retrieve JSON from POST
    reg_json = request.get_json(silent=True)
    if (reg_json is None):
        return make_response("JSON should be given", 400)
    
    if not "token" in reg_json.keys():
        return make_response("JSON should contain token", 400)

    # insert new user info if it does not duplicate
    account_lock.acquire()
    cursor = mongo.db.accounts.find({"token" : reg_json["token"]})
    if cursor.count() > 0:
        account_lock.release()
        return make_response("Given token is already registered", 400)

    mongo.db.accounts.insert_one(reg_json)
    account_lock.release()

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
    app.run(host='0.0.0.0', port = 8080, debug=True)
