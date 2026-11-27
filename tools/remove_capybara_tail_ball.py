"""Removes the ball on the capybara's rear, filling the spot with her rump.

The model is one welded surface, so the ball cannot be cut off without leaving a hole.
Instead, the ball's vertices (a box around it) are rebuilt from the body around them:
- shape: seen from a point inside her body, each vertex gets a direction and a distance.
  Both are filled in from the edge of the spot (each vertex repeatedly takes the average of
  its neighbors, while the body around stays put), so the spot follows the round rump
  like a dome instead of a flat skin;
- color: the texture coordinates are filled in the same way, so the spot shows the brown
  of the rump around it instead of the ball's cracked texture.

It was run once, on the model as generated, and its result is in the repository:
    git show 6e1c2c1:world/assets/capybara/capybara.glb > original.glb
    python tools/remove_capybara_tail_ball.py original.glb world/assets/capybara/capybara.glb
"""

import json
import struct
import sys

import numpy as np

# The box around the ball, in the model's space (x is her length with the head at +x, y up).
BALL_FRONT_X = -0.385
BALL_TOP_Y = -0.08
BALL_BOTTOM_Y = -0.29
BALL_HALF_WIDTH = 0.09
# A point inside her rump, from where directions and distances are measured.
BODY_CENTER = np.array([-0.2, -0.1, 0.0])
FILL_PASSES = 400


def accessor_slice(
    gltf: dict, accessor_index: int, binary_start: int
) -> tuple[int, int, type, int]:
    accessor = gltf["accessors"][accessor_index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    dtype = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[accessor["componentType"]]
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[accessor["type"]]
    offset = binary_start + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return offset, accessor["count"] * width * np.dtype(dtype).itemsize, dtype, width


def read(data: bytearray, gltf: dict, accessor_index: int, binary_start: int) -> np.ndarray:
    offset, size, dtype, width = accessor_slice(gltf, accessor_index, binary_start)
    return np.frombuffer(bytes(data[offset : offset + size]), dtype=dtype).reshape(-1, width).copy()


def write(
    data: bytearray, gltf: dict, accessor_index: int, binary_start: int, values: np.ndarray
) -> None:
    offset, size, dtype, _ = accessor_slice(gltf, accessor_index, binary_start)
    data[offset : offset + size] = values.astype(dtype).tobytes()


def fill_from_edge(values: np.ndarray, unknown: list[int], neighbors: dict[int, list[int]]) -> None:
    """Each unknown value becomes the average of its neighbors, again and again: the known
    values around (the edge) spread smoothly into the spot."""
    for _ in range(FILL_PASSES):
        for index in unknown:
            values[index] = values[neighbors[index]].mean(axis=0)


def neighbors_of(triangles: np.ndarray) -> dict[int, list[int]]:
    found: dict[int, set[int]] = {}
    for corner_a, corner_b, corner_c in triangles:
        for one, other in ((corner_a, corner_b), (corner_b, corner_c), (corner_c, corner_a)):
            found.setdefault(int(one), set()).add(int(other))
            found.setdefault(int(other), set()).add(int(one))
    return {index: sorted(others) for index, others in found.items()}


source_path, output_path = sys.argv[1], sys.argv[2]
data = bytearray(open(source_path, "rb").read())
json_length = struct.unpack_from("<I", data, 12)[0]
gltf = json.loads(data[20 : 20 + json_length])
binary_chunk_start = 20 + json_length
binary_start = binary_chunk_start + 8

primitive = gltf["meshes"][0]["primitives"][0]
position_index = primitive["attributes"]["POSITION"]
uv_index = primitive["attributes"]["TEXCOORD_0"]
positions = read(data, gltf, position_index, binary_start)
uvs = read(data, gltf, uv_index, binary_start)
triangles = read(data, gltf, primitive["indices"], binary_start).reshape(-1, 3)

in_ball = (
    (positions[:, 0] < BALL_FRONT_X)
    & (positions[:, 1] <= BALL_TOP_Y)
    & (positions[:, 1] >= BALL_BOTTOM_Y)
    & (np.abs(positions[:, 2]) < BALL_HALF_WIDTH)
)
print(f"rebuilding {in_ball.sum()} of {len(positions)} vertices")

# Shape. Copies of a vertex made by texture seams share a spot: weld them, so the surface
# stays closed, then copy the result back to every copy.
spot_of: dict[tuple[float, ...], int] = {}
welded = np.array([spot_of.setdefault(tuple(np.round(p, 5)), i) for i, p in enumerate(positions)])
spot_neighbors = neighbors_of(welded[triangles])
spots_in_ball = sorted({int(spot) for spot in welded[in_ball]})
offsets = positions - BODY_CENTER
distances = np.linalg.norm(offsets, axis=1, keepdims=True)
directions = offsets / distances
fill_from_edge(distances, spots_in_ball, spot_neighbors)
fill_from_edge(directions, spots_in_ball, spot_neighbors)
directions /= np.linalg.norm(directions, axis=1, keepdims=True)
positions = (BODY_CENTER + directions * distances)[welded]

# Color: by real corners, not welded spots, since each copy has its own texture coordinates.
corner_neighbors = neighbors_of(triangles)
fill_from_edge(uvs, [int(index) for index in np.flatnonzero(in_ball)], corner_neighbors)

write(data, gltf, position_index, binary_start, positions)
write(data, gltf, uv_index, binary_start, uvs)
gltf["accessors"][position_index]["min"] = positions.min(axis=0).tolist()
gltf["accessors"][position_index]["max"] = positions.max(axis=0).tolist()

# The JSON chunk may change length: rebuild the file, padding the JSON with spaces to 4 bytes.
json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
json_bytes += b" " * (-len(json_bytes) % 4)
body = (
    struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes + bytes(data[binary_chunk_start:])
)
open(output_path, "wb").write(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
print("written", output_path)
