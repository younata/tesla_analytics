import os

import time
from logging import Logger, INFO
from typing import Callable
from urllib import error as urlliberror
from invoke import task

from tesla_analytics import api_controller
from tesla_analytics.main import app
from tesla_analytics.models import ChargeState, db, ClimateState, DriveState, VehicleState
from tesla_analytics.tesla_service import TeslaService


LOG = Logger(__name__)


@task
def web(ctx):
    LOG.setLevel(INFO)

    create_tables()

    app.register_blueprint(api_controller.blueprint, url_prefix="/api")

    app.run()


@task
def monitor(ctx):
    LOG.setLevel(INFO)
    tesla_service = TeslaService(os.environ["TESLA_EMAIL"], os.environ["TESLA_PASS"])

    create_tables()

    vehicle_id = os.getenv("VEHICLE_ID", tesla_service.vehicles()[0]["id"])

    while True:
        LOG.info("Fetching more data on car")
        try:
            tesla_service.wake_up(vehicle_id)
            charge = tesla_service.charge_state(vehicle_id)
            climate = tesla_service.climate(vehicle_id)
            position = tesla_service.position(vehicle_id)
            vehicle_state = tesla_service.vehicle_state(vehicle_id)
        except urlliberror.URLError:
            LOG.exception("Encountered error trying to fetch data, retrying in 2 minutes")
            time.sleep(120)
            continue

        add_item_to_db(lambda: ChargeState(charge))
        add_item_to_db(lambda: ClimateState(climate))
        add_item_to_db(lambda: DriveState(position))
        add_item_to_db(lambda: VehicleState(vehicle_state))
        db.session.commit()

        wait = 15  # seconds
        if charge["charging_state"] == "Charging":
            wait = 60  # 1 minute
        elif charge["charging_state"] == "Disconnected" and \
                (position.get("shift_state") is None or position.get("shift_state") == "P"):
            wait = 300  # 5 minutes

        LOG.info("Successfully pulled and stored car data, sleeping and trying again in %f minutes", wait/60)
        time.sleep(wait)


def add_item_to_db(fn: Callable):
    try:
        db.session.add(fn())
    except KeyError:
        LOG.exception("Encountered KeyError while trying to store data")


def create_tables():
    try:
        db.create_all()
    except:
        pass  # eh
