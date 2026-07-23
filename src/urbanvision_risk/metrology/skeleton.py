from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

BinaryImage = NDArray[np.bool_]
CoordinateArray = NDArray[np.int32]
EdgeArray = NDArray[np.int32]
WeightArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class SkeletonGraph:
    coordinates_yx: CoordinateArray
    edges: EdgeArray
    edge_weights: WeightArray
    degree: NDArray[np.int32]
    component_labels: NDArray[np.int32]


def _binary_image(mask: NDArray[np.generic]) -> BinaryImage:
    array = np.asarray(mask)
    if array.ndim != 2:
        raise ValueError("A skeleton mask must be a two-dimensional array")
    return np.ascontiguousarray(array > 0)


def zhang_suen_thinning(mask: NDArray[np.generic]) -> BinaryImage:
    """Return a deterministic one-pixel skeleton using Zhang-Suen thinning."""

    image = _binary_image(mask).astype(np.uint8)
    if image.size == 0:
        return image.astype(bool)

    image[[0, -1], :] = 0
    image[:, [0, -1]] = 0
    changed = True
    while changed:
        changed = False
        for first_subiteration in (True, False):
            p2 = image[:-2, 1:-1]
            p3 = image[:-2, 2:]
            p4 = image[1:-1, 2:]
            p5 = image[2:, 2:]
            p6 = image[2:, 1:-1]
            p7 = image[2:, :-2]
            p8 = image[1:-1, :-2]
            p9 = image[:-2, :-2]
            center = image[1:-1, 1:-1]

            neighbor_count = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            transitions = (
                ((p2 == 0) & (p3 == 1)).astype(np.uint8)
                + ((p3 == 0) & (p4 == 1)).astype(np.uint8)
                + ((p4 == 0) & (p5 == 1)).astype(np.uint8)
                + ((p5 == 0) & (p6 == 1)).astype(np.uint8)
                + ((p6 == 0) & (p7 == 1)).astype(np.uint8)
                + ((p7 == 0) & (p8 == 1)).astype(np.uint8)
                + ((p8 == 0) & (p9 == 1)).astype(np.uint8)
                + ((p9 == 0) & (p2 == 1)).astype(np.uint8)
            )
            if first_subiteration:
                triplet_a = p2 * p4 * p6
                triplet_b = p4 * p6 * p8
            else:
                triplet_a = p2 * p4 * p8
                triplet_b = p2 * p6 * p8

            remove = (
                (center == 1)
                & (neighbor_count >= 2)
                & (neighbor_count <= 6)
                & (transitions == 1)
                & (triplet_a == 0)
                & (triplet_b == 0)
            )
            if np.any(remove):
                center[remove] = 0
                changed = True
    return image.astype(bool)


def build_skeleton_graph(skeleton: NDArray[np.generic]) -> SkeletonGraph:
    """Build an 8-neighbour graph without redundant diagonal corner edges."""

    binary = _binary_image(skeleton)
    height, width = binary.shape
    coordinates = np.argwhere(binary).astype(np.int32)
    node_ids = np.full((height, width), -1, dtype=np.int32)
    if coordinates.size:
        node_ids[coordinates[:, 0], coordinates[:, 1]] = np.arange(
            coordinates.shape[0], dtype=np.int32
        )

    edge_parts: list[EdgeArray] = []
    weight_parts: list[WeightArray] = []

    def add_edges(left: BinaryImage, right: BinaryImage, weight: float) -> None:
        matches = left & right
        if not np.any(matches):
            return
        left_y, left_x = np.nonzero(matches)
        if weight == 1.0:
            if left.shape == (height, width - 1):
                right_y, right_x = left_y, left_x + 1
            else:
                right_y, right_x = left_y + 1, left_x
        elif left.shape == (height - 1, width - 1):
            right_y, right_x = left_y + 1, left_x + 1
        else:
            right_y, right_x = left_y + 1, left_x
        part = np.column_stack(
            (node_ids[left_y, left_x], node_ids[right_y, right_x])
        ).astype(np.int32)
        edge_parts.append(part)
        weight_parts.append(np.full(part.shape[0], weight, dtype=np.float64))

    add_edges(binary[:, :-1], binary[:, 1:], 1.0)
    add_edges(binary[:-1, :], binary[1:, :], 1.0)

    down_right = binary[:-1, :-1] & binary[1:, 1:]
    down_right &= ~(binary[:-1, 1:] | binary[1:, :-1])
    if np.any(down_right):
        y, x = np.nonzero(down_right)
        edge_parts.append(
            np.column_stack((node_ids[y, x], node_ids[y + 1, x + 1])).astype(np.int32)
        )
        weight_parts.append(np.full(y.size, math.sqrt(2.0), dtype=np.float64))

    down_left = binary[:-1, 1:] & binary[1:, :-1]
    down_left &= ~(binary[:-1, :-1] | binary[1:, 1:])
    if np.any(down_left):
        y, x_right = np.nonzero(down_left)
        edge_parts.append(
            np.column_stack(
                (node_ids[y, x_right + 1], node_ids[y + 1, x_right])
            ).astype(np.int32)
        )
        weight_parts.append(np.full(y.size, math.sqrt(2.0), dtype=np.float64))

    if edge_parts:
        edges = np.concatenate(edge_parts, axis=0)
        weights = np.concatenate(weight_parts)
    else:
        edges = np.empty((0, 2), dtype=np.int32)
        weights = np.empty(0, dtype=np.float64)

    degree = np.zeros(coordinates.shape[0], dtype=np.int32)
    if edges.size:
        np.add.at(degree, edges[:, 0], 1)
        np.add.at(degree, edges[:, 1], 1)

    _, labels = cv2.connectedComponents(binary.astype(np.uint8), connectivity=8)
    component_labels = (
        labels[coordinates[:, 0], coordinates[:, 1]].astype(np.int32)
        if coordinates.size
        else np.empty(0, dtype=np.int32)
    )
    return SkeletonGraph(
        coordinates_yx=coordinates,
        edges=edges,
        edge_weights=weights,
        degree=degree,
        component_labels=component_labels,
    )


def _cluster_count(mask: BinaryImage) -> int:
    if not np.any(mask):
        return 0
    count, _ = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    return int(count - 1)


def _principal_orientation(coordinates_yx: CoordinateArray) -> float | None:
    if coordinates_yx.shape[0] < 2:
        return None
    xy = coordinates_yx[:, ::-1].astype(np.float64)
    centered = xy - np.mean(xy, axis=0)
    covariance = centered.T @ centered / max(1, xy.shape[0] - 1)
    values, vectors = np.linalg.eigh(covariance)
    vector = vectors[:, int(np.argmax(values))]
    angle = math.degrees(math.atan2(float(vector[1]), float(vector[0]))) % 180.0
    return round(angle, 4)


def _farthest_node(
    start: int,
    adjacency: list[list[tuple[int, float]]],
    allowed: set[int],
) -> tuple[int, float, dict[int, int]]:
    distances: dict[int, float] = {start: 0.0}
    parents: dict[int, int] = {}
    queue: list[tuple[float, int]] = [(0.0, start)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance > distances[node]:
            continue
        for neighbor, weight in adjacency[node]:
            if neighbor not in allowed:
                continue
            candidate = distance + weight
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                parents[neighbor] = node
                heapq.heappush(queue, (candidate, neighbor))
    farthest = max(distances, key=distances.__getitem__)
    return farthest, distances[farthest], parents


def _main_path_tortuosity(graph: SkeletonGraph) -> tuple[float | None, float | None]:
    if graph.coordinates_yx.shape[0] < 2 or graph.edges.size == 0:
        return None, None
    adjacency: list[list[tuple[int, float]]] = [
        [] for _ in range(graph.coordinates_yx.shape[0])
    ]
    for (left, right), weight in zip(graph.edges, graph.edge_weights, strict=True):
        adjacency[int(left)].append((int(right), float(weight)))
        adjacency[int(right)].append((int(left), float(weight)))

    best_length = 0.0
    best_tortuosity: float | None = None
    for component_id in np.unique(graph.component_labels):
        nodes_array = np.flatnonzero(graph.component_labels == component_id)
        if nodes_array.size < 2:
            continue
        allowed = {int(node) for node in nodes_array}
        start = int(nodes_array[0])
        endpoint, _, _ = _farthest_node(start, adjacency, allowed)
        other_endpoint, path_length, _ = _farthest_node(endpoint, adjacency, allowed)
        first_yx = graph.coordinates_yx[endpoint].astype(np.float64)
        second_yx = graph.coordinates_yx[other_endpoint].astype(np.float64)
        chord = float(np.linalg.norm(first_yx - second_yx))
        if path_length > best_length and chord > 0:
            best_length = path_length
            best_tortuosity = path_length / chord
    if best_length == 0:
        return None, None
    return round(best_length, 4), round(float(best_tortuosity), 4)


def box_counting_dimension(skeleton: NDArray[np.generic]) -> float | None:
    binary = _binary_image(skeleton)
    min_dimension = min(binary.shape)
    sizes: list[int] = []
    counts: list[int] = []
    size = 2
    while size <= min_dimension // 2:
        padded_height = math.ceil(binary.shape[0] / size) * size
        padded_width = math.ceil(binary.shape[1] / size) * size
        padded = np.zeros((padded_height, padded_width), dtype=bool)
        padded[: binary.shape[0], : binary.shape[1]] = binary
        boxes = padded.reshape(
            padded_height // size,
            size,
            padded_width // size,
            size,
        )
        count = int(np.count_nonzero(np.any(boxes, axis=(1, 3))))
        if count > 0:
            sizes.append(size)
            counts.append(count)
        size *= 2
    if len(counts) < 2 or len(set(counts)) < 2:
        return None
    slope = np.polyfit(
        np.log(1.0 / np.asarray(sizes, dtype=np.float64)),
        np.log(np.asarray(counts, dtype=np.float64)),
        1,
    )[0]
    return round(float(max(0.0, slope)), 4)


def summarize_skeleton(
    skeleton: NDArray[np.generic],
    graph: SkeletonGraph | None = None,
) -> dict[str, int | float | None]:
    binary = _binary_image(skeleton)
    active_graph = graph or build_skeleton_graph(binary)
    endpoint_nodes = active_graph.degree == 1
    junction_nodes = active_graph.degree >= 3
    endpoint_mask = np.zeros(binary.shape, dtype=bool)
    junction_mask = np.zeros(binary.shape, dtype=bool)
    if active_graph.coordinates_yx.size:
        endpoint_coordinates = active_graph.coordinates_yx[endpoint_nodes]
        junction_coordinates = active_graph.coordinates_yx[junction_nodes]
        endpoint_mask[endpoint_coordinates[:, 0], endpoint_coordinates[:, 1]] = True
        junction_mask[junction_coordinates[:, 0], junction_coordinates[:, 1]] = True
    path_length, tortuosity = _main_path_tortuosity(active_graph)
    component_count = (
        int(np.unique(active_graph.component_labels).size)
        if active_graph.component_labels.size
        else 0
    )
    return {
        "skeleton_pixel_count": int(np.count_nonzero(binary)),
        "graph_edge_count": int(active_graph.edges.shape[0]),
        "network_length_pixels": round(float(np.sum(active_graph.edge_weights)), 4),
        "component_count": component_count,
        "endpoint_count": int(np.count_nonzero(endpoint_nodes)),
        "endpoint_cluster_count": _cluster_count(endpoint_mask),
        "junction_pixel_count": int(np.count_nonzero(junction_nodes)),
        "junction_cluster_count": _cluster_count(junction_mask),
        "main_path_length_pixels": path_length,
        "main_path_tortuosity": tortuosity,
        "principal_orientation_degrees": _principal_orientation(
            active_graph.coordinates_yx
        ),
        "box_counting_dimension": box_counting_dimension(binary),
    }
