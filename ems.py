import requests
import logging
from time import sleep
from threading import Thread



class Boiler:

    def __init__(self, uri: str, token: str):
        self.uri = uri.strip()
        if not self.uri.endswith("/"):
            self.uri = self.uri + '/'
        self.token = token
        self.fetch_period_sec = 3
        self.selected_flow_temperature = -1
        self.current_flow_temperature = -1
        self.heating_active = False
        self.heating_activated = False
        self.dhw_selected_temp = -1        # domestic hot water
        self.dhw_set_temp = -1
        self.dhw_storage_temp = -1
        self.dhw_flow_temp_offset = 40
        self.dhw_active = False
        self.dhw_activated = False
        Thread(target=self.__run_loop, daemon=True).start()

    def set_listener(self, listener):
        self.__listener = listener

    def __notify_listener(self):
        self.__listener()

    def __run_loop(self):
        logging.info("ems uri " + self.uri + " has been validated (fetch loop period: " + str(self.fetch_period_sec) + " sec)")
        while True:
            try:
                self.__fetch_data()
            except Exception as e:
                logging.warning(str(e))
            sleep(self.fetch_period_sec)

    def __fetch_data(self):
        resp = requests.get(self.uri)
        data = resp.json()
        self.selected_flow_temperature = data['selflowtemp']
        self.current_flow_temperature = data['curflowtemp']
        self.heating_active = data['heatingactive']
        self.heating_activated = data['heatingactivated']
        self.dhw_selected_temp = data['dhw']['settemp']
        self.dhw_set_temp = data['dhw']['seltemp']
        self.dhw_storage_temp = data['dhw']['storagetemp2']
        self.dhw_active = data['dhw']['active']
        self.dhw_activated = data['dhw']['activated']
        self.dhw_flow_temp_offset = data['dhw']['flowtempoffset']
        self.__notify_listener()


    def set_selected_flow_temperature(self, temp: float):
        update_uri = self.uri + "selflowtemp"
        resp = requests.post(update_uri,
                             headers={"Authorization": "Bearer " + self.token},
                             json={"cmd": "selflowtemp", "data": temp})
        resp.raise_for_status()
        logging.info("selflowtemp updated to " + str(temp))
        self.__fetch_data()

    def set_dhw_selected_temp(self, temp: int):
        update_uri = self.uri + "dhw/seltemp"
        resp = requests.post(update_uri,
                             headers={"Authorization": "Bearer " + self.token},
                             json={"cmd": "seltemp", "data": temp})
        resp.raise_for_status()
        logging.info("dhw/seltemp updated to " + str(temp))
        self.__fetch_data()

    def set_dhw_flow_temp_offset(self, temp: int):
        update_uri = self.uri + "dhw/flowtempoffset"
        resp = requests.post(update_uri,
                             headers={"Authorization": "Bearer " + self.token},
                             json={"cmd": "flowtempoffset", "data": temp})
        resp.raise_for_status()
        logging.info("dhw/flowtempoffset updated to " + str(temp))
        self.__fetch_data()

    def set_dhw_activated(self, on: bool):
        update_uri = self.uri + "dhw/activated"
        resp = requests.post(update_uri,
                             headers={"Authorization": "Bearer " + self.token},
                             json={"cmd": "activated", "data": on})
        resp.raise_for_status()
        logging.info("dhw/activated updated to " + str(on))
        self.__fetch_data()

'''
http://192.168.1.82/api/boiler


https://docs.emsesp.org/Commands/

https://docs.emsesp.org/tips-and-tricks/#controlling-the

curl -v -X PUT  -d "{\"dhw_selected_temp\": 49}" http://localhost:8976/0/properties/dhw_selected_temp

'''