import os

import time
from logging import Logger
from urllib import error as urlliberror
from invoke import task

from tesla_analytics.storage_service import StorageService
from tesla_analytics.tesla_service import TeslaService


LOG = Logger(__name__)


@task
def monitor(ctx):
    storage_service = StorageService(os.environ["STORAGE_URI"])
    tesla_service = TeslaService(os.environ["TESLA_EMAIL"], os.environ["TESLA_PASS"])

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

        storage_service.store("charge_state", charge)
        storage_service.store("climate_state", climate)
        storage_service.store("drive_state", position)
        storage_service.store("vehicle_state", vehicle_state)

        wait = 15  # seconds
        if charge["charging_state"] == "Charging":
            wait = 60  # 1 minute
        elif charge["charging_state"] == "Disconnected" and position["shift_state"] is None:
            wait = 300  # 5 minutes

        LOG.info("Successfully pulled and stored car data, sleeping and trying again in %f minutes", wait/60)
        time.sleep(wait)
