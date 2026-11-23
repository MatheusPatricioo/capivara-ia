import logging
import threading
from types import TracebackType
from typing import Self

from websockets.exceptions import ConnectionClosed
from websockets.sync.server import Server, ServerConnection, serve

from src.infrastructure.world_messages import WorldMessage

logger = logging.getLogger(__name__)


class WorldServer:
    """WebSocket server the Godot world connects to. It sends body messages to every client.

    It runs in a background thread, so the agent loop can stay synchronous.
    Messages sent with remember=True are replayed to worlds that connect later,
    so a world opened after a drawing still shows the current chalkboard.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._clients: set[ServerConnection] = set()
        self._remembered: dict[str, str] = {}
        self._lock = threading.Lock()
        self._server: Server | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._server = serve(self._handle_client, self._host, self._port)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("World server listening on ws://%s:%s", self._host, self.port)

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

    @property
    def port(self) -> int:
        """The real port, useful when the server was created with port 0 (any free port)."""
        if self._server is None:
            return self._port
        return int(self._server.socket.getsockname()[1])

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def broadcast(self, message: WorldMessage, remember: bool = False) -> None:
        payload = message.model_dump_json()
        with self._lock:
            if remember:
                self._remembered[message.type] = payload
            clients = list(self._clients)
        for client in clients:
            self._send(client, payload)

    def _handle_client(self, connection: ServerConnection) -> None:
        # Read the address now: after an abrupt disconnect the socket can no longer tell it.
        address = connection.remote_address
        with self._lock:
            self._clients.add(connection)
            remembered_payloads = list(self._remembered.values())
        logger.info("World connected: %s", address)
        for payload in remembered_payloads:
            self._send(connection, payload)
        try:
            for _ignored_message in connection:
                pass
        except ConnectionClosed:
            pass
        finally:
            with self._lock:
                self._clients.discard(connection)
            logger.info("World disconnected: %s", address)

    def _send(self, client: ServerConnection, payload: str) -> None:
        try:
            client.send(payload)
        except ConnectionClosed:
            with self._lock:
                self._clients.discard(client)
