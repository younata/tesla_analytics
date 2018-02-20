from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

from tesla_analytics.application import app

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, index=True)
    password_hash = db.Column(db.String)
    tesla_access_token = db.Column(db.String, nullable=True)
    vehicles = db.relationship('Vehicle', backref='user')


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tesla_id = db.Column(db.String, index=True, nullable=False)
    vin = db.Column(db.String, nullable=True)
    color = db.Column(db.String, nullable=True)
    name = db.Column(db.String, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    next_update_time = db.Column(db.DateTime, nullable=True)

    charge_states = db.relation('ChargeState', backref='vehicle')
    climate_states = db.relation('ClimateState', backref='vehicle')
    drive_states = db.relation('DriveState', backref='vehicle')
    vehicle_states = db.relation('VehicleState', backref='vehicle')

    def serialize(self):
        return {
            "vehicle_id": self.tesla_id,
            "vin": self.vin,
            "color": self.color,
            "name": self.name,
        }


class ChargeState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    data = db.Column(db.JSON)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)

    def __init__(self, data, vehicle):
        data = dict(data)
        timestamp = datetime.fromtimestamp(data.pop("timestamp") / 1000.0)
        super(ChargeState, self).__init__(timestamp=timestamp, data=data, vehicle=vehicle)

    def serialize(self):
        return {**self.data, **{"timestamp": self.timestamp.isoformat() + "Z"}}


class ClimateState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    data = db.Column(db.JSON)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)

    def __init__(self, data, vehicle):
        data = dict(data)
        timestamp = datetime.fromtimestamp(data.pop("timestamp") / 1000.0)
        super(ClimateState, self).__init__(timestamp=timestamp, data=data, vehicle=vehicle)

    def serialize(self):
        return {**self.data, **{"timestamp": self.timestamp.isoformat() + "Z"}}


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
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)

    def __init__(self, data, vehicle):
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
            data=data,
            vehicle=vehicle
        )

    def serialize(self):
        return {**self.data, **{
            "timestamp": self.timestamp.isoformat() + "Z",
            "gps_as_of": self.gps_as_of.isoformat() + "Z",
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
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)

    def __init__(self, data, vehicle):
        data = dict(data)
        timestamp = datetime.fromtimestamp(data.pop("timestamp") / 1000.0)
        super(VehicleState, self).__init__(timestamp=timestamp, data=data, vehicle=vehicle)

    def serialize(self):
        return {**self.data, **{"timestamp": self.timestamp.isoformat() + "Z"}}
