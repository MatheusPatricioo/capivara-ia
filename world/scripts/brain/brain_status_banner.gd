extends CanvasLayer

## A small warning over the world while the brain (the Python service) is offline.
## Without the brain the capybara only wanders: nobody decides to research, save or draw,
## and nothing on screen said why. Registered as the autoload "BrainStatus", after "Brain"
## and "BrainLauncher". It only shows the connection state: no AI logic lives here.

const OFFLINE_TEXT: String = (
	"Cérebro desconectado: a capivara só passeia.\n"
	+ "Ligue com .\\start.ps1 ou python -m src.live_capybara"
)
const STARTING_TEXT: String = (
	"Ligando o cérebro (Ollama, memória e cérebro)...\n"
	+ "Na primeira vez pode levar um minuto."
)
## Above the 3D world, below the chalkboard and computer screens (layer 10).
const DRAW_LAYER: int = 5
const SCREEN_MARGIN: Vector2 = Vector2(12, 12)
const PADDING: int = 10
const CORNER_RADIUS: int = 6
const BACKGROUND_COLOR: Color = Color(0.08, 0.08, 0.08, 0.75)
const TEXT_COLOR: Color = Color(1.0, 0.86, 0.45)

var _panel: PanelContainer
var _label: Label


## The brain starts disconnected and only signals changes, so the warning starts visible.
func _ready() -> void:
	layer = DRAW_LAYER
	_panel = _create_panel()
	add_child(_panel)
	Brain.connection_changed.connect(_on_connection_changed)
	BrainLauncher.launch_started.connect(_on_launch_started)


func _on_connection_changed(is_connected: bool) -> void:
	_panel.visible = not is_connected
	if not is_connected:
		_show_text(OFFLINE_TEXT)


func _on_launch_started() -> void:
	_show_text(STARTING_TEXT)


## reset_size shrinks the panel back to the text, which may be shorter than the last one.
func _show_text(text: String) -> void:
	_label.text = text
	_panel.reset_size()


func _create_panel() -> PanelContainer:
	var panel: PanelContainer = PanelContainer.new()
	panel.position = SCREEN_MARGIN
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_theme_stylebox_override("panel", _create_background())
	_label = Label.new()
	_label.text = OFFLINE_TEXT
	_label.add_theme_color_override("font_color", TEXT_COLOR)
	panel.add_child(_label)
	return panel


func _create_background() -> StyleBoxFlat:
	var background: StyleBoxFlat = StyleBoxFlat.new()
	background.bg_color = BACKGROUND_COLOR
	background.set_corner_radius_all(CORNER_RADIUS)
	background.set_content_margin_all(PADDING)
	return background
