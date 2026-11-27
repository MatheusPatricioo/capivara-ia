class_name ReadableDates
extends RefCounted

## Turns the dates the brain sends ("2026-11-25T14:30", "2026-11-25") into the way people
## read them in Brazil. Anything in another shape is shown as it came.


## "2026-11-25T14:30" becomes "25/11 às 14:30".
static func day_and_time(written_at: String) -> String:
	var date_and_time: PackedStringArray = written_at.split("T")
	if date_and_time.size() != 2:
		return written_at
	var date_parts: PackedStringArray = date_and_time[0].split("-")
	if date_parts.size() != 3:
		return written_at
	return "%s/%s às %s" % [date_parts[2], date_parts[1], date_and_time[1]]


## "2026-11-25T14:30" becomes "14:30".
static func time_only(written_at: String) -> String:
	var date_and_time: PackedStringArray = written_at.split("T")
	return date_and_time[1] if date_and_time.size() == 2 else written_at


## "2026-11-25" becomes "25/11".
static func day_and_month(day: String) -> String:
	var date_parts: PackedStringArray = day.split("-")
	if date_parts.size() != 3:
		return day
	return "%s/%s" % [date_parts[2], date_parts[1]]


## "2026-11-25" becomes "25/11/2026".
static func full_day(day: String) -> String:
	var date_parts: PackedStringArray = day.split("-")
	if date_parts.size() != 3:
		return day
	return "%s/%s/%s" % [date_parts[2], date_parts[1], date_parts[0]]
