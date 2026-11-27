class_name ClipPacer
extends Node

## Keeps the game from running faster than real time while a clip is recorded.
##
## The Movie Maker advances the game exactly 1/FPS per frame and renders as fast as it
## can, ignoring the project's FPS limit. The brain lives in real time: when the game runs
## ahead, her lines and orders land late in the clip. Each frame, when the game clock is
## ahead of the wall clock, this waits the difference. It cannot help when the computer is
## too slow (the game then runs behind, and record_clip.ps1 warns).

var _game_seconds: float = 0.0
var _started_at_microseconds: int = 0


func _ready() -> void:
	if not ClipMode.is_on():
		set_process(false)
		return
	# Last of the frame, so the wait also covers what the other nodes did.
	process_priority = 1000


func _process(delta: float) -> void:
	if _started_at_microseconds == 0:
		_started_at_microseconds = Time.get_ticks_usec()
		return
	_game_seconds += delta
	var real_seconds: float = (Time.get_ticks_usec() - _started_at_microseconds) / 1_000_000.0
	var ahead_seconds: float = _game_seconds - real_seconds
	if ahead_seconds > 0.0:
		OS.delay_usec(int(ahead_seconds * 1_000_000.0))
