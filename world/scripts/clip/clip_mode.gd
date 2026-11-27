class_name ClipMode
extends RefCounted

## Whether the world runs to record a clip, and which shot. record_clip.ps1 passes them as
## user arguments, after "--", which Godot hands to the game untouched:
##     godot --path world --write-movie clip.avi -- --clip --clip-shot=auto
## Without "--clip" the game is the normal one: nothing about clips is on.

const CLIP_ARGUMENT: String = "--clip"
const SHOT_ARGUMENT_PREFIX: String = "--clip-shot="
const DEFAULT_SHOT: String = "auto"
const WARMUP_ARGUMENT_PREFIX: String = "--clip-warmup="


static func is_on() -> bool:
	return CLIP_ARGUMENT in OS.get_cmdline_user_args()


## "auto", "close", "medium" or "wide", as passed; "auto" when not given.
static func requested_shot() -> String:
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with(SHOT_ARGUMENT_PREFIX):
			return argument.trim_prefix(SHOT_ARGUMENT_PREFIX).to_lower()
	return DEFAULT_SHOT


## Seconds at the start that record_clip.ps1 cuts off (the brain connecting, the sky
## arriving, the first stutters): the story starts after them. 0 when not given.
static func warmup_seconds() -> float:
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with(WARMUP_ARGUMENT_PREFIX):
			return maxf(argument.trim_prefix(WARMUP_ARGUMENT_PREFIX).to_float(), 0.0)
	return 0.0
