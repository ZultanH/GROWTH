import json

def Unsuccessful(error_msg):
    return json.dumps({"success": False, "error": True, "error_msg": error_msg})

def Successful():
    return json.dumps({"success": True, "error": False})
