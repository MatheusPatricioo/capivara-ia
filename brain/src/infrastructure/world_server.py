import logging
import threading
from collections.abc import Callable
from types import TracebackType
from typing import Self

from websockets.exceptions import ConnectionClosed
from websockets.sync.server import Server, ServerConnection, serve

from src.infrastructure.world_messages import WorldEvent, WorldMessage, parse_world_event

logger = logging.getLogger(__name__)


def _ignore_event(event: WorldEvent) -> None:
    pass


class WorldServer:
    """WebSocket server the Godot world connects to. It sends body messages to every client.

    It runs in a background thread, so the agent loop can stay synchronous.
    Messages sent with remember=True are replayed to worlds that connect later,
    so a world opened later still shows how she feels and the current sky.

    Events sent by the world (NoticedMessage, LetterOpenedMessage) are validated and handed
    to on_event, which runs in the server thread. Invalid messages are logged and dropped.
    """

    def __init__(
        self,
        host: str,
        port: int,
        on_event: Callable[[WorldEvent], None] = _ignore_event,
    ) -> None:
        self._host = host
        self._port = port
        self._on_event = on_event
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
        for remembered_payload in remembered_payloads:
            self._send(connection, remembered_payload)
        try:
            for received_payload in connection:
                self._receive(received_payload)
        except ConnectionClosed:
            pass
        finally:
            with self._lock:
                self._clients.discard(connection)
            logger.info("World disconnected: %s", address)

    def _receive(self, payload: str | bytes) -> None:
        event = parse_world_event(payload)
        if event is None:
            logger.warning("Ignored an invalid message from the world: %.200r", payload)
            return
        try:
            self._on_event(event)
        except Exception:
            # A bug in the listener must not disconnect the world.
            logger.exception("Failed to handle a world event: %s", event)

    def _send(self, client: ServerConnection, payload: str) -> None:
        try:
            client.send(payload)
        except ConnectionClosed:
            with self._lock:
                self._clients.discard(client)
