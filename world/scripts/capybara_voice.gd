class_name CapybaraVoice
extends AudioStreamPlayer3D

## Her voice, coming from her body: the 3D player sits on her, so the sound follows where
## she is. The audio arrives as raw PCM and is played from memory, without a file. A newer
## speech interrupts the one still playing; an older one that arrives late is dropped.

const NO_SPEECH_YET: int = 0

var _played_speech_id: int = NO_SPEECH_YET
var _creator_is_talking: bool = false


func _ready() -> void:
	Brain.voice_received.connect(_on_voice_received)
	Brain.creator_talking_changed.connect(_on_creator_talking_changed)
	Brain.voice_mode_changed.connect(_on_voice_mode_changed)
	Brain.connection_changed.connect(_on_connection_changed)


func _on_voice_received(speech_id: int, pcm: PackedByteArray, sample_rate: int) -> void:
	if speech_id <= _played_speech_id or Brain.voice_mode == Brain.VOICE_MODE_MUTE:
		return
	if _creator_is_talking:
		return
	_played_speech_id = speech_id
	stream = _wav_from(pcm, sample_rate)
	play()


## AudioStreamWAV plays raw samples: 16-bit, mono, at the rate the voice was made with.
func _wav_from(pcm: PackedByteArray, sample_rate: int) -> AudioStreamWAV:
	var wav: AudioStreamWAV = AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.stereo = false
	wav.mix_rate = sample_rate
	wav.data = pcm
	return wav


## When her creator starts talking she hushes at once, and says nothing over him.
func _on_creator_talking_changed(talking: bool) -> void:
	_creator_is_talking = talking
	if talking:
		stop()


## Muting her also silences the reply she is saying right now.
func _on_voice_mode_changed(mode: StringName) -> void:
	if mode == Brain.VOICE_MODE_MUTE:
		stop()


## A restarted brain counts its speeches from 1 again.
func _on_connection_changed(brain_is_connected: bool) -> void:
	if brain_is_connected:
		_played_speech_id = NO_SPEECH_YET
