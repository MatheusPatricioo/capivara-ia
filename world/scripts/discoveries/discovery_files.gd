class_name DiscoveryFiles
extends RefCounted

## Reads what the capybara saves in the root of the discoveries folder: Markdown notes
## and PNG drawings. File names always come from listing the folder itself, so nothing
## outside it is read.

const NOTE_EXTENSION: String = "md"
const DRAWING_EXTENSION: String = "png"
## The brain saves file names as "2026-11-23-title.png"; titles leave the date out.
const DATE_PREFIX_LENGTH: int = 11


## File names with the given extension, most recently changed first.
## Empty when the folder does not exist.
static func list_newest_first(discoveries_path: String, extension: String) -> PackedStringArray:
	var file_names: Array[String] = []
	if not DirAccess.dir_exists_absolute(discoveries_path):
		return PackedStringArray(file_names)
	for file_name: String in DirAccess.get_files_at(discoveries_path):
		if file_name.get_extension().to_lower() == extension:
			file_names.append(file_name)
	file_names.sort_custom(_is_newer.bind(discoveries_path))
	return PackedStringArray(file_names)


## The note's text, or an empty string when it cannot be read.
static func read_text(discoveries_path: String, file_name: String) -> String:
	return FileAccess.get_file_as_string(discoveries_path.path_join(file_name))


## The drawing as a texture, or null when the file is missing or is not a valid image.
## Files outside res:// are not imported by Godot, so they are loaded as plain images.
static func load_drawing(discoveries_path: String, file_name: String) -> ImageTexture:
	var drawing: Image = Image.load_from_file(discoveries_path.path_join(file_name))
	if drawing == null or drawing.is_empty():
		return null
	return ImageTexture.create_from_image(drawing)


## The newest drawings that load, up to the given count, as {"title", "texture"} pairs.
static func load_newest_drawings(discoveries_path: String, count: int) -> Array[Dictionary]:
	var drawings: Array[Dictionary] = []
	for file_name: String in list_newest_first(discoveries_path, DRAWING_EXTENSION):
		if drawings.size() >= count:
			break
		var texture: ImageTexture = load_drawing(discoveries_path, file_name)
		if texture != null:
			drawings.append({"title": drawing_title(file_name), "texture": texture})
	return drawings


## "2026-11-23-gato-dormindo.png" becomes "gato dormindo".
static func drawing_title(file_name: String) -> String:
	var title: String = file_name.get_basename()
	if title.length() > DATE_PREFIX_LENGTH and title[4] == "-" and title[7] == "-":
		title = title.substr(DATE_PREFIX_LENGTH)
	return title.replace("-", " ")


## Newer files first; files changed in the same second fall back to the name, newest date prefix first.
static func _is_newer(first_name: String, second_name: String, discoveries_path: String) -> bool:
	var first_time: int = FileAccess.get_modified_time(discoveries_path.path_join(first_name))
	var second_time: int = FileAccess.get_modified_time(discoveries_path.path_join(second_name))
	if first_time != second_time:
		return first_time > second_time
	return first_name > second_name
