from peewee import *
from .models import *

import hashlib
import uuid
import pyjwt as jwt
import json

def percentage(percent, whole):
  return (percent * whole) / 100.0

class user:
    def __init__(self, username, password):
        pass_hash = hashlib.sha256(password.encode()).hexdigest()
        self.username = username
        self.password = pass_hash
    
    def valid_user(self):
        try:
           User.select().where((User.username == self.username) & (User.password == self.password)).get()
           return True
        except User.DoesNotExist:
            return False
    
    @classmethod
    def create(cls, username, password):
        pass_hash = hashlib.sha256(password.encode()).hexdigest()
        new_user = User(
            username = username,
            password = pass_hash,
            uuid = uuid.uuid4()
        )
        new_user.save()

    @property
    def uuid(self):
        record = User.select().where((User.username == self.username) & (User.password == self.password)).get()
        return record.uuid
    
    @property
    def current_plan(self):
        record = User.select().where((User.username == self.username) & (User.password == self.password)).get()
        return record.current_plan
        
    def all_users(self):
        tbl = []
        for user in User.select():
            tbl[user.username] = [user.email_address, (True if user.should_email == 1 else False), user.arduino_uid, user.current_plan, user.uuid]
        return tbl

    def is_banned(self, user):
        try:
            BannedUser.select().where(BannedUser.user == user).get()
            return True
        except BannedUser.DoesNotExist:
            return False

    def get_ban_logs(self, user):
        tbl = {}
        
        for bannedUser in BannedUser.select().where(BannedUser.old_uuid == user):
            tbl[bannedUser.old_uuid] = [
                bannedUser.ban_time,
                bannedUser.banned_by,
                bannedUser.ban_reason,
                bannedUser.banned_until,
                bannedUser.old_arduino_uid,
                bannedUser.old_plan
            ]
        return tbl
    
    def set_plan(self, plan_name):
        User.update(current_plan = plan_name).where((User.username == self.username) & (User.password == self.password)).execute()
    
    def ban_user(self, uuid, reason):
        reason = reason if reason is not None else "Abusing services"
        user_obj = User.select().where(User.uuid == uuid).get()
        banned_user = BannedUser(
            banned_by           = self.uuid,
            ban_reason          = reason,
            old_email           = user_obj.email_address,
            old_should_email    = user_obj.should_email,
            old_password        = user_obj.password,
            old_arduino_uid     = user_obj.arduino_uid,
            old_plan            = user_obj.current_plan,
            old_uuid            = user_obj.uuid,
            old_username        = user_obj.username
        )

        banned_user.save()
        User.delete().where(User.uuid == uuid).execute()
    
    def unban_user(self, user, reason):
        reason = reason if reason is not None else "Unban time reached"
        banned_user = BannedUser.select().where(BannedUser.old_uuid == user).get()
        new_user = User(
            email_address   = banned_user.old_email_address,
            should_email    = banned_user.old_should_email,
            username        = banned_user.old_username,
            password        = banned_user.old_password,
            arduino_uid     = banned_user.old_arduino_uid,
            current_plan    = banned_user.old_plan,
            uuid            = banned_user.old_uuid
        )
        unbanned_user = UnbannedUser(
            user            = banned_user.old_uuid,
            unbanned_by     = self.uuid,
            unban_reason    = reason
        )

        BannedUser.delete().where(BannedUser.old_uuid == user).execute() #delete Banned User record
        new_user.save() #Create new User record with identical details
        unbanned_user.save() #Push into Unbanned User table to log ban

    def has_token(self):
        user_obj = User.select().where(User.uuid == self.uuid).get()
        return True if user_obj.api_token != "none" else False
    
    def get_token(self):
        user_obj = User.select().where(User.uuid == self.uuid).get()
        return user_obj.api_token
        
class api:
    def __init__(self, api_token):
        self.api_token = api_token
        self.SECRET = '>yx>";!6G"d{XS2@'

    def is_valid(self):
        api_token = self.api_token
        try:
            jwt.decode(api_token, self.SECRET, algorithms=['HS256'])
            return True
        except jwt.InvalidTokenError:
            return False

    def has_expired(self):
        api_token = self.api_token
        try:
            jwt.decode(api_token, self.SECRET, algorithms=['HS256'])
            return False
        except jwt.ExpiredSignatureError:
            return True
    
    @property
    def plan(self):
        api_token = self.api_token
        obj = jwt.decode(api_token, self.SECRET, algorithms=['HS256'])
        return obj['plan']
    
    @property
    def user(self):
        api_token = self.api_token
        obj = jwt.decode(api_token, self.SECRET, algorithms=['HS256'])
        return obj['uuid']
    
    @property
    def user_status(self):
        api_token = self.api_token
        obj = jwt.decode(api_token, self.SECRET, algorithms=['HS256'])
        user_obj = User.selet().where(User.uuid == obj.uuid).get()

        return json.loads({
            "uuid": obj['uuid'],
            "plan": obj['plan'],
            "email_address": user_obj.email_address,
            "arduino_uid": user_obj.arduino_uid,
        })
    
    @property
    def arduino_status(self):
        api_token = self.api_token
        obj = jwt.decode(api_token, self.SECRET, algorithms=['HS256'])
        user_obj = User.select().where(User.uuid == obj.uuid).get()
        arduino_obj = Arduino.select().where(Arduino.owner_uid == user_obj.uuid).get()

        return json.loads({
            "owner_uuid": obj['uuid'],
            "verified": arduino_obj.verified,
            "should_water": arduino_obj.should_water
        })
        
    def claim_arduino(self, arduino_uid):
        User.update(arduino_uid = arduino_uid).where(User.uuid == self.user).execute()
    
    def create_arduino(self):
        new_arduino = Arduino(
            uid = uuid.uuid4(),
            owner_uid = self.user,
            verified = False
        )
        new_arduino.save()

    def should_water(self, boolean):
        Arduino.update(should_water = boolean).where(Arduino.owner_uid == self.user).execute()

    @property
    def arduino_uid(self):
        token_obj = jwt.decode(self.api_token, self.SECRET, algorithms=['HS256'])
        user_uuid = token_obj['uuid']
        arduino_obj = Arduino.select().where(Arduino.owner_uid == user_uuid).get()
        return arduino_obj.uid

class service:
    def __init__(self, uid, service_name):
        self.uid = uid
        self.service_name = service_name

    def is_valid(self):
        try:
            User.select().where(User.uid == self.uid).get()
            return True
        except User.DoesNotExist:
            return False
        
    @property
    def user(self):
        return User.select().where(User.uid == self.uid).get()
    
    def can_access(self):
        return self.service_name in self.available_services()
    
    def available_services(self):
        user = self.user
        user_current_plan = user.current_plan
        plan_obj = Plan.select().where(Plan.plan_name == user_current_plan).get()
        available_services = [Service.service_name for Service in Service.select().where(Service.access_int <= plan_obj.access_int)]
        return available_services

class planToken:
    def __init__(self, token):
        self.token = token
    
    def is_valid(self):
        try:
            PlanToken.select().where(PlanToken.token == self.token).get()
            return True
        except PlanToken.DoesNotExist:
            return False
    
    def expire(self):
        PlanToken.delete().where(PlanToken.token == self.token).execute()

    @property
    def plan(self):
        token_obj = PlanToken.select().where(PlanToken.token == self.token).get()
        return token_obj.plan_name

    @property
    def price(self):
        plan_obj = Plan.select().where(Plan.plan_name == self.plan).get()
        return plan_obj.price

    def has_discount(self):
        token_obj = PlanToken.select().where(PlanToken.token == self.token).get()
        return True if token_obj.discount > 0.0 else False
    
    @property
    def discount_price(self):
        original_price = self.price

        if self.has_discount():
            token_obj = PlanToken.select().where(PlanToken.token == self.token).get()
            percent_discount = token_obj.discount
            return original_price - percentage(percent_discount, original_price)
        else:
            return original_price
    
    @classmethod
    def create(cls, plan_name, discount = 0.0):
        new_token = PlanToken(
            token = uuid.uuid4(),
            discount = discount,
            plan_name = plan_name,
        )
        new_token.save()
        return new_token.token

    def register(self, user):
        old_token = PlanToken.select().where(PlanToken.token == self.token).get() #grab existing token model
        logged_token = OldPlanToken( #Push token into logs
            token       = self.token,
            registree   = user,
            discount    = old_token.discount,
            plan_name   = old_token.plan_name
        )
        PlanToken.delete().where(PlanToken.token == self.token).execute() #delete token to prevent abuse
        logged_token.save() #save log

class action:
    def __init__(self, uid, status):
        self.uid = uid
        self.status = status
    
    def add(self):
        new_action = Action(
            arduino_uid = self.uid,
            status = self.status
        )
        new_action.save()

    def delete(self):
        Action.delete().where(Action.arduino_uid == self.uid).execute()

    def get_status(self):
        action_obj = Action.select().where(Action.arduino_uid == self.uid).get()
        return True if action_obj.status == 1 else False
    
    def update(self):
        Action.update({"arduino_uid": self.uid, "status": self.status}).where(Action.arduino_uid == self.uid).execute()

    def handle(self, _type):
        if _type == "add":
            self.add()
        elif _type == "remove":
            self.delete()
        elif _type == "update":
            self.update()
