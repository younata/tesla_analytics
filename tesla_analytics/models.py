from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

from tesla_analytics.main import app

db = SQLAlchemy(app)


class ChargeState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    data = db.Column(db.JSON)

    def __init__(self, data):
        data = dict(data)
        timestamp = datetime.fromtimestamp(data.pop("timestamp") / 1000.0)
        super(ChargeState, self).__init__(timestamp=timestamp, data=data)

    def serialize(self):
        return {**self.data, **{"timestamp": self.timestamp.isoformat()}}


class ClimateState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    data = db.Column(db.JSON)

    def __init__(self, data):
        data = dict(data)
        timestamp = datetime.fromtimestamp(data.pop("timestamp") / 1000.0)
        super(ClimateState, self).__init__(timestamp=timestamp, data=data)

    def serialize(self):
        return {**self.data, **{"timestamp": self.timestamp.isoformat()}}


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
        data = dict(data)
        timestamp = datetime.fromtimestamp(data.pop("timestamp") / 1000.0)
        gps_as_of = datetime.fromtimestamp(data.pop("gps_as_of"))
        latitude = data.pop("latitude")
        longitude = data.pop("longitude")
        power = data.pop("power")
        shift_state = data.pop("shift_state")
        speed = data.pop("speed")

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

    def serialize(self):
        return {**self.data, **{
            "timestamp": self.timestamp.isoformat(),
            "gps_as_of": self.gps_as_of.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "power": self.power,
            "shift_state": self.shift_state,
            "speed": self.speed,
        }}


class VehicleState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    data = db.Column(db.JSON)

    def __init__(self, data):
        data = dict(data)
        timestamp = datetime.fromtimestamp(data.pop("timestamp") / 1000.0)
        super(VehicleState, self).__init__(timestamp=timestamp, data=data)

    def serialize(self):
        return {**self.data, **{"timestamp": self.timestamp.isoformat()}}
