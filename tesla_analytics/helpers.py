import os
from functools import wraps

from flask import request


def requires_api_token(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        app_token = request.headers.get("X-APP-TOKEN")
        if not app_token:
            return "", 401
        if app_token != os.getenv("API_TOKEN"):
            return "", 401
        return func(*args, **kwargs)

    return decorated_function
