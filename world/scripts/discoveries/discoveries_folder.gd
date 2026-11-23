class_name DiscoveriesFolder
extends RefCounted

## Finds the capybara's discoveries folder, the same one the brain writes to.
## The world only reads from it. Lookup order:
## 1. the DISCOVERIES_DIR environment variable;
## 2. the DISCOVERIES_DIR line in brain/.env (shared with the brain, so it is set only once);
## 3. discoveries/ in the project root, the brain's own default.

const VARIABLE_NAME: String = "DISCOVERIES_DIR"
const BRAIN_ENV_FILE_RELATIVE_PATH: String = "brain/.env"
const DEFAULT_FOLDER_NAME: String = "discoveries"


## Absolute path of the discoveries folder, with forward slashes.
static func path() -> String:
	var from_environment: String = OS.get_environment(VARIABLE_NAME)
	if not from_environment.is_empty():
		return _to_absolute(from_environment)
	var env_file_path: String = project_root().path_join(BRAIN_ENV_FILE_RELATIVE_PATH)
	var from_env_file: String = _read_variable_from_env_file(env_file_path)
	if not from_env_file.is_empty():
		return _to_absolute(from_env_file)
	return project_root().path_join(DEFAULT_FOLDER_NAME)


## The repository root. res:// is the world/ folder, so the root is one level up.
static func project_root() -> String:
	return ProjectSettings.globalize_path("res://..").simplify_path()


## Returns the value of VARIABLE_NAME in a KEY=value file, or "" when it is missing.
static func _read_variable_from_env_file(env_file_path: String) -> String:
	if not FileAccess.file_exists(env_file_path):
		return ""
	var env_text: String = FileAccess.get_file_as_string(env_file_path)
	for raw_line: String in env_text.split("\n"):
		var line: String = raw_line.strip_edges()
		if line.is_empty() or line.begins_with("#") or not line.contains("="):
			continue
		var key: String = line.get_slice("=", 0).strip_edges()
		if key == VARIABLE_NAME:
			var value: String = line.substr(line.find("=") + 1).strip_edges()
			return value.trim_prefix("\"").trim_suffix("\"")
	return ""


## Windows paths come with backslashes; relative paths are taken from the project root.
static func _to_absolute(folder_path: String) -> String:
	var normalized_path: String = folder_path.replace("\\", "/")
	if normalized_path.is_relative_path():
		normalized_path = project_root().path_join(normalized_path)
	return normalized_path.simplify_path()
