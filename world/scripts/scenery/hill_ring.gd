@tool
class_name HillRing
extends Resource

## One ring of distant hills around the world, edited in the Inspector of DistantHills.
## Farther rings should be lighter and bluer: that fading is what makes them look far.

## Distance from the world's center to the foot of the hills.
@export var inner_radius: float = 26.0
## How far the slope runs outward, from the foot to the ridge.
@export var depth: float = 8.0
## Lowest and highest points of the ridge. The game camera sits about 5 m high, so a
## ridge much taller than that hides the sunset behind it.
@export var min_height: float = 2.0
@export var max_height: float = 5.0
@export var color: Color = Color(0.25, 0.45, 0.35)
