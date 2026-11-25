extends Node

## Connection to the capybara's brain (the Python service), registered as the autoload "Brain".
## It receives orders and turns them into signals, and reports what happens in the world
## (like something the capybara noticed): no AI logic lives here.
## While the brain is offline it keeps trying to connect, so the world can open first.

signal go_to_requested(point_id: StringName)
## How the capybara feels: her strongest emotion ("joy", "loneliness"... or "calm"), how strong
## it is (0 to 1), valence (-1 bad to 1 good) and arousal (0 calm to 1 agitated).
signal feelings_changed(emotion: StringName, intensity: float, valence: float, arousal: float)
## The time of day and the weather: day_fraction from 0 (midnight) to 1, how many real
## seconds a world day lasts (to move the sun between messages) and the sky ("clear",
## "cloudy", "fog", "rain", "storm" or "unknown").
signal sky_changed(day_fraction: float, day_length_seconds: float, weather: StringName)
## Every letter in the mailbox, the newest first. Each one is a Dictionary with file_name,
## written_at ("2026-11-25T14:30"), text, unread, and reply and replied_at (null while
## her creator has not answered).
signal mailbox_changed(letters: Array)
## The latest pages of her diary, the newest day first. Each one is a Dictionary with day
## ("2026-11-25") and entries, an Array of Dictionaries with written_at and text, the
## earliest first.
signal diary_changed(days: Array)
## She stops, faces her creator and listens for the given seconds. Sent again on every
## exchange: each one only extends the time.
signal listening_requested(seconds: float)
## Something she says, for the speech balloon. speech_id grows with every speech, so an
## older one that arrives late can be dropped.
signal speech_received(speech_id: int, caption: String)
## Her creator sent her a message, so the world can show she is thinking about it.
signal creator_message_sent(text: String)
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


## Tells the brain the capybara noticed something. Dropped while the brain is offline:
## she will notice it again the next time she walks by.
func report_noticed(thing_id: StringName, description: String) -> void:
	print("Capybara noticed %s" % thing_id)
	if not _is_connected:
		return
	var event: Dictionary = {"type": "noticed", "thing": String(thing_id), "description": description}
	_socket.send_text(JSON.stringify(event))


## Tells the brain her creator opened a letter, so it marks the letter as read. Dropped while
## the brain is offline: the letter stays unread and is reported again next time.
func report_letter_opened(file_name: String) -> void:
	if not _is_connected:
		return
	_socket.send_text(JSON.stringify({"type": "letter_opened", "letter": file_name}))


## Sends her creator's reply to a letter. False while the brain is offline: nothing was sent,
## so the text stays in the box for him to send again later.
func report_letter_replied(file_name: String, text: String) -> bool:
	if not _is_connected:
		return false
	_socket.send_text(JSON.stringify({"type": "letter_replied", "letter": file_name, "text": text}))
	return true


## Sends what her creator typed to her. False while the brain is offline: nothing was
## sent, so the text stays in the box for him to send again.
func send_creator_message(text: String) -> bool:
	if not _is_connected:
		return false
	_socket.send_text(JSON.stringify({"type": "creator_said", "text": text}))
	creator_message_sent.emit(text)
	return true


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
		"feelings":
			feelings_changed.emit(
				StringName(str(message.get("emotion", "calm"))),
				float(message.get("intensity", 0.0)),
				float(message.get("valence", 0.0)),
				float(message.get("arousal", 0.3)),
			)
		"mailbox":
			var letters: Variant = message.get("letters", [])
			mailbox_changed.emit(letters if letters is Array else [])
		"diary":
			var days: Variant = message.get("days", [])
			diary_changed.emit(days if days is Array else [])
		"sky":
			sky_changed.emit(
				float(message.get("day_fraction", 0.5)),
				float(message.get("day_length_seconds", 86400.0)),
				StringName(str(message.get("weather", "unknown"))),
			)
		"listening":
			listening_requested.emit(float(message.get("seconds", 0.0)))
		"speech":
			speech_received.emit(int(message.get("speech_id", 0)), str(message.get("caption", "")))
		_:
			push_warning("Unknown message type from the brain: %s" % message.get("type"))


func _set_connected(is_connected: bool) -> void:
	if is_connected == _is_connected:
		return
	_is_connected = is_connected
	print("Brain %s (%s)" % ["connected" if is_connected else "disconnected", _url])
	connection_changed.emit(is_connected)
