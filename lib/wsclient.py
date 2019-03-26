import lib.constants as c

from ws4py.client.threadedclient import WebSocketClient


class WSClient(WebSocketClient):
    def __init__(self, name=None, url=None):

        super(WSClient, self).__init__(url=url, protocols=['http-only'])
        self._clientName = name

    def opened(self):
        c.cso_logger.info('WSClient opened connection')

    def closed(self, code, reason=None):
        if code != 1000:
            print('WSClient: Connection closed. Code <{0}>, Reason: <{1}>'.format(code, reason))

    def received_message(self, m):
        print('WSClient: Client received data. That\'s not what we want at this stage')
