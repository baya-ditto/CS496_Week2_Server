from flask import Flask, request, make_response, redirect, jsonify
from flask_pymongo import PyMongo as pymongo
import bson, json
import threading
#import mysocket

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/myapp_py"
mongo = pymongo(app)
accounts_lock = threading.Lock()
gallery_lock = threading.Lock()
clist_lock = threading.Lock()

@app.route("/", methods=['GET', 'POST'])
def hello():
    j = request.get_json(silent=True)
    if j != None:
        print j, type(j) is list # if j = [1,2,3,4] (jsonarray), it becomes list!
    return "Hello world!"




# helper function for app's refresh.
# image_ids app's requiring -> available (image_ids + images) among them
def filterAvailableImageInfos(req_image_ids):
    gallery_lock.acquire()
    cursor = mongo.db.gallery.find()
    gallery_lock.release()

    image_infos = []
    for result in cursor:
        image_infos.append(result)

    return list(filter(lambda x: str(x["_id"]) in req_image_ids, image_infos))


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

@app.route("/gallery/getImages/", methods=['POST'])
def sendImages():
    req_ids_json = request.get_json(silent=True)
    if req_ids_json is None:
        return make_response("JSON array of required_image_ids should be given", 400)

    if type(req_ids_json) != list:
        return make_response("JSON array of required_image_ids should be given2", 400)
    a = filterAvailableImageInfos(req_ids_json)
    result = []
    for imageInfo in a:
        result.append({"_id":str(imageInfo["_id"]), "base64":imageInfo["base64"]})
    return jsonify(result)
# end refresh function

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



@app.route("/register/", methods=['POST'])
# + idea : gather facebook profile image from app, and save it in database, too.
def register():
    # Retrieve JSON from POST
    reg_json = request.get_json(silent=True)
    if (reg_json is None):
        print "here0"
        return make_response("JSON should be given", 400)
    
    print reg_json
    if not "token" in reg_json.keys():
        print "token"
        return make_response("JSON should contain token", 400)
    if not "nickname" in reg_json.keys():
        print "nickname"
        return make_response("JSON should contain nickname", 400)
    if not "name" in reg_json.keys():
        print "name"
        return make_response("JSON should contain name", 400)
    if not "phoneNumber" in reg_json.keys():
        print "phoneNumber"
        return make_response("JSON should contain phoneNumber", 400)
    #if not "emailAddress" in reg_json.keys():
    #    return make_response("JSON should contain emailAddress", 400)
    if not "profile" in reg_json.keys():
        print "profile"
        return make_response("JSON should contain profile", 400)


    print "here1"
    # insert new user info if it does not duplicate
    accounts_lock.acquire()
    cursor = mongo.db.accounts.find({"token" : reg_json["token"]})
    if cursor.count() > 0:
        print "here2"
        accounts_lock.release()
        return make_response("Given token is already registered", 400)

    print "here3"
    mongo.db.accounts.insert_one(reg_json)
    accounts_lock.release()
    return make_response("register success", 200)

@app.route("/contact/", methods=['GET'])
def contact():
    token = request.args.get('token')
    if token is None:
        return make_response("Token should be given", 400)

    accounts_lock.acquire()
    count = mongo.db.accounts.find({"token" : token}).count()
    accounts_lock.release()
    if count != 1:
        return make_response("Wrong token", 400)
        
    # return all other user's info.
    # -> temporary return all user's info
    res_array = []
    accounts_lock.acquire()
    #cursor = mongo.db.accounts.find({"token" : {"$ne" : token}}) # contains _id too.
    cursor = mongo.db.accounts.find({})
    accounts_lock.release()

    for account_info in cursor:
        _id = account_info["_id"]
        assert type(_id) == bson.objectid.ObjectId
        account_info["_id"] = str(_id)
        res_array.append(account_info)

    return jsonify(res_array)


@app.route("/login/", methods=['GET'])
def login():
    token = request.args.get('token')

    if token is None:
        return make_response("Token should be given", 400)
    print 'token : {} end'.format(token)

    cursor = mongo.db.accounts.find({"token" : token})

    if cursor.count() > 0:
        if cursor.count() > 1:
            Exception("Token %s exists more than once" % token)
        return make_response("login success", 200)
    else:
        res = make_response("register please")
        res.mimetype = "text/plain"
        return res


class canvas_list():
    def __init__(self):
        #self.canvases = []
        self.idTable = dict()
        #self.primaryId = 0
        self.lock = threading.Lock()

    # insert success -> True / fail -> False
    def insert(self, canvas):
        self.lock.acquire()
        # do not allow duplicate images
        if (self.idTable[canvas.image_id] if canvas.image_id in self.idTable.keys() else False):
            self.lock.release()
            return False
        #self.canvases.append(canvas)
        self.idTable[canvas.image_id] = canvas
        self.lock.release()
        return True
    
    def remove(self, canvas):
        self.lock.acquire()
        if not (self.idTable[canvas.image_id] if canvas.image_id in self.idTable.keys() else False):
            self.lock.release()
            return False
        #self.canvases.remove(canvas)
        self.idTable[canvas.image_id] = None
        self.lock.release()
        return True
    
    # Get my_canvas list from idTable (image_id -> (my_canvas or None))
    def getCanvasList(self):
        items = self.idTable.items()
        return list(filter(lambda x: x.__class__ is my_canvas, items))


# painter : {token, socket, (canvas_list)
class my_canvas():
    # Everytime painter exits from open_canvas, painters removed, and when painters becomes empty, canvas will be closed.
    def __init__(self, _id, image_id, image, painters=[]):
        self._id = _id
        self.image_id = image_id
        self.image = image
        self.painters = painters
        self.actions = []

    def add_painter(self, painter):
        self.painters.append(painter)
        painter.canvas = self

    def remove_painter(self, painter):
        self.painters.remove(painter)
        painter.canvas = None

    def getSocketList(self):
        return list(filter(lambda x: x != None, map(lambda x: x.socket, self.painters)))

class painter():
    def __init__(self, token, socket=None, canvas=None, actions=[]):
        self.token = token
        self.socket = socket
        self.canvas = canvas
        self.actions=[]


#canvas_id = 0
clist = canvas_list()
token_to_painter = dict() # user token -> painter

'''
@app.route("/canvas/participate/", methods=['GET'])
def participate():
    token = request.args.get("token")
    image_id = request.args.get("image_id")

    if token is None:
        return make_response("token should be given", 400)
    if image_id is None:
        return make_response("image_id should be given", 400)

    # image_id validity check
    if image_id in clist.idTable.keys() and clist.idTable[image_id] != None:
        # update user info + add user into painter list
        user = painter(token)
        clist.idTable[image_id].add_painter(user)
        token_to_painter[token] = user

        # user.socket will be set socket connect handler.
    else:
        return make_response("image_id is not valid", 400)
'''


@app.route("/canvas/getOpenList/", methods=['GET'])
def canvas_show_open_list():
    clist.lock.acquire()
    res_json = jsonify(map(lambda x: x.image_id, clist.getCanvasList()))
    clist.lock.release()
    return res_json
    

@app.route("/canvas/register/", methods=['POST', 'GET'])
def canvas_register():
    # Get image_id (ObjectId of image in server) to register on open canvas
    if request.method == 'GET':
        image_id = request.args.get('image_id')
        if image_id is None:
            return make_response("image_id should be given", 400)

        # Image_id validity check
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
        _id = mongo.db.canvas.insert_one({"base64" : image_str})
        db_lock.release()

        clist.lock.acquire()
        clist.insert(my_canvas(str(_id), image_id, image_str))
        # assumption : app has cloud gallery's image, and their image_id(ObjectId) 
        #(the app would be able to register the image because it had the image on its view)
        # Prob : What if another app register its own image? (which this app doesn't have) - ignore.
        res_json = jsonify(map(lambda x: x.image_id, clist.getCanvasList()))
        clist.lock.release()

        return res_json;


    else:
        pass

def handler(s):
    header = s.recv(1024)
    if not header:
        print "no header"
        return

    header_json = json.loads(header)

    print "parsed header : "
    print header_json
    print "----------------"

    if not "token" in header_json.keys():
        s.close()
        return
    if not "image_id" in header_json.keys():
        s.close()
        return

    token = header_json["token"]
    image_id = header_json["image_id"]

    user = painter(token, s)
    clist.lock.acquire()
    if image_id in clist.idTable.keys() and clist.idTable[image_id] != None:
        # update user (token, socket, canvas) + insert into canvas.painters

        clist.idTable[image_id].add_painter(user)
        token_to_painter[token] = user

        clist.lock.release()
    else:
        clist.lock.release()
        print "image_id is not valid"
        return
    
    while True:
        data = s.recv(1024)
        if not data:
            break

        # manage user action (Json {"point" : {"x" : 1, "y" : 2}, "color" : 0xffffff})
        action = json.loads(data)

        user.actions.append(action)
        print "Get user action : ", action

        for sock in canvas.getSocketList():
            sock.sendall(json.dumps(action))


thread_count = 0
max_thread = 4
tlock = threading.Lock()


if (__name__ == '__main__'):
    app.run(host='0.0.0.0', port = 8080, debug=True)
    
    '''
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8888))

    while True:
        server_socket.listen(10)
        conn, addr = server_socket.accept()

        print "connected : "
        print (conn, addr)

        tlock.acquire()
        if (thread_num <= max_thread):
            thread_num += 1
            sockets.append(conn)
            print "sockets : ", sockets
            tlock.release()
            t = threading.Thread(target=handler, args=(conn,))
            t.start()
        else:
            tlock.release()
    '''
