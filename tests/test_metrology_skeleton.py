import math

import cv2
import numpy as np

from urbanvision_risk.metrology.engine import measure_crack_mask
from urbanvision_risk.metrology.skeleton import (
    build_skeleton_graph,
    summarize_skeleton,
    zhang_suen_thinning,
)


def _skeletonize(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask > 0, 1)
    return zhang_suen_thinning(padded)[1:-1, 1:-1]


def test_thinning_reduces_a_thick_line_to_a_connected_centerline() -> None:
    mask = np.zeros((100, 150), dtype=np.uint8)
    cv2.line(mask, (20, 50), (125, 50), 255, 11)

    skeleton = _skeletonize(mask)
    summary = summarize_skeleton(skeleton)

    assert np.count_nonzero(skeleton) < np.count_nonzero(mask) / 5
    assert summary["component_count"] == 1
    assert summary["endpoint_count"] == 2
    assert summary["junction_cluster_count"] == 0
    assert 95 < float(summary["network_length_pixels"]) < 115
    assert float(summary["principal_orientation_degrees"]) < 1


def test_graph_detects_branch_topology_without_counting_a_junction_blob_as_many_nodes() -> None:
    mask = np.zeros((121, 121), dtype=np.uint8)
    cv2.line(mask, (60, 15), (60, 105), 255, 7)
    cv2.line(mask, (15, 60), (105, 60), 255, 7)

    skeleton = _skeletonize(mask)
    graph = build_skeleton_graph(skeleton)
    summary = summarize_skeleton(skeleton, graph)

    assert summary["component_count"] == 1
    assert summary["endpoint_count"] == 4
    assert summary["junction_cluster_count"] == 1
    assert summary["graph_edge_count"] >= summary["skeleton_pixel_count"] - 1
    assert float(summary["box_counting_dimension"]) >= 0.8


def test_diagonal_graph_uses_euclidean_edge_weights() -> None:
    skeleton = np.zeros((50, 50), dtype=np.uint8)
    for coordinate in range(5, 45):
        skeleton[coordinate, coordinate] = 1

    graph = build_skeleton_graph(skeleton)

    assert graph.edges.shape[0] == 39
    assert math.isclose(
        float(np.sum(graph.edge_weights)),
        39 * math.sqrt(2),
        rel_tol=1e-9,
    )


def test_pixel_only_measurement_refuses_to_claim_physical_units() -> None:
    mask = np.zeros((100, 150), dtype=np.uint8)
    cv2.line(mask, (20, 50), (125, 50), 255, 11)

    result = measure_crack_mask(mask)

    assert result["measurement_space"] == "pixel_only"
    assert result["physical_geometry"] is None
    assert result["decision_boundary"]["physical_measurement_valid"] is False
    assert 8 < result["pixel_geometry"]["width_distribution"]["mean"] < 15
