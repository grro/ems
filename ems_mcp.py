import asyncio
import logging
import threading
from typing import Dict
from fastmcp import FastMCP
from zeroconf import IPVersion, ServiceInfo, Zeroconf
import socket
from ems import Boiler


logger = logging.getLogger(__name__)




class MDNS:

    def __init__(self):
        self.registered: Dict[str, ServiceInfo] = dict()
        self.zc = Zeroconf(ip_version=IPVersion.V4Only)
        self.service_type = "_mcp._tcp.local."
        self.hostname = socket.gethostname()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            self.local_ip = s.getsockname()[0]
        finally:
            s.close()


    def register_mdns(self, name: str, port: int):
        try:
            service_name = f"{name}.{self.service_type}"
            service_info = ServiceInfo(
                type_= self.service_type,
                name=service_name,
                addresses=[socket.inet_aton(self.local_ip)],
                port=port,
                properties={
                    "version": "1.0",
                    "path": "/sse",
                    "server_type": "fastmcp"
                },
                server=f"{self.hostname}.local.",
            )

            logging.info(f"mDNS: Registering {service_name} at {self.local_ip}:{port}")
            self.zc.register_service(service_info)
            self.registered[name] = service_info
        except Exception as e:
            logging.error(f"mDNS Registration failed: {e}")

    def unregister_mdns(self, name: str):
        service_info = self.registered.get(name)
        if service_info is not None:
            logging.info("mDNS: Unregistering service...")
            self.zc.unregister_service(service_info)
            self.zc.close()




class EmsMCPServer:
    def __init__(self, name: str, port: int, boiler: Boiler, host: str = "0.0.0.0"):
        self.name = name
        self.host = host
        self.port = port

        self.mdns = MDNS()
        self.mcp = FastMCP(self.name)
        self.boiler = boiler
        self.loop = asyncio.new_event_loop()
        self.last_state: Dict[str, bool] = dict()
        self.writable_properties = (
            "selected_flow_temperature",
            "dhw_selected_temp",
            "dhw_flow_temp_offset",
            "dhw_activated",
        )


        @self.mcp.tool(name="boiler_overview")
        def get_boiler_overview() -> dict:
            """
            Returns a compact, real-time overview of the boiler state.

            Each line is marked with:
              - [RW]: writable via set_boiler_property
              - [RO]: read-only (status only)

            Returns:
                dict: A JSON-serializable boiler state payload including values,
                      writable flags and units where applicable.
            """
            try:
                boiler = self.boiler

                def _on_off(value: bool) -> str:
                    return "ON" if value else "OFF"

                def _writable(name: str) -> bool:
                    return name in self.writable_properties

                return {
                    "ok": True,
                    "properties": {
                        "selected_flow_temperature": {
                            "value": boiler.selected_flow_temperature,
                            "unit": "C",
                            "writable": _writable("selected_flow_temperature"),
                        },
                        "current_flow_temperature": {
                            "value": boiler.current_flow_temperature,
                            "unit": "C",
                            "writable": _writable("current_flow_temperature"),
                        },
                        "heating_active": {
                            "value": boiler.heating_active,
                            "status": _on_off(boiler.heating_active),
                            "writable": _writable("heating_active"),
                        },
                        "heating_activated": {
                            "value": boiler.heating_activated,
                            "status": _on_off(boiler.heating_activated),
                            "writable": _writable("heating_activated"),
                        },
                        "dhw_selected_temp": {
                            "value": boiler.dhw_selected_temp,
                            "unit": "C",
                            "writable": _writable("dhw_selected_temp"),
                        },
                        "dhw_set_temp": {
                            "value": boiler.dhw_set_temp,
                            "unit": "C",
                            "writable": _writable("dhw_set_temp"),
                        },
                        "dhw_storage_temp": {
                            "value": boiler.dhw_storage_temp,
                            "unit": "C",
                            "writable": _writable("dhw_storage_temp"),
                        },
                        "dhw_flow_temp_offset": {
                            "value": boiler.dhw_flow_temp_offset,
                            "unit": "C",
                            "writable": _writable("dhw_flow_temp_offset"),
                        },
                        "dhw_active": {
                            "value": boiler.dhw_active,
                            "status": _on_off(boiler.dhw_active),
                            "writable": _writable("dhw_active"),
                        },
                        "dhw_activated": {
                            "value": boiler.dhw_activated,
                            "status": _on_off(boiler.dhw_activated),
                            "writable": _writable("dhw_activated"),
                        },
                    },
                }

            except Exception as e:
                logging.warning(f"Failed to generate boiler overview: {e}", exc_info=True)
                return {"ok": False, "error": f"Error generating boiler overview: {e}"}


        @self.mcp.tool(name="set_boiler_property")
        def set_boiler_property(property_name: str, value: str) -> dict:
            """
            Sets a writable boiler property via one parameterized endpoint.

            Supported properties:
              - selected_flow_temperature (float)
              - dhw_selected_temp (int)
              - dhw_flow_temp_offset (int)
              - dhw_activated (bool: true/false, on/off, 1/0)

            See boiler_overview for [RW]/[RO] status hints.
            """
            try:
                supported_properties = self.writable_properties

                if property_name not in supported_properties:
                    supported = ", ".join(supported_properties)
                    return {
                        "ok": False,
                        "error": f"Unsupported property '{property_name}'. Supported: {supported}",
                    }

                if property_name == "selected_flow_temperature":
                    parsed_value = float(value)
                    self.boiler.set_selected_flow_temperature(parsed_value)
                elif property_name in ("dhw_selected_temp", "dhw_flow_temp_offset"):
                    parsed_value = int(value)
                    if property_name == "dhw_selected_temp":
                        self.boiler.set_dhw_selected_temp(parsed_value)
                    else:
                        self.boiler.set_dhw_flow_temp_offset(parsed_value)
                else:
                    normalized = value.strip().lower()
                    truthy = {"true", "1", "on", "yes"}
                    falsy = {"false", "0", "off", "no"}
                    if normalized in truthy:
                        parsed_value = True
                    elif normalized in falsy:
                        parsed_value = False
                    else:
                        return {
                            "ok": False,
                            "error": "Invalid boolean value for 'dhw_activated'. Use true/false, on/off, 1/0 or yes/no.",
                        }
                    self.boiler.set_dhw_activated(parsed_value)

                result = {
                    "ok": True,
                    "property": property_name,
                    "value": parsed_value,
                    "writable": True,
                }
                if property_name == "dhw_activated":
                    result["status"] = "ON" if parsed_value else "OFF"
                return result
            except ValueError as e:
                return {"ok": False, "error": f"Invalid value for '{property_name}': {e}"}
            except Exception as e:
                logging.warning(f"Failed to set boiler property '{property_name}': {e}", exc_info=True)
                return {"ok": False, "error": f"Error setting '{property_name}': {e}"}


    async def __run(self) -> None:
        logger.info(f"MCP Server '{self.name}' running on http://{self.host}:{self.port}/sse")
        await self.mcp.run_async(
            transport="sse",
            host=self.host,
            port=self.port,
            uvicorn_config={"access_log": False, "log_config": None}
        )


    def start(self):
        self.mdns.register_mdns(self.name, self.port)

        def _run_loop():
            asyncio.set_event_loop(self.loop)
            try:
                self.loop.run_until_complete(self.__run())
            finally:
                self.loop.close()

        thread = threading.Thread(target=_run_loop, daemon=True)
        thread.start()


    def stop(self):
        self.mdns.unregister_mdns(self.name)
        self.loop.stop()
        logging.info("MCP Server stopped")