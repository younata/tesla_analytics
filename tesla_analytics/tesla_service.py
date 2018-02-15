import teslajson


class TeslaService(object):
    def __init__(self, email='', password='', token=''):
        self.connection = teslajson.Connection(
            email=email,
            password=password,
            access_token=token
        )

    @property
    def token(self):
        return self.connection.access_token

    def vehicles(self):
        return self.connection.vehicles

    def wake_up(self, vehicle_id: str):
        self.__vehicle__(vehicle_id).wake_up()

    def charge_state(self, vehicle_id: str) -> dict:
        return self.__fetch_data__(vehicle_id, "charge_state")

    def climate(self, vehicle_id: str) -> dict:
        return self.__fetch_data__(vehicle_id, "climate_state")

    def position(self, vehicle_id: str) -> dict:
        return self.__fetch_data__(vehicle_id, "drive_state")

    def vehicle_state(self, vehicle_id: str) -> dict:
        return self.__fetch_data__(vehicle_id, "vehicle_state")

    def __fetch_data__(self, vehicle_id: str, command: str) -> dict:
        return self.__vehicle__(vehicle_id).data_request(command)

    def __vehicle__(self, vehicle_id: str) -> teslajson.Vehicle:
        return [v for v in self.vehicles() if v["id"] == vehicle_id][0]
