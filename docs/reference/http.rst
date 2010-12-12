habitat.http: message insertion by HTTP POST
============================================

.. automodule:: habitat.http

SocketServer.py hack
--------------------

The following code is quoted from Python's SocketServer.py (Python
Software Foundation License Version 2)::

    # Python 2.6.5: SocketServer.py

    def __init__(self, server_address, RequestHandlerClass):
        (...)
        self.__is_shut_down = threading.Event()
        self.__serving = False

    def serve_forever(self, poll_interval=0.5):
        self.__serving = True
        self.__is_shut_down.clear()
        while self.__serving:
            (...)
        self.__is_shut_down.set()

    def shutdown(self):
        self.__serving = False
        self.__is_shut_down.wait()

    # Python 2.7.0: SocketServer.py

    def __init__(self, server_address, RequestHandlerClass):
        (...)
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False

    def serve_forever(self, poll_interval=0.5):
        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                (...)
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def shutdown(self):
        self.__shutdown_request = True
        self.__is_shut_down.wait()

    # Program:

    def start(self):
        self.accept_thread = threading.Thread(target=self.serve_forever)
        (...)
        self.accept_thread.start()

    # The issue in 2.6.5
    #
    # Main thread: test            Accept thread
    # accept_thread.start()
    # server.shutdown()
    # self.__serving = False
    # self.__is_shut_down.wait()
    #                              server.serve_forever()
    #                              self.__serving = True
    # Hence it never shuts down and deadlocks.

The Python 2.7 implementation is more robust, and supports starting
serve_forever in a thread followed by the quick calling of shutdown.
This is admittedly not typcal use, but the habitat tests will cause
this problem.

Hence the following hack in habitat.http.SCGIApplication.start is
required. If the SocketServer has a __serving attribute (i.e.,
Python 2.6.5) then we wait for it to become true before returning
from start::

    try:
        while not self._BaseServer__serving:
            time.sleep(0.001)
    except AttributeError:
        pass

