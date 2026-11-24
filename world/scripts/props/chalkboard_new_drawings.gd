class_name ChalkboardNewDrawings
extends Node

## Notices when the brain pins a new drawing on the chalkboard and has the gallery draw it
## stroke by stroke once the capybara reaches the board.
##
## The brain sends every pinned drawing (newest last) each time the board changes, and sends
## them again whenever the world connects. So the first message after connecting is only
## remembered: what it brings was already drawn before, it is not new.

## Seconds since her arrival during which she counts as still at the board (she stays a few
## seconds; the drawing message may come right after she arrived).
const STILL_AT_BOARD_SECONDS: float = 4.0
## If she never arrives (the path is blocked, nobody drives her), draw anyway after this.
const MAX_WAIT_SECONDS: float = 20.0

var _gallery: ChalkboardGallery
var _arrival_point: InteractionPoint
var _newest_signature: String = ""
var _is_first_message_since_connection: bool = true
var _wait_timer: Timer = Timer.new()


## arrival_point may be null: then the drawing starts right away.
func _init(gallery: ChalkboardGallery, arrival_point: InteractionPoint) -> void:
	_gallery = gallery
	_arrival_point = arrival_point


func _ready() -> void:
	_wait_timer.one_shot = true
	_wait_timer.timeout.connect(_start_drawing)
	add_child(_wait_timer)
	Brain.chalkboard_changed.connect(_on_chalkboard_changed)
	Brain.connection_changed.connect(_on_connection_changed)
	if _arrival_point != null:
		_arrival_point.capybara_arrived.connect(_start_drawing)


func _on_connection_changed(is_connected: bool) -> void:
	if is_connected:
		_is_first_message_since_connection = true


func _on_chalkboard_changed(drawings: Array) -> void:
	if drawings.is_empty() or not drawings.back() is Dictionary:
		return
	var newest: Dictionary = drawings.back()
	var signature: String = JSON.stringify(newest)
	var is_new: bool = signature != _newest_signature and not _is_first_message_since_connection
	_newest_signature = signature
	_is_first_message_since_connection = false
	if is_new:
		_prepare(newest)


func _prepare(newest: Dictionary) -> void:
	var strokes: ChalkStrokes = ChalkStrokes.from_message(newest)
	if strokes.is_empty():
		return
	_gallery.wait_for_new_drawing(strokes)
	if _arrival_point == null or _arrival_point.seconds_since_capybara_arrived() <= STILL_AT_BOARD_SECONDS:
		_start_drawing()
		return
	_wait_timer.start(MAX_WAIT_SECONDS)


## Called on her arrival, or by the timer. Does nothing when no drawing is waiting.
func _start_drawing() -> void:
	_wait_timer.stop()
	_gallery.draw_new_drawing()
