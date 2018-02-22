from datetime import datetime, timedelta
from logging import Logger
from typing import Callable
from urllib import error as urlliberror

from tesla_analytics.models import Vehicle, ChargeState, ClimateState, DriveState, VehicleState, db, User
from tesla_analytics.tesla_service import TeslaService


LOG = Logger(__name__)


def monitor():
    for user in User.query.filter(User.tesla_access_token.isnot(None)).all():
        for vehicle in user.vehicles:
            if vehicle.next_update_time is None or vehicle.next_update_time < current_time():
                try:
                    vehicle.next_update_time = vehicle_poller(vehicle)
                except InvalidToken:
                    notify_user_of_bad_token(user)
                    user.tesla_access_token = None
                    db.session.add(user)
                    db.session.commit()
                    break
                else:
                    db.session.add(vehicle)
                    db.session.commit()


def notify_user_of_bad_token(user):
    pass


def vehicle_poller(vehicle: Vehicle) -> datetime:
    try:
        tesla_service = TeslaService(token=vehicle.user.tesla_access_token)
    except urlliberror.URLError:
        raise InvalidToken()

    vehicle_id = vehicle.tesla_id
    try:
        tesla_service.wake_up(vehicle_id)
        charge = tesla_service.charge_state(vehicle_id)
        climate = tesla_service.climate(vehicle_id)
        position = tesla_service.position(vehicle_id)
        vehicle_state = tesla_service.vehicle_state(vehicle_id)
    except ValueError:
        users_vehicles = [v['id'] for v in tesla_service.vehicles()]
        LOG.exception("Vehicle id '{}' not found in user's vehicles ({})".format(vehicle_id, users_vehicles))
        return current_time() + timedelta(minutes=10)
    except urlliberror.URLError:
        LOG.exception("Encountered error trying to fetch data, retrying in 2 minutes")
        return current_time() + timedelta(minutes=2)

    add_item_to_db(lambda: ChargeState(charge, vehicle=vehicle))
    add_item_to_db(lambda: ClimateState(climate, vehicle=vehicle))
    add_item_to_db(lambda: DriveState(position, vehicle=vehicle))
    add_item_to_db(lambda: VehicleState(vehicle_state, vehicle=vehicle))
    db.session.commit()

    LOG.info("Successfully pulled and stored car data")
    if charge["charging_state"] == "Charging":
        return current_time() + timedelta(minutes=1)
    elif charge["charging_state"] == "Disconnected" and \
            (position.get("shift_state") is None or position.get("shift_state") == "P"):
        return current_time() + timedelta(minutes=10)
    return current_time() + timedelta(seconds=15)


def add_item_to_db(fn: Callable):
    try:
        db.session.add(fn())
    except KeyError:
        LOG.exception("Encountered KeyError while trying to store data")


def current_time() -> datetime:
    return datetime.now()


class InvalidToken(Exception):
    pass
