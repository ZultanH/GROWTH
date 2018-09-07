from flask import Flask, jsonify, request, render_template
from .modules.models import *
from .modules.weather import getWeather
from .modules.error_types import Successful, Unsuccessful
from .modules.database import user, service, api, planToken, action
from .modules.gmail import *

import json
import datetime
import pyowm
import pyjwt as jwt
import paypalrestsdk
import re

JWT_SECRET = ''

owm = pyowm.OWM('')
app = Flask(__name__)

def jwt_verify(token_str):
    try:
        jwt.decode(token_str, JWT_SECRET, algorithms=['HS256'])
        return True
    except jwt.InvalidTokenError:
        return False

def validUser(uuid):
    try:
        User.select().where(User.uuid == uuid).get()
        return True
    except User.DoesNotExist:
        return False
    
@app.route('/')
def index():
    return ':D?'


@app.route("/api/weather/current/<string:weather_type>", methods=["GET"])
def forceast_short(weather_type):
    if weather_type not in ("short", "full"):
        return Unsuccessful("invalid weather type")
    
    if weather_type == "short":
        weather_obj = getWeather(True)
        return jsonify(weather_obj)
    else:
        weather_obj = getWeather(False)
        return jsonify(weather_obj)


@app.route("/api/user/login", methods=['POST'])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    module = user(username, password)

    if not module.valid_user():
        return Unsuccessful("Invalid User")
    
    return Successful()

@app.route("/api/user/create", methods = ['POST'])
def create():
    username = request.form.get('username')
    password = request.form.get('password')

    #if not re.match('^[a-z0-9_-]{3,16}$', username):
    #    return Unsuccessful("Invalid Username Pattern")
    
    #if not re.match('^[a-zA-Z0-9_-!@#$%^&*]{6,18}$', password):
    #    return Unsuccessful("Invalid Password Pattern")
    
    user.create(username, password)
    return Successful()



@app.route("/api/arduino/claim", methods=['POST'])
def claim_arduino():
    api_token = request.form.get('api_token')
    arduino_uid = request.form.get('arduino_uid')

    module = api(api_token)

    if not module.is_valid():
        return Unsuccessful("Invalid API Key")
    
    user = module.user

    if not validUser(user):
        return Unsuccessful("Invalid User")
    
    module.claim_arduino(arduino_uid)

    return Successful()

@app.route("/api/action", methods = ['POST'])
def action_end():
    api_token        = request.form.get('api_token')
    action_type      = request.form.get('action')
    status           = request.form.get('status')

    module = api(api_token)

    if not module.is_valid():
        return Unsuccessful("Invalid API Token")
    
    if module.has_expired():
        return Unsuccessful("API Token has expired")
    
    if action_type not in ("update", "remove", "add"):
        return Unsuccessful("Invalid Action Type")
    
    arduino_uid = module.arduino_uid

    action(arduino_uid, status).handle(action_type)
    return Successful()

@app.route("/api/arduino/status", methods = ['POST'])
def status():
    api_token = request.form.get("api_token")

    module = api(api_token)

    if not module.is_valid():
        return Unsuccessful("Invalid API Token")
    
    if module.has_expired():
        return Unsuccessful("API Token has expired")
    
    return module.arduino_status

@app.route("/api/user/status", methods = ['POST'])
def user_status():
    api_token = request.form.get("api_token")

    module = api(api_token)

    if not module.is_valid():
        return Unsuccessful("Invalid API Token")
    
    if module.has_expired():
        return Unsuccessful("API Token has expired")
    
    return module.user_status


@app.route("/api/token/new", methods = ['POST'])
def give_token():
    username = request.form.get('username')
    password = request.form.get('password')

    module = user(username, password)

    if not module.valid_user():
        return Unsuccessful("Invalid User")
    
    if module.has_token():
        return Unsuccessful("User has already recieved token")
    
    token = jwt.encode({
        "user": module.uuid,
        "plan": module.current_plan
    }, JWT_SECRET, algorithm="HS256")

    return jsonify({
        "success": True,
        "error": False,
        "api_token": token
    })

@app.route("/api/token/get", methods = ['POST'])
def get_token():
    username = request.form.get('username')
    password = request.form.get('password')

    module = user(username, password)

    if not module.valid_user():
        return Unsuccessful("Invalid User")
    
    if not module.has_token():
        return Unsuccessful("User has not received a token")
    
    return jsonify({
        "success": True,
        "error": False,
        "api_token": module.get_token()
    })

@app.route("/paypal")
def paypal():
    return render_template("paypal.html")

@app.route('/payment', methods=['POST'])
def payment():
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "http://localhost:8000/payment/execute",
            "cancel_url": "http://localhost:8000/"},
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "GROWTH Personal Plan",
                    "sku": "1738",
                    "price": "20.00",
                    "currency": "AUD",
                    "quantity": 1
                }]},
            "amount": {
                "total": "20.00",
                "currency": "AUD"},
            "description": "Personal Plan for GROWTH application"}]})

    if payment.create():
        return jsonify({
            "success": True,
            "error": False,
            "paymentID": payment.id
        })
    else:
        return jsonify({
            "success": False,
            "error": True,
            "error_msg": payment.error,
            "paymentID": payment.id
        })

@app.route('/execute', methods=['POST'])
def execute():
    payment = paypalrestsdk.Payment.find(request.form['paymentID'])

    if payment.execute({'payer_id' : request.form['payerID']}):
        send_product_token(payment.payer.payer_info.email, planToken.create("personal"))
        return jsonify({
            'success' : True,
            'error': False
        })
    else:
        return jsonify({
            "success": False,
            "error": True,
            "error_msg": payment.error
        })

@app.route("/api/service/validate", methods = ['POST'])
def validate():
    username        = request.form.get('username')
    password        = request.form.get('password')
    service_token   = request.form.get("service_token")
    
    user_module     = user(username, password)
    product_module  = planToken(service_token)

    if not user_module.valid_user():
        return Unsuccessful("Invalid User")

    if not product_module.is_valid():
        return Unsuccessful("Invalid Token")
    
    product_module.register(user_module.uuid)
