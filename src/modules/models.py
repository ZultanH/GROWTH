from peewee import *
import datetime

db = SqliteDatabase('./db/garduino.db')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    api_token       = CharField(default = "none")
    email_address   = CharField(default = "none")
    should_email    = BooleanField(default = False)
    username        = CharField()
    password        = CharField()
    arduino_uid     = CharField(default = "none")
    current_plan    = CharField(default = "free")
    uuid            = CharField()

class Arduino(BaseModel):
    uid             = CharField(default = "none")
    owner_uid       = CharField(default = "none")
    should_water    = BooleanField(default = False)
    verified        = BooleanField(default = False)

class Log(BaseModel):
    arduino_uid     = CharField(default = "none")
    soilTemp        = FloatField()
    airTemp         = FloatField()
    soilMoisture    = FloatField()
    humidity        = FloatField()
    heatIndex       = FloatField()
    sunlight        = FloatField()
    last_watered    = CharField(default = "never")

class BannedUser(BaseModel):
    ban_time            = CharField(default = str(datetime.datetime.now()))
    banned_by           = CharField()
    ban_reason          = CharField(default = "abusing services")
    banned_until        = DateTimeField(default = datetime.datetime.utcnow() + datetime.timedelta(weeks = 4)) # 1 month
    user                = CharField()
    old_email           = CharField()
    old_should_email    = BooleanField(default = False)
    old_password        = CharField()
    old_arduino_uid     = CharField()
    old_plan            = CharField()
    old_uuid            = CharField()

class UnbannedUser(BaseModel):
    unban_time    = CharField(default = str(datetime.datetime.now()))
    user          = CharField()
    unbanned_by   = CharField(default = "server")
    unban_reason  = CharField(default = "Unban time reached")

class Plan(BaseModel):
    plan_name   = CharField(default = "free")
    price       = IntegerField()
    access_int  = IntegerField(default = 4)

class Service(BaseModel):
    access_int      = IntegerField(default = 3)
    service_name    = CharField()

class PlanToken(BaseModel):
    token = CharField()
    discount = FloatField(default = 0.0)
    plan_name = CharField(default = 'personal')

class OldPlanToken(BaseModel):
    token = CharField()
    registree = CharField()
    time_registered = CharField(default = str(datetime.datetime.now()))
    discount = FloatField(default = 0.0)
    plan_name = CharField(default = 'personal')

class Action(BaseModel):
    arduino_uid = CharField()
    _type       = CharField()
    status      = BooleanField(default = False)


db.connect()
db.create_tables([User, Arduino, Log, Service, Plan, BannedUser, UnbannedUser, PlanToken, OldPlanToken, Action])
