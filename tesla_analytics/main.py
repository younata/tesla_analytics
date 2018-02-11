import os
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgres://tesla:{passwd}@{host}/tesla".format(
    passwd=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
