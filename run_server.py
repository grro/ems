import sys
import logging
from webthing import (MultipleThings, WebThingServer)
from ems import Boiler
from ems_webthing import BoilerThing
from ems_mcp import EmsMCPServer


def run_server(port: int, ems_uri: str, token: str):
    ems_uri = ems_uri.strip()
    if not ems_uri.endswith("/"):
        ems_uri = ems_uri + '/'

    boiler = Boiler(ems_uri + "api/boiler", token)
    webthing_server = WebThingServer(MultipleThings([BoilerThing(boiler)], 'boiler'), port=port, disable_host_validation=True)
    mcp_server = EmsMCPServer("boiler", port+2, boiler)
    try:
        mcp_server.start()
        logging.info('starting the server http://localhost:' + str(port) + " (ems=" + ems_uri + ")")
        webthing_server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        mcp_server.stop()
        webthing_server.stop()
        logging.info('done')



if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(name)-20s: %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('tornado.access').setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('starlette.middleware.base').setLevel(logging.WARNING)
    logging.getLogger('fastmcp').setLevel(logging.WARNING)
    logging.getLogger('mcp').setLevel(logging.WARNING)
    logging.getLogger('mcp.server').setLevel(logging.WARNING)
    logging.getLogger('mcp.server.lowlevel.server').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').disabled = True
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    run_server(int(sys.argv[1]), sys.argv[2], sys.argv[3])




# npx @modelcontextprotocol/inspector
# http://localhost:6274/