class_name ClipRecorder
extends Node

## Decides when the story of a clip starts and ends. The Movie Maker records from the first
## frame, but the clip only counts from the moment the brain is ready: the world connected
## and her real sky arrived (the brain sends it on connection). From then it lets the game
## run for the clip's seconds, writes that moment to a small marker file next to the
## video and closes the game. record_clip.ps1 reads the marker and cuts the video there.
##
## If the brain is not ready in time, it writes the failure to the marker and closes the
## game, so no clip is made of a capybara without her brain.

## Emitted once, at the frame the story starts.
signal story_started

## After connecting, how long to wait for the sky before starting anyway (a brain with
## the sky turned off never sends it).
const SKY_WAIT_SECONDS: float = 5.0
## The story never starts before this, even with a brain that answers at once: the first
## frames still stutter while the scene settles.
const SETTLE_SECONDS: float = 1.0
## Extra seconds recorded after the clip, so the cut never lands past the last frame.
const TAIL_SECONDS: float = 0.5
const EXIT_BRAIN_NOT_READY: int = 3

var _game_seconds: float = 0.0
var _connected_at: float = -1.0
var _has_sky: bool = false
var _story_started_at: float = -1.0


func _ready() -> void:
	if not ClipMode.is_on():
		set_process(false)
		return
	Brain.connection_changed.connect(_on_connection_changed)
	Brain.sky_changed.connect(_on_sky_changed)


func _process(delta: float) -> void:
	_game_seconds += delta
	if _story_started_at < 0.0:
		_start_story_when_ready()
		return
	if _game_seconds >= _story_started_at + ClipMode.story_seconds() + TAIL_SECONDS:
		_finish({"story_start_seconds": snappedf(_story_started_at, 0.001)}, 0)


func _start_story_when_ready() -> void:
	var is_connected: bool = _connected_at >= 0.0
	if _game_seconds < SETTLE_SECONDS:
		return
	if is_connected and (_has_sky or _game_seconds - _connected_at >= SKY_WAIT_SECONDS):
		_story_started_at = _game_seconds
		print("Clip story starts at %.3f s of game time" % _story_started_at)
		story_started.emit()
	elif _game_seconds >= ClipMode.brain_wait_seconds():
		var waited_seconds: int = int(ClipMode.brain_wait_seconds())
		_finish({"error": "the brain was not ready after %d s" % waited_seconds}, EXIT_BRAIN_NOT_READY)


func _on_connection_changed(is_connected: bool) -> void:
	if is_connected and _connected_at < 0.0:
		_connected_at = _game_seconds


func _on_sky_changed(_day_fraction: float, _day_length_seconds: float, _weather: StringName) -> void:
	_has_sky = true


func _finish(marker: Dictionary, exit_code: int) -> void:
	set_process(false)
	var marker_path: String = ClipMode.marker_path()
	if not marker_path.is_empty():
		var marker_file: FileAccess = FileAccess.open(marker_path, FileAccess.WRITE)
		if marker_file == null:
			push_error("Could not write the clip marker at %s" % marker_path)
		else:
			marker_file.store_string(JSON.stringify(marker))
			marker_file.close()
	get_tree().quit(exit_code)
