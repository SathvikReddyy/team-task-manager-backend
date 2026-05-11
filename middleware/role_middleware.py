from functools import wraps
from flask_jwt_extended import get_jwt

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        claims=get_jwt()
        if(claims.get('role')!="admin"):
            return {
                "message": "Admin access required"
            },403
        return fn(*args,**kwargs)   
    return wrapper