class_name BrainQuestion
extends RefCounted

## Asks the brain something and waits for its own answer:
##     var reply: Dictionary = await BrainQuestion.ask({"type": "list_drawings"})
## The reply is the brain's message, or a "request_failed" one made here when the brain is
## offline ("offline") or takes too long ("timeout"), so the caller always gets an answer
## and only has to check reply["type"].

const FAILED_TYPE: String = "request_failed"
const TIMEOUT_SECONDS: float = 5.0

## Emitted once, with the reply or with a failure made here.
signal _settled(reply: Dictionary)

## Questions still waiting. Holding them here keeps each one alive until it is settled:
## nothing else references a question while its caller awaits.
static var _waiting: Array[BrainQuestion] = []

var _request_id: String = ""
var _is_settled: bool = false


static func ask(request: Dictionary) -> Dictionary:
	var question: BrainQuestion = BrainQuestion.new()
	_waiting.append(question)
	var reply: Dictionary = await question._ask(request)
	_waiting.erase(question)
	return reply


static func failure(reason: String) -> Dictionary:
	return {"type": FAILED_TYPE, "reason": reason}


func _ask(request: Dictionary) -> Dictionary:
	_request_id = Brain.send_request(request)
	if _request_id.is_empty():
		return failure("offline")
	Brain.reply_received.connect(_on_reply_received)
	Brain.get_tree().create_timer(TIMEOUT_SECONDS).timeout.connect(_on_timeout)
	var reply: Dictionary = await _settled
	Brain.reply_received.disconnect(_on_reply_received)
	return reply


## Every reply reaches every question: each one keeps only the reply to its own request.
func _on_reply_received(reply: Dictionary) -> void:
	if str(reply.get("request_id", "")) == _request_id:
		_settle(reply)


func _on_timeout() -> void:
	_settle(failure("timeout"))


func _settle(reply: Dictionary) -> void:
	if _is_settled:
		return
	_is_settled = true
	_settled.emit(reply)
