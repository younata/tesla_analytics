from logging import Logger, INFO
from time import sleep

import bcrypt
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from tesla_analytics import workers
from tesla_analytics.application import app
from tesla_analytics.models import db, User, Vehicle, ChargeState, ClimateState, DriveState, VehicleState
from tesla_analytics.tesla_service import TeslaService

LOG = Logger(__name__)


manager = Manager(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)


@manager.command
def monitor():
    LOG.setLevel(INFO)
    while True:
        workers.monitor()
        sleep(5)


@manager.command
def create_user(email, password, tesla_email, tesla_password):
    user = User(
        email=email,
        password_hash=bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt()).decode("utf-8")
    )
    _update_users_vehicles(user, tesla_email, tesla_password)


@manager.command
def test_user(email, password):
    user = User(
        email=email,
        password_hash=bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt()).decode("utf-8")
    )
    db.session.add(user)
    db.session.commit()
    print("Successfully added user!")


@manager.command
def login(email, tesla_email, tesla_password):
    user = User.find_by(email=email)
    _update_users_vehicles(user, tesla_email, tesla_password)


def _update_users_vehicles(user, tesla_email, tesla_password):
    tesla_service = TeslaService(email=tesla_email, password=tesla_password)
    user.tesla_access_token = tesla_service.token

    for tesla_vehicle in tesla_service.vehicles():
        stored_vehicle = user.vehicles.find_by(tesla_id=tesla_vehicle["id"]).first()
        if stored_vehicle:
            stored_vehicle.vin = tesla_vehicle["vin"]
            stored_vehicle.color = tesla_vehicle["color"]
            stored_vehicle.name = tesla_vehicle["display_name"]
        else:
            stored_vehicle = Vehicle(
                tesla_id=tesla_vehicle["id"],
                vin=tesla_vehicle["vin"],
                color=tesla_vehicle["color"],
                name=tesla_vehicle["display_name"],
                user=user
            )
        db.session.add(stored_vehicle)

    vehicle_ids = [v["id"] for v in tesla_service.vehicles()]

    for stored_vehicle in user.vehicles:
        if stored_vehicle.tesla_id not in vehicle_ids:
            db.session.delete(ChargeState.vehicle_id.equals(stored_vehicle.id))
            db.session.delete(ClimateState.vehicle_id.equals(stored_vehicle.id))
            db.session.delete(DriveState.vehicle_id.equals(stored_vehicle.id))
            db.session.delete(VehicleState.vehicle_id.equals(stored_vehicle.id))
            db.session.delete(stored_vehicle)
            print("Deleting vehicle '{}' from user".format(stored_vehicle.name))

    db.session.add(user)
    db.session.commit()
    print("Successfully logged in user!")


if __name__ == "__main__":
    manager.run()
