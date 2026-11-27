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
## The moon phase, sent with the sky: 0 new moon, 0.25 first quarter, 0.5 full, 0.75 last quarter.
signal moon_changed(phase: float)
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
## Her voice for the speech of the same speech_id: 16-bit mono PCM samples (little endian)
## at sample_rate Hz. Only sent when the speech came with audio (her voice is on).
signal voice_received(speech_id: int, pcm: PackedByteArray, sample_rate: int)
## Her creator switched her voice: VOICE_MODE_MUTE or VOICE_MODE_CONVERSATION.
signal voice_mode_changed(mode: StringName)
## Her creator sent her a message, so the world can show she is thinking about it.
signal creator_message_sent(text: String)
## What she understood when her creator talked out loud ("" when she heard nothing).
signal creator_heard(text: String)
## Her creator pressed (true) or released (false) the talk button: she hushes while he talks.
signal creator_talking_changed(talking: bool)
## Her creator closed the chat: she stops listening and goes back to her own life.
signal conversation_ended
signal connection_changed(is_connected: bool)
## The answer to a request sent with send_request(): it carries the same request_id.
## Use BrainQuestion.ask() to send a request and wait for its own reply.
signal reply_received(reply: Dictionary)

const DEFAULT_URL: String = "ws://127.0.0.1:8765"
## Set this environment variable to use another address, like ws://127.0.0.1:8799.
const URL_ENVIRONMENT_VARIABLE: String = "CAPYBARA_BRAIN_URL"
## Seconds between two connection attempts while the brain is offline.
const RECONNECT_DELAY_SECONDS: float = 3.0
## Largest message the world accepts. The default (64 KiB) is too small for her voice:
## a few seconds of speech in base64 already pass it. Same limit as the brain (MAX_AUDIO_BYTES).
const INBOUND_BUFFER_BYTES: int = 8 * 1024 * 1024

## Only captions, no voice.
const VOICE_MODE_MUTE: StringName = &"mute"
## She says her replies to her creator out loud.
const VOICE_MODE_CONVERSATION: StringName = &"conversation"

## The voice mode her creator chose. Sent to the brain on every connection, so a
## restarted brain learns it again.
var voice_mode: StringName = VOICE_MODE_CONVERSATION

var _socket: WebSocketPeer = WebSocketPeer.new()
var _url: String = DEFAULT_URL
var _is_connected: bool = false
var _seconds_until_reconnect: float = 0.0
var _sent_request_count: int = 0


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
	_socket.inbound_buffer_size = INBOUND_BUFFER_BYTES
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


## Her creator does not want to talk anymore. The world lets her go at once, even while
## the brain is offline; the brain, when connected, resumes her thoughts without waiting.
func end_conversation() -> void:
	conversation_ended.emit()
	if _is_connected:
		_socket.send_text(JSON.stringify({"type": "conversation_ended"}))


## Her creator pressed (true) or released (false) the talk button: the brain records the
## microphone in between. False while the brain is offline: nobody is there to hear.
func set_creator_talking(talking: bool) -> bool:
	creator_talking_changed.emit(talking)
	if not _is_connected:
		return false
	_socket.send_text(JSON.stringify({"type": "creator_talking", "talking": talking}))
	return true


## Switches her voice. Kept even while the brain is offline: it is sent when it connects.
func set_voice_mode(mode: StringName) -> void:
	if mode == voice_mode:
		return
	voice_mode = mode
	voice_mode_changed.emit(mode)
	_send_voice_mode()


## Sends a request (like {"type": "list_drawings"}) with a new request_id and returns that
## id, so the caller can recognize its reply. Returns "" while the brain is offline.
func send_request(request: Dictionary) -> String:
	if not _is_connected:
		return ""
	_sent_request_count += 1
	var request_id: String = "world-%d" % _sent_request_count
	var message: Dictionary = request.duplicate()
	message["request_id"] = request_id
	_socket.send_text(JSON.stringify(message))
	return request_id


func _send_voice_mode() -> void:
	if not _is_connected:
		return
	_socket.send_text(JSON.stringify({"type": "voice_mode", "mode": String(voice_mode)}))


func _read_messages() -> void:
	while _socket.get_available_packet_count() > 0:
		_handle_message(_socket.get_packet().get_string_from_utf8())


func _handle_message(text: String) -> void:
	var parsed: Variant = JSON.parse_string(text)
	if not parsed is Dictionary:
		push_warning("The brain sent a message that is not a JSON object: %s" % text)
		return
	var message: Dictionary = parsed
	# Only replies carry a request_id: orders from the brain never do.
	if message.has("request_id"):
		reply_received.emit(message)
		return
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
			moon_changed.emit(float(message.get("moon_phase", 0.5)))
		"listening":
			listening_requested.emit(float(message.get("seconds", 0.0)))
		"speech":
			_handle_speech(message)
		"heard":
			var heard_text: String = str(message.get("text", ""))
			creator_heard.emit(heard_text)
			if not heard_text.is_empty():
				creator_message_sent.emit(heard_text)
		_:
			push_warning("Unknown message type from the brain: %s" % message.get("type"))


## The caption goes to the balloon and, when it came with audio, her voice to her body.
func _handle_speech(message: Dictionary) -> void:
	var speech_id: int = int(message.get("speech_id", 0))
	speech_received.emit(speech_id, str(message.get("caption", "")))
	var audio_field: Variant = message.get("audio")
	if not audio_field is Dictionary:
		return
	var audio: Dictionary = audio_field
	var pcm: PackedByteArray = Marshalls.base64_to_raw(str(audio.get("pcm16_base64", "")))
	var sample_rate: int = int(audio.get("sample_rate", 0))
	if pcm.is_empty() or sample_rate <= 0:
		push_warning("The brain sent a speech with audio that cannot be played")
		return
	voice_received.emit(speech_id, pcm, sample_rate)


func _set_connected(is_connected: bool) -> void:
	if is_connected == _is_connected:
		return
	_is_connected = is_connected
	print("Brain %s (%s)" % ["connected" if is_connected else "disconnected", _url])
	if is_connected:
		_send_voice_mode()
	connection_changed.emit(is_connected)
