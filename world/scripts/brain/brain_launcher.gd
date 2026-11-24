extends Node

## Starts the brain when the world is played from the Godot editor and no brain answers,
## so pressing Play is enough. Registered as the autoload "BrainLauncher", after "Brain".
## It only runs the project's start.ps1 with -SkipWorld (Ollama, memory and brain):
## knowing how to start them stays in that script, and no AI logic lives here.
##
## Only from the editor, on Windows, with start.ps1 next to the world folder: an exported
## game never tries. One attempt per Play: if the brain stops later, it is not restarted
## in a loop. Closing the game leaves the brain running, since it lives without the world.

signal launch_started

const START_SCRIPT_RELATIVE_PATH: String = "../start.ps1"
## Set to "0" to turn the automatic start off.
const AUTOSTART_ENVIRONMENT_VARIABLE: String = "CAPYBARA_BRAIN_AUTOSTART"
## Longer than one reconnection attempt (3 s), so a brain already running connects first.
const GRACE_SECONDS: float = 4.0

var _is_connected: bool = false


func _ready() -> void:
	Brain.connection_changed.connect(_on_connection_changed)
	if not _can_autostart():
		return
	get_tree().create_timer(GRACE_SECONDS).timeout.connect(_launch_if_still_disconnected)


func _on_connection_changed(is_connected: bool) -> void:
	_is_connected = is_connected


## A custom brain address (CAPYBARA_BRAIN_URL) means the brain lives elsewhere: not ours to start.
func _can_autostart() -> bool:
	return (
		OS.has_feature("editor")
		and OS.get_name() == "Windows"
		and OS.get_environment(AUTOSTART_ENVIRONMENT_VARIABLE) != "0"
		and OS.get_environment(Brain.URL_ENVIRONMENT_VARIABLE).is_empty()
		and FileAccess.file_exists(_start_script_path())
	)


func _start_script_path() -> String:
	return ProjectSettings.globalize_path("res://").path_join(START_SCRIPT_RELATIVE_PATH).simplify_path()


## start.ps1 waits for Ollama and Docker, so it runs as a separate process and the world
## keeps going meanwhile. The brain still opens in its own window, with its logs visible.
func _launch_if_still_disconnected() -> void:
	if _is_connected:
		return
	var start_script: String = _start_script_path()
	var arguments: PackedStringArray = [
		"-NoProfile", "-ExecutionPolicy", "Bypass", "-File", start_script, "-SkipWorld"
	]
	var process_id: int = OS.create_process("powershell.exe", arguments)
	if process_id == -1:
		push_warning("Could not start the brain with %s" % start_script)
		return
	print("Starting the brain: %s -SkipWorld (process %d)" % [start_script, process_id])
	launch_started.emit()
