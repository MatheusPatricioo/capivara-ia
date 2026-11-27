class_name ClipMode
extends RefCounted

## Whether the world runs to record a clip, and which shot. record_clip.ps1 passes them as
## user arguments, after "--", which Godot hands to the game untouched:
##     godot --path world --write-movie clip.avi -- --clip --clip-shot=auto --clip-seconds=20
##         --clip-marker=D:/clipes/clip.json --clip-brain-wait=60
## Without "--clip" the game is the normal one: nothing about clips is on.

const CLIP_ARGUMENT: String = "--clip"
const SHOT_ARGUMENT_PREFIX: String = "--clip-shot="
const DEFAULT_SHOT: String = "auto"
const SECONDS_ARGUMENT_PREFIX: String = "--clip-seconds="
const MARKER_ARGUMENT_PREFIX: String = "--clip-marker="
const BRAIN_WAIT_ARGUMENT_PREFIX: String = "--clip-brain-wait="
const DEFAULT_STORY_SECONDS: float = 20.0
const DEFAULT_BRAIN_WAIT_SECONDS: float = 60.0


static func is_on() -> bool:
	return CLIP_ARGUMENT in OS.get_cmdline_user_args()


## "auto" or the name of one shot (see ClipShot.named), as passed; "auto" when not given.
static func requested_shot() -> String:
	var shot: String = _text_argument(SHOT_ARGUMENT_PREFIX).to_lower()
	return shot if not shot.is_empty() else DEFAULT_SHOT


## Seconds of story to record, counted from the moment the brain is ready.
static func story_seconds() -> float:
	return _number_argument(SECONDS_ARGUMENT_PREFIX, DEFAULT_STORY_SECONDS)


## The longest wait for the brain, in seconds, before the recording gives up.
static func brain_wait_seconds() -> float:
	return _number_argument(BRAIN_WAIT_ARGUMENT_PREFIX, DEFAULT_BRAIN_WAIT_SECONDS)


## Where to write when the story started (or why it could not); "" for nowhere.
static func marker_path() -> String:
	return _text_argument(MARKER_ARGUMENT_PREFIX)


static func _number_argument(prefix: String, default_value: float) -> float:
	var text_value: String = _text_argument(prefix)
	if not text_value.is_valid_float():
		return default_value
	return maxf(text_value.to_float(), 0.0)


static func _text_argument(prefix: String) -> String:
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return ""
