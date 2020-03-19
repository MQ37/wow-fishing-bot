import flask
import socket
import json
from flask import render_template, request, send_file, Response
from threading import Thread
from flask_cors import CORS, cross_origin
import cv2

class WebServer():

    def __init__(self, bot):
        self.app = flask.Flask(__name__)
        self.cors = CORS(self.app)
        self.bot = bot
        self.local_ip = socket.gethostbyname(socket.gethostname())

        def stream():
            while True:
                im = self.bot.stream_live(True)
                if im is False:
                    im = cv2.imread("error_screen.png")
                ret, im = cv2.imencode(".jpg", im)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + im.tobytes() + b'\r\n\r\n')

        @self.app.route("/live")
        def live():
            return Response(stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


        @cross_origin()
        @self.app.route("/", methods=["GET", "POST"])
        def page():
            action = request.form.get("action")
            if action:
                if action == "bobber_roi":
                    bot.bobber_roi()
                    ret = {"message": "Bobber ROI - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "start":
                    bot.start_init()
                    ret = {"message": "Start - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "stop":
                    bot.stop_init()
                    ret = {"message": "Stop - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "bobber_template":
                    bot.select_bobber_template()
                    ret = {"message": "Bobber template - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "debug":
                    bot.debug()
                    ret = {"message": "Debugging", "color": "green"}
                    return json.dumps(ret)
                elif action == "change_config":
                    if all([name in request.form for name in ["config[margin_c_b]", "config[bobber_threshold]"]]):
                        bot.change_config(request.form)
                        ret = {"message": "Changed", "color": "green"}
                        return json.dumps(ret)
                    ret = {"message": "Error", "color": "red"}
                    return json.dumps(ret)
                elif action == "alt_tab":
                    bot.alt_tab()
                    ret = {"message": "Alt Tab - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "hit_enter":
                    bot.hit_enter()
                    ret = {"message": "Enter - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "hand_cursor_im":
                    bot.create_hand_cursor()
                    ret = {"message": "Hand cursor - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "fishing_cursor_im":
                    bot.create_fishing_cursor()
                    ret = {"message": "Fishing cursor - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "get_item_list":
                    items = bot.item_list
                    items["time"] = bot.running_minutes()
                    return json.dumps(items)
                elif action == "save":
                    bot.save()
                    ret = {"message": "Save Settings - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "load":
                    bot.load()
                    ret = {"message": "Load Settings - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "limit":
                    bot.set_limit(request.form["item"], request.form["count"], request.form["time"])
                    ret = {"message": "Limit - OK", "color": "green"}
                    return json.dumps(ret)
                elif action == "shutdown":
                    bot.shutdown()
                    ret = {"message": "Shutdown - OK", "color": "green"}
                    return json.dumps(ret)

            return render_template("template.html", ip=self.local_ip, **self.bot.config_properties)

    def run(self):
        flask_t = Thread(target=self.app.run, kwargs={"host": "0.0.0.0"})
        flask_t.daemon = True
        flask_t.start()
