extends Node

## Connection to the capybara's brain (the Python service), registered as the autoload "Brain".
## It only receives orders and turns them into signals: no AI logic lives here.
## While the brain is offline it keeps trying to connect, so the world can open first.

signal go_to_requested(point_id: StringName)
signal chalkboard_changed(drawings: Array)
signal connection_changed(is_connected: bool)

const DEFAULT_URL: String = "ws://127.0.0.1:8765"
## Set this environment variable to use another address, like ws://127.0.0.1:8799.
const URL_ENVIRONMENT_VARIABLE: String = "CAPYBARA_BRAIN_URL"
## Seconds between two connection attempts while the brain is offline.
const RECONNECT_DELAY_SECONDS: float = 3.0

var _socket: WebSocketPeer = WebSocketPeer.new()
var _url: String = DEFAULT_URL
var _is_connected: bool = false
var _seconds_until_reconnect: float = 0.0


func _ready() -> void:
	var custom_url: String = OS.get_environment(URL_ENVIRONMENT_VARIABLE)
	if not custom_url.is_empty():
		_url = custom_url
	_connect_to_brain()


func _process(delta: float) -> void:
	_socket.poll()
	match _socket.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			_set_connected(true)
			_read_messages()
		WebSocketPeer.STATE_CLOSED:
			_set_connected(false)
			_seconds_until_reconnect -= delta
			if _seconds_until_reconnect <= 0.0:
				_connect_to_brain()


## A fresh peer per attempt: a closed WebSocketPeer is not reused.
func _connect_to_brain() -> void:
	_seconds_until_reconnect = RECONNECT_DELAY_SECONDS
	_socket = WebSocketPeer.new()
	var error: Error = _socket.connect_to_url(_url)
	if error != OK:
		push_warning("Could not start a connection to the brain at %s (error %d)" % [_url, error])


func _read_messages() -> void:
	while _socket.get_available_packet_count() > 0:
		_handle_message(_socket.get_packet().get_string_from_utf8())


func _handle_message(text: String) -> void:
	var parsed: Variant = JSON.parse_string(text)
	if not parsed is Dictionary:
		push_warning("The brain sent a message that is not a JSON object: %s" % text)
		return
	var message: Dictionary = parsed
	match message.get("type"):
		"go_to":
			go_to_requested.emit(StringName(str(message.get("point", ""))))
		"chalkboard":
			var drawings: Variant = message.get("drawings", [])
			chalkboard_changed.emit(drawings if drawings is Array else [])
		_:
			push_warning("Unknown message type from the brain: %s" % message.get("type"))


func _set_connected(is_connected: bool) -> void:
	if is_connected == _is_connected:
		return
	_is_connected = is_connected
	print("Brain %s (%s)" % ["connected" if is_connected else "disconnected", _url])
	connection_changed.emit(is_connected)
