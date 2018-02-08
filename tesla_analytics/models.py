from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

from tesla_analytics.main import app

db = SQLAlchemy(app)


class ChargeState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    data = db.Column(db.JSON)

    def __init__(self, data):
        timestamp = datetime.fromtimestamp(data.pop("timestamp"))
        super(ChargeState, self).__init__(timestamp=timestamp, data=data)


class ClimateState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    data = db.Column(db.JSON)

    def __init__(self, data):
        timestamp = datetime.fromtimestamp(data.pop("timestamp"))
        super(ClimateState, self).__init__(timestamp=timestamp, data=data)


class DriveState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    gps_as_of = db.Column(db.DateTime)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    power = db.Column(db.Float)
    shift_state = db.Column(db.String, nullable=True)
    speed = db.Column(db.Integer, nullable=True)
    data = db.Column(db.JSON)

    def __init__(self, data):
        timestamp = datetime.fromtimestamp(data.pop("timestamp"))
        gps_as_of = datetime.fromtimestamp(data.pop("gps_as_of"))
        latitude = datetime.fromtimestamp(data.pop("latitude"))
        longitude = datetime.fromtimestamp(data.pop("longitude"))
        power = datetime.fromtimestamp(data.pop("power"))
        shift_state = datetime.fromtimestamp(data.pop("shift_state"))
        speed = datetime.fromtimestamp(data.pop("speed"))

        super(DriveState, self).__init__(
            timestamp=timestamp,
            gps_as_of=gps_as_of,
            latitude=latitude,
            longitude=longitude,
            power=power,
            shift_state=shift_state,
            speed=speed,
            data=data
        )


class VehicleState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    data = db.Column(db.JSON)

    def __init__(self, data):
        timestamp = datetime.fromtimestamp(data.pop("timestamp"))
        super(VehicleState, self).__init__(timestamp=timestamp, data=data)
