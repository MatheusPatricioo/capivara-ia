"""Removes the tangerine on the capybara's head, filling the spot with the top of her head.

Shape, as in tools/remove_capybara_tail_ball.py: the model is one welded surface, so the
fruit cannot be cut off without leaving a hole. Its vertices (a short cylinder around it,
above the head) are rebuilt from the head around them: seen from a point inside her head,
each vertex gets a direction and a distance, both filled in from the edge of the spot, so
it closes as a dome that continues the round top of the head.

Color: the texture is painted, not the texture coordinates moved. The fruit and the fur
are separate islands of the texture: moving coordinates between islands stretches a
triangle across whatever lies between them (stripes and red patches). So every vertex keeps
its coordinates, and the fruit's own area of the texture (the triangles of the spot, plus
the ones around it that still show peel colors) is painted with the fur around it: each
corner takes the color of the nearest fur on her head, in 3D, and each triangle blends its
three corners. One flat color for all of it showed as a patch of another tone.

The spot was found by the fruit's colors (orange and leaf green) and by height: the head
around it reaches y 0.297, the fruit rises to 0.355. It was run once, on the model after
the tail fix, and its result is in the repository:
    git show bf35ed9:world/assets/capybara/capybara.glb > before.glb
    python tools/remove_capybara_head_tangerine.py before.glb world/assets/capybara/capybara.glb
"""

import io
import json
import struct
import sys

import numpy as np
from PIL import Image

# The fruit, in the model's space (x is her length with the head at +x, y up).
FRUIT_CENTER_X = 0.268
FRUIT_CENTER_Z = -0.011
FRUIT_RADIUS = 0.095
FRUIT_BOTTOM_Y = 0.265
# A point inside her head, under the fruit, from where directions and distances are measured.
HEAD_CENTER = np.array([0.27, 0.12, -0.01])
FILL_PASSES = 400
# Around the spot, out to this distance from the fruit's axis and above this height,
# triangles with peel colors are part of the fruit too.
STAIN_RADIUS = 0.14
STAIN_BOTTOM_Y = 0.2
# The fur is looked for out to this distance from the fruit's axis.
FUR_SEARCH_RADIUS = 0.2
# Half the size, in pixels, of the window averaged to read the fur's color under a vertex:
# one pixel alone may land on a darker or lighter fleck.
FUR_SAMPLE_HALF_WINDOW = 3
# Pixels each painted triangle grows by, so no peel shows along its edges.
PAINT_MARGIN_PIXELS = 3
# How far (0 to 255, per channel distance) a vertex's color may be from the typical fur
# and still count as fur: the peel has dark red flecks that are neither orange nor green.
FUR_COLOR_TOLERANCE = 30.0


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


def colors_under(pixels: np.ndarray, uvs: np.ndarray) -> np.ndarray:
    """The texture's color (0 to 1) under each vertex's texture coordinates."""
    height, width, _ = pixels.shape
    columns = np.clip((uvs[:, 0] * width).astype(int), 0, width - 1)
    rows = np.clip((uvs[:, 1] * height).astype(int), 0, height - 1)
    return pixels[rows, columns] / 255.0


def shows_peel(colors: np.ndarray) -> np.ndarray:
    """Orange peel or leaf green; the fur is a darker, duller brown."""
    red, green, blue = colors[:, 0], colors[:, 1], colors[:, 2]
    orange = (red > 0.7) & (green > 0.35) & (green < 0.75) & (blue < 0.3) & (red - green > 0.2)
    leaf = (green > red + 0.08) & (green > blue + 0.08)
    return orange | leaf


def window_colors(pixels: np.ndarray, uvs: np.ndarray) -> np.ndarray:
    """The average color (0 to 255) of a small window of the texture under each vertex."""
    height, width, _ = pixels.shape
    colors = np.empty((len(uvs), 3), dtype=np.float32)
    for index, (u, v) in enumerate(uvs):
        column, row = int(u * width), int(v * height)
        window = pixels[
            max(row - FUR_SAMPLE_HALF_WINDOW, 0) : row + FUR_SAMPLE_HALF_WINDOW + 1,
            max(column - FUR_SAMPLE_HALF_WINDOW, 0) : column + FUR_SAMPLE_HALF_WINDOW + 1,
        ]
        colors[index] = window.reshape(-1, 3).mean(axis=0)
    return colors


def paint_blended_triangle(pixels: np.ndarray, corner_pixels: np.ndarray, corner_colors: np.ndarray) -> None:
    """Paints one triangle of the texture, blending its corners' colors (barycentric
    weights), grown by PAINT_MARGIN_PIXELS so its edges are covered too."""
    centroid = corner_pixels.mean(axis=0)
    away = corner_pixels - centroid
    lengths = np.maximum(np.linalg.norm(away, axis=1, keepdims=True), 1e-6)
    grown = corner_pixels + away / lengths * PAINT_MARGIN_PIXELS
    height, width, _ = pixels.shape
    left, top = np.floor(grown.min(axis=0)).astype(int)
    right, bottom = np.ceil(grown.max(axis=0)).astype(int)
    left, top = max(left, 0), max(top, 0)
    right, bottom = min(right, width - 1), min(bottom, height - 1)
    if right < left or bottom < top:
        return
    columns, rows = np.meshgrid(np.arange(left, right + 1), np.arange(top, bottom + 1))
    points = np.stack([columns.ravel() + 0.5, rows.ravel() + 0.5], axis=1)
    corner_a, corner_b, corner_c = grown
    edge_b, edge_c = corner_b - corner_a, corner_c - corner_a
    determinant = edge_b[0] * edge_c[1] - edge_b[1] * edge_c[0]
    if abs(determinant) < 1e-9:
        return
    offsets = points - corner_a
    weight_b = (offsets[:, 0] * edge_c[1] - offsets[:, 1] * edge_c[0]) / determinant
    weight_c = (edge_b[0] * offsets[:, 1] - edge_b[1] * offsets[:, 0]) / determinant
    weight_a = 1.0 - weight_b - weight_c
    inside = (weight_a >= 0) & (weight_b >= 0) & (weight_c >= 0)
    weights = np.stack([weight_a, weight_b, weight_c], axis=1)[inside]
    blended = weights @ corner_colors
    pixels[rows.ravel()[inside], columns.ravel()[inside]] = blended


def replace_image(data: bytearray, gltf: dict, binary_chunk_start: int, image_bytes: bytes) -> bytes:
    """The binary chunk with the texture swapped for these bytes. The views after it move
    by the change in size; every view stays aligned to 4 bytes."""
    binary_start = binary_chunk_start + 8
    binary_length = struct.unpack_from("<I", data, binary_chunk_start)[0]
    binary = bytes(data[binary_start : binary_start + binary_length])
    view = gltf["bufferViews"][gltf["images"][0]["bufferView"]]
    old_start = view["byteOffset"]
    old_padded_length = view["byteLength"] + (-view["byteLength"] % 4)
    new_padded = image_bytes + b"\x00" * (-len(image_bytes) % 4)
    shift = len(new_padded) - old_padded_length
    for other_view in gltf["bufferViews"]:
        if other_view.get("byteOffset", 0) > old_start:
            other_view["byteOffset"] += shift
    view["byteLength"] = len(image_bytes)
    gltf["buffers"][0]["byteLength"] += shift
    return binary[:old_start] + new_padded + binary[old_start + old_padded_length :]


source_path, output_path = sys.argv[1], sys.argv[2]
data = bytearray(open(source_path, "rb").read())
json_length = struct.unpack_from("<I", data, 12)[0]
gltf = json.loads(data[20 : 20 + json_length])
binary_chunk_start = 20 + json_length
binary_start = binary_chunk_start + 8

primitive = gltf["meshes"][0]["primitives"][0]
position_index = primitive["attributes"]["POSITION"]
positions = read(data, gltf, position_index, binary_start)
uvs = read(data, gltf, primitive["attributes"]["TEXCOORD_0"], binary_start)
triangles = read(data, gltf, primitive["indices"], binary_start).reshape(-1, 3)

distance_from_fruit_axis = np.hypot(
    positions[:, 0] - FRUIT_CENTER_X, positions[:, 2] - FRUIT_CENTER_Z
)
in_fruit = (distance_from_fruit_axis < FRUIT_RADIUS) & (positions[:, 1] > FRUIT_BOTTOM_Y)
print(f"rebuilding {in_fruit.sum()} of {len(positions)} vertices")

# Color, read before the shape changes: which triangles are the fruit, and the fur's color.
image_view = gltf["bufferViews"][gltf["images"][0]["bufferView"]]
image_start = binary_start + image_view["byteOffset"]
texture = Image.open(io.BytesIO(bytes(data[image_start : image_start + image_view["byteLength"]])))
texture = texture.convert("RGB")
pixels = np.asarray(texture).astype(np.float32)
vertex_colors = colors_under(pixels, uvs)
peel = shows_peel(vertex_colors)
above_stain_bottom = positions[:, 1] > STAIN_BOTTOM_Y
fruit_vertex = in_fruit | (peel & (distance_from_fruit_axis < STAIN_RADIUS) & above_stain_bottom)
fruit_triangles = triangles[fruit_vertex[triangles].any(axis=1)]
fruit_corners = np.unique(fruit_triangles)
might_be_fur = ~fruit_vertex & ~peel & (distance_from_fruit_axis < FUR_SEARCH_RADIUS) & above_stain_bottom
candidate_indices = np.flatnonzero(might_be_fur)
candidate_colors = window_colors(pixels, uvs[candidate_indices])
typical_fur = np.median(candidate_colors, axis=0)
looks_like_fur = np.linalg.norm(candidate_colors - typical_fur, axis=1) < FUR_COLOR_TOLERANCE
fur_indices = candidate_indices[looks_like_fur]
fur_colors = candidate_colors[looks_like_fur]
print(f"typical fur {typical_fur.round()}, {looks_like_fur.sum()} of {len(candidate_indices)} candidates")

# Shape. Copies of a vertex made by texture seams share a spot: weld them, so the surface
# stays closed, then copy the result back to every copy.
spot_of: dict[tuple[float, ...], int] = {}
welded = np.array([spot_of.setdefault(tuple(np.round(p, 5)), i) for i, p in enumerate(positions)])
spot_neighbors = neighbors_of(welded[triangles])
spots_in_fruit = sorted({int(spot) for spot in welded[in_fruit]})
offsets = positions - HEAD_CENTER
distances = np.linalg.norm(offsets, axis=1, keepdims=True)
directions = offsets / distances
fill_from_edge(distances, spots_in_fruit, spot_neighbors)
fill_from_edge(directions, spots_in_fruit, spot_neighbors)
directions /= np.linalg.norm(directions, axis=1, keepdims=True)
positions = (HEAD_CENTER + directions * distances)[welded]
write(data, gltf, position_index, binary_start, positions)
gltf["accessors"][position_index]["min"] = positions.min(axis=0).tolist()
gltf["accessors"][position_index]["max"] = positions.max(axis=0).tolist()

# Color, now that the dome is in place: each corner of the fruit's triangles takes the
# color of the nearest fur on her head, and each triangle blends its three corners.
corner_color: dict[int, np.ndarray] = {}
for corner in fruit_corners:
    nearest = np.argmin(np.linalg.norm(positions[fur_indices] - positions[corner], axis=1))
    corner_color[int(corner)] = fur_colors[nearest]
print(f"painting {len(fruit_triangles)} triangles from {len(fur_indices)} vertices of fur")
texture_size = np.array([texture.width, texture.height], dtype=np.float32)
for corners in fruit_triangles:
    paint_blended_triangle(
        pixels,
        uvs[corners] * texture_size,
        np.array([corner_color[int(corner)] for corner in corners]),
    )
painted = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))

png = io.BytesIO()
painted.save(png, format="PNG", optimize=True)
binary = replace_image(data, gltf, binary_chunk_start, png.getvalue())

# The JSON chunk may change length: rebuild the file, padding the JSON with spaces to 4 bytes.
json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
json_bytes += b" " * (-len(json_bytes) % 4)
body = (
    struct.pack("<II", len(json_bytes), 0x4E4F534A)
    + json_bytes
    + struct.pack("<II", len(binary), 0x004E4942)
    + binary
)
open(output_path, "wb").write(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
print("written", output_path)
