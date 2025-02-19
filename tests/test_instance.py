import copy
import math
import os
from typing import List

import numpy as np
import pytest

from sleap import Labels
from sleap.instance import (
    Instance,
    InstancesList,
    LabeledFrame,
    Point,
    PredictedInstance,
    PredictedPoint,
)
from sleap.skeleton import Skeleton


def test_instance_node_get_set_item(skeleton):
    """
    Test basic get item and set item functionality of instances.
    """
    instance = Instance(skeleton=skeleton)
    instance["head"].x = 20
    instance["head"].y = 50

    instance["left-wing"] = Point(x=30, y=40, visible=False)

    assert instance["head"].x == 20
    assert instance["head"].y == 50

    assert instance["left-wing"] == Point(x=30, y=40, visible=False)

    thorax_point = instance["thorax"]
    assert math.isnan(thorax_point.x) and math.isnan(thorax_point.y)

    instance[0] = [-20, -50]
    assert instance["head"].x == -20
    assert instance["head"].y == -50

    instance[0] = np.array([-21, -51])
    assert instance["head"].x == -21
    assert instance["head"].y == -51


def test_instance_node_multi_get_set_item(skeleton):
    """
    Test basic get item and set item functionality of instances.
    """
    node_names = ["head", "left-wing", "right-wing"]
    points = {"head": Point(1, 4), "left-wing": Point(2, 5), "right-wing": Point(3, 6)}

    instance1 = Instance(skeleton=skeleton, points=points)

    instance1[node_names] = list(points.values())

    x_values = [p.x for p in instance1[node_names]]
    y_values = [p.y for p in instance1[node_names]]

    assert np.allclose(x_values, [1, 2, 3])
    assert np.allclose(y_values, [4, 5, 6])

    np.testing.assert_array_equal(
        instance1[np.array([0, 2, 4])], [[1, 4], [np.nan, np.nan], [3, 6]]
    )

    instance1[np.array([0, 1])] = [[1, 2], [3, 4]]
    np.testing.assert_array_equal(instance1[np.array([0, 1])], [[1, 2], [3, 4]])

    instance1[[0, 1]] = [[4, 3], [2, 1]]
    np.testing.assert_array_equal(instance1[np.array([0, 1])], [[4, 3], [2, 1]])

    instance1[["left-wing", "right-wing"]] = [[-4, -3], [-2, -1]]
    np.testing.assert_array_equal(instance1[np.array([3, 4])], [[-4, -3], [-2, -1]])
    assert instance1["left-wing"].x == -4
    assert instance1["left-wing"].y == -3
    assert instance1["right-wing"].x == -2
    assert instance1["right-wing"].y == -1


def test_non_exist_node(skeleton):
    """
    Test is instances throw key errors for nodes that don't exist in the skeleton.
    """
    instance = Instance(skeleton=skeleton)

    with pytest.raises(KeyError):
        instance["non-existent-node"].x = 1

    with pytest.raises(KeyError):
        instance = Instance(skeleton=skeleton, points={"non-exist": Point()})


def test_instance_point_iter(skeleton):
    """
    Test iteration methods over instances.
    """
    node_names = ["left-wing", "head", "right-wing"]
    points = {"head": Point(1, 4), "left-wing": Point(2, 5), "right-wing": Point(3, 6)}

    instance = Instance(skeleton=skeleton, points=points)

    assert [node.name for node in instance.nodes] == ["head", "left-wing", "right-wing"]
    assert np.allclose([p.x for p in instance.points], [1, 2, 3])
    assert np.allclose([p.y for p in instance.points], [4, 5, 6])

    # Make sure we can iterate over tuples
    for (node, point) in instance.nodes_points:
        assert points[node.name] == point


def test_skeleton_node_name_change():
    """
    Test that and instance is not broken after a node on the
    skeleton has its name changed.
    """

    s = Skeleton("Test")
    s.add_nodes(["a", "b", "c", "d", "e"])
    s.add_edge("a", "b")

    instance = Instance(s)
    instance["a"] = Point(1, 2)
    instance["b"] = Point(3, 4)

    # Rename the node
    s.relabel_nodes({"a": "A"})

    # Reference to the old node name should raise a KeyError
    with pytest.raises(KeyError):
        instance["a"].x = 2

    # Make sure the A now references the same point on the instance
    assert instance["A"] == Point(1, 2)
    assert instance["b"] == Point(3, 4)


def test_instance_comparison(skeleton):

    node_names = ["left-wing", "head", "right-wing"]
    points = {"head": Point(1, 4), "left-wing": Point(2, 5), "right-wing": Point(3, 6)}

    instance1 = Instance(skeleton=skeleton, points=points)
    instance2 = copy.deepcopy(instance1)

    assert instance1.matches(instance1)

    assert instance1 != instance2

    assert instance1.matches(instance2)

    instance2["head"].x = 42
    assert not instance1.matches(instance2)

    instance2 = copy.deepcopy(instance1)
    instance2.skeleton.add_node("extra_node")
    assert not instance1.matches(instance2)


def test_points_array(skeleton):
    """Test conversion of instances to points array"""

    node_names = ["left-wing", "head", "right-wing"]
    points = {"head": Point(1, 4), "left-wing": Point(2, 5), "right-wing": Point(3, 6)}

    instance1 = Instance(skeleton=skeleton, points=points)

    pts = instance1.get_points_array()

    assert pts.shape == (len(skeleton.nodes), 2)
    assert np.allclose(pts[skeleton.node_to_index("left-wing"), :], [2, 5])
    assert np.allclose(pts[skeleton.node_to_index("head"), :], [1, 4])
    assert np.allclose(pts[skeleton.node_to_index("right-wing"), :], [3, 6])
    assert np.isnan(pts[skeleton.node_to_index("thorax"), :]).all()

    # Now change a point, make sure it is reflected
    instance1["head"].x = 0
    instance1["thorax"] = Point(1, 2)
    pts = instance1.get_points_array()
    assert np.allclose(pts[skeleton.node_to_index("head"), :], [0, 4])
    assert np.allclose(pts[skeleton.node_to_index("thorax"), :], [1, 2])

    # Make sure that invisible points are nan iff invisible_as_nan=True
    instance1["thorax"] = Point(1, 2, visible=False)

    pts = instance1.get_points_array()
    assert not np.isnan(pts[skeleton.node_to_index("thorax"), :]).all()

    pts = instance1.points_array
    assert np.isnan(pts[skeleton.node_to_index("thorax"), :]).all()


def test_points_array_copying(skeleton):
    node_names = ["left-wing", "head", "right-wing"]
    points = {"head": Point(1, 4), "left-wing": Point(2, 5), "right-wing": Point(3, 6)}

    instance1 = Instance(skeleton=skeleton, points=points)

    first_node = skeleton.nodes[0]

    # Make sure that changing *uncopied* points array does change instance.
    pts = instance1.get_points_array(copy=False)
    assert pts[0]["x"] == instance1[first_node].x
    pts[0]["x"] = 123
    assert pts[0]["x"] == instance1[first_node].x  # these should match

    # Make sure that changing copied points array doesn't change instance.
    pts = instance1.get_points_array(copy=True)
    assert pts[0][0] == instance1[first_node].x
    pts[0][0] = 456
    assert pts[0][0] != instance1[first_node].x  # these shouldn't match

    # Make sure we can get full copy
    pts = instance1.get_points_array(copy=True, full=True)
    assert pts.shape[1] == 4  # x, y, visible, complete

    # Make sure we can get copy with just coordinates
    pts = instance1.get_points_array(copy=True, full=False)
    assert pts.shape[1] == 2  # x, y


def test_predicted_points_array_with_score(skeleton):
    pred_inst = PredictedInstance(
        skeleton=skeleton,
        points={
            skeleton.nodes[0]: PredictedPoint(1, 2, score=0.3),
            skeleton.nodes[1]: PredictedPoint(4, 5, score=0.6, visible=False),
        },
        score=1.0,
    )

    pts = pred_inst.points_and_scores_array

    # Make sure we got (x, y, score) for first point
    assert pts[0, 0] == 1
    assert pts[0, 1] == 2
    assert pts[0, 2] == 0.3

    # Make sure invisible point has NaNs
    assert np.isnan(pts[1, 0])


def test_modifying_skeleton(skeleton):
    node_names = ["left-wing", "head", "right-wing"]
    points = {"head": Point(1, 4), "left-wing": Point(2, 5), "right-wing": Point(3, 6)}

    instance1 = Instance(skeleton=skeleton, points=points)

    assert len(instance1.points) == 3

    skeleton.add_node("new test node")

    instance1.points  # this updates instance with changes from skeleton
    instance1["new test node"] = Point(7, 8)

    assert len(instance1.points) == 4

    skeleton.delete_node("head")
    assert len(instance1.points) == 3


def test_instance_labeled_frame_ref(skeleton, centered_pair_vid):
    """
    Test whether links between labeled frames and instances are kept
    """
    instances = [Instance(skeleton=skeleton) for i in range(3)]

    frame = LabeledFrame(video=centered_pair_vid, frame_idx=0, instances=instances)

    assert frame.instances[0].frame == frame
    assert frame[0].frame == frame
    assert frame[0].frame_idx == 0


def test_instance_from_pointsarray(skeleton):
    pointsarray = np.array([[1, 2], [3, 4]])
    inst = Instance.from_pointsarray(pointsarray, skeleton=skeleton)

    assert inst[skeleton.nodes[0]].x == 1
    assert inst[skeleton.nodes[0]].y == 2
    assert inst[skeleton.nodes[1]].x == 3
    assert inst[skeleton.nodes[1]].y == 4


def test_frame_merge_predicted_and_user(skeleton, centered_pair_vid):
    user_inst = Instance(
        skeleton=skeleton,
        points={skeleton.nodes[0]: Point(1, 2)},
    )
    user_frame = LabeledFrame(
        video=centered_pair_vid,
        frame_idx=0,
        instances=[user_inst],
    )

    pred_inst = PredictedInstance(
        skeleton=skeleton,
        points={skeleton.nodes[0]: PredictedPoint(1, 2, score=1.0)},
        score=1.0,
    )
    pred_frame = LabeledFrame(
        video=centered_pair_vid,
        frame_idx=0,
        instances=[pred_inst],
    )

    LabeledFrame.complex_frame_merge(user_frame, pred_frame)

    # We should be able to cleanly merge the user and the predicted instance,
    # and we want to retain both even though they perfectly match.
    assert user_inst in user_frame.instances
    assert pred_inst in user_frame.instances
    assert user_inst.frame == user_frame
    assert pred_inst.frame == user_frame
    assert len(user_frame.instances) == 2


def test_frame_merge_between_predicted_and_user(skeleton, centered_pair_vid):
    user_inst = Instance(
        skeleton=skeleton,
        points={skeleton.nodes[0]: Point(1, 2)},
    )
    user_labels = Labels(
        [
            LabeledFrame(
                video=centered_pair_vid,
                frame_idx=0,
                instances=[user_inst],
            )
        ]
    )

    pred_inst = PredictedInstance(
        skeleton=skeleton,
        points={skeleton.nodes[0]: PredictedPoint(1, 2, score=1.0)},
        score=1.0,
    )
    pred_labels = Labels(
        [
            LabeledFrame(
                video=centered_pair_vid,
                frame_idx=0,
                instances=[pred_inst],
            )
        ]
    )

    # Merge predictions into current labels dataset
    _, _, new_conflicts = Labels.complex_merge_between(
        user_labels,
        new_labels=pred_labels,
        unify=False,  # since we used match_to when loading predictions file
    )

    # new predictions should replace old ones
    Labels.finish_complex_merge(user_labels, new_conflicts)

    # We should be able to cleanly merge the user and the predicted instance,
    # and we want to retain both even though they perfectly match.
    assert user_inst in user_labels[0].instances
    assert pred_inst in user_labels[0].instances
    assert len(user_labels[0].instances) == 2


def test_instance_rotation(skeleton):

    instance = Instance(skeleton=skeleton)
    instance["head"].x = 20
    instance["head"].y = 50

    # affine transformation matrix w/ rotation and translation
    # cv2.getRotationMatrix2D((10, 10), 45, 1)
    mat = np.array(
        [[0.70710678, 0.70710678, -4.14213562], [-0.70710678, 0.70710678, 10.0]]
    )

    instance.transform_points(mat)

    assert int(instance["head"].x) == 45
    assert int(instance["head"].y) == 31


def test_merge_nodes_data(min_labels):
    labels = min_labels.copy()
    labels.skeleton.add_node("a")

    # case: base node point set and visible
    inst = labels[0][0]
    inst["A"] = Point(x=0, y=1, visible=True)
    inst["a"] = Point(x=1, y=2, visible=True)
    inst._merge_nodes_data("A", "a")
    assert inst["A"].x == 0 and inst["A"].y == 1

    # case: base node point unset
    inst = labels[0][0]
    inst["A"] = Point(x=np.nan, y=np.nan, visible=False)
    inst["a"] = Point(x=1, y=2, visible=True)
    inst._merge_nodes_data("A", "a")
    assert inst["A"].x == 1 and inst["A"].y == 2

    # case: base node point set but not visible
    inst = labels[0][1]
    inst["A"] = Point(x=0, y=1, visible=False)
    inst["a"] = Point(x=1, y=2, visible=True)
    inst._merge_nodes_data("A", "a")
    assert inst["A"].x == 1 and inst["A"].y == 2

    # case: predicted instance/point
    inst = PredictedInstance.from_numpy(
        points=np.array([[np.nan, np.nan], [1, 2], [2, 3]]),
        point_confidences=np.array([0.1, 0.8, 0.9]),
        instance_score=0.7,
        skeleton=labels.skeleton,
    )
    inst._merge_nodes_data("A", "a")
    assert inst["A"].x == 2 and inst["A"].y == 3 and inst["A"].score == 0.9


def test_instance_fill_missing():
    skeleton = Skeleton.from_names_and_edge_inds(["a", "b", "c"], [])

    for _ in range(10):
        inst = Instance.from_numpy(
            [[1, 1], [10, 10], [np.nan, np.nan]], skeleton=skeleton
        )
        inst.fill_missing()
        assert inst.points[2].x >= 0
        assert inst.points[2].y >= 0
        assert inst.points[2].x <= 10
        assert inst.points[2].y <= 10

    for _ in range(10):
        inst = Instance.from_numpy(
            [[1, 1], [10, 10], [np.nan, np.nan]], skeleton=skeleton
        )
        inst.fill_missing(max_x=7, max_y=5)
        assert inst.points[2].x >= 0
        assert inst.points[2].y >= 0
        assert inst.points[2].x <= 7
        assert inst.points[2].y <= 5


def test_labeledframe_numpy(centered_pair_predictions):
    lf = centered_pair_predictions.labeled_frames[0]
    assert lf.numpy().shape == (2, 24, 2)

    lf.instances = []
    assert lf.numpy().shape == (0, 0, 2)


def test_labeledframe_instance_counting(min_labels, centered_pair_predictions):
    lf = centered_pair_predictions.labeled_frames[0]
    assert lf.n_user_instances == 0
    assert len(lf.user_instances) == 0
    assert not lf.has_user_instances

    assert lf.n_predicted_instances == 2
    assert all([type(inst) == PredictedInstance for inst in lf.predicted_instances])
    assert lf.has_predicted_instances

    assert lf.n_tracked_instances == 2
    assert all(
        [
            type(inst) == PredictedInstance and inst.track is not None
            for inst in lf.tracked_instances
        ]
    )
    assert lf.has_tracked_instances

    lf = min_labels.labeled_frames[0]
    assert lf.n_user_instances == 2
    assert all([type(inst) == Instance for inst in lf.user_instances])
    assert lf.has_user_instances

    assert lf.n_predicted_instances == 0
    assert len(lf.predicted_instances) == 0
    assert not lf.has_predicted_instances

    assert lf.n_tracked_instances == 0
    assert len(lf.tracked_instances) == 0
    assert not lf.has_tracked_instances


def test_labeledframe_remove_untracked(
    min_tracks_2node_labels: "Labels", centered_pair_predictions: "Labels"
):
    """Test removal of untracked instances on both user-labeled and predicted frames.

    Args:
        min_tracks_2node_labels: Labels object which contains user labeled frames with
            tracked instances.
        centered_pair_predictions: Labels object which contains predicted frames with
            tracked instances.
    """
    # Load user-labeled frames.
    lf = min_tracks_2node_labels.labeled_frames[0]
    assert any([type(inst) == Instance for inst in lf.instances])

    lf.instances[0].track = None
    assert any([inst.track is None for inst in lf.instances])

    lf.remove_untracked()
    assert all([inst.track is not None for inst in lf.instances])

    # Load predicted frames.
    lf = centered_pair_predictions.labeled_frames[0]
    assert any([type(inst) == PredictedInstance for inst in lf.instances])

    lf.instances[0].track = None
    assert any([inst.track is None for inst in lf.instances])

    lf.remove_untracked()
    assert all([inst.track is not None for inst in lf.instances])


def test_instance_structuring_from_predicted(centered_pair_predictions):
    labels = centered_pair_predictions.copy()
    pred_inst = labels[0][0]
    assert type(pred_inst) == PredictedInstance

    inst = Instance.from_numpy(pred_inst.numpy(), pred_inst.skeleton)
    labels[0].instances.append(inst)

    # Force a unstructuring -> structuring and check that we can copy without setting
    # the Instance.from_predicted field
    labels_copy = labels.copy()

    # Set from_predicted
    inst.from_predicted = pred_inst
    assert inst.from_predicted == pred_inst

    # Unstructure -> structure
    labels_copy = labels.copy()


def test_instances_list(centered_pair_predictions):

    labels = centered_pair_predictions

    def test_extend(instances: InstancesList, list_of_instances: List[Instance]):
        instances.extend(list_of_instances)
        assert len(instances) == len(list_of_instances)
        for instance in instances:
            assert isinstance(instance, PredictedInstance)
            if instances.labeled_frame is None:
                assert instance.frame is None
            else:
                assert instance.frame == instances.labeled_frame

    def test_append(instances: InstancesList, instance: Instance):
        prev_len = len(instances)
        instances.append(instance)
        assert len(instances) == prev_len + 1
        assert instances[-1] == instance
        assert instance.frame == instances.labeled_frame

    def test_labeled_frame_setter(
        instances: InstancesList, labeled_frame: LabeledFrame
    ):
        instances.labeled_frame = labeled_frame
        for instance in instances:
            assert instance.frame == labeled_frame

    # Case 1: Create an empty instances list
    labeled_frame = labels.labeled_frames[0]
    list_of_instances = list(labeled_frame.instances)
    instances = InstancesList()
    assert len(instances) == 0
    assert instances._labeled_frame is None
    assert instances.labeled_frame is None

    # Extend instances list
    assert not isinstance(list_of_instances, InstancesList)
    assert isinstance(list_of_instances, list)
    test_extend(instances, list_of_instances)

    # Set the labeled frame
    test_labeled_frame_setter(instances, labeled_frame)

    # Case 2: Create an empy instances list but initialize the labeled frame
    instances = InstancesList(labeled_frame=labeled_frame)
    assert len(instances) == 0
    assert instances._labeled_frame == labeled_frame
    assert instances.labeled_frame == labeled_frame

    # Extend instances to the list from a different labeled frame
    labeled_frame = labels.labeled_frames[1]
    list_of_instances = list(labeled_frame.instances)
    test_extend(instances, list_of_instances)

    # Add instance to the list
    instance = list_of_instances[0]
    instance.frame = None
    test_append(instances, instance)

    # Set the labeled frame
    test_labeled_frame_setter(instances, labeled_frame)

    # Test InstancesList.copy
    instances_copy = instances.copy()
    assert len(instances_copy) == len(instances)
    assert not isinstance(instances_copy, InstancesList)
    assert isinstance(instances_copy, list)

    # Test InstancesList.clear
    instances_in_instances = list(instances)
    instances.clear()
    assert len(instances) == 0
    for instance in instances_in_instances:
        assert instance.frame is None

    # Case 3: Create an instances list with a list of instances
    labeled_frame = labels.labeled_frames[0]
    list_of_instances = list(labeled_frame.instances)
    instances = InstancesList(list_of_instances)
    assert len(instances) == len(list_of_instances)
    assert instances._labeled_frame is None
    assert instances.labeled_frame is None
    for instance in instances:
        assert instance.frame is None

    # Add instance to the list
    instance = list_of_instances[0]
    test_append(instances, instance)

    # Case 4: Create an instances list with a list of instances and initialize the frame
    labeled_frame_1 = labels.labeled_frames[0]
    labeled_frame_2 = labels.labeled_frames[1]
    list_of_instances = list(labeled_frame_2.instances)
    instances = InstancesList(list_of_instances, labeled_frame=labeled_frame_1)
    assert len(instances) == len(list_of_instances)
    assert instances._labeled_frame == labeled_frame
    assert instances.labeled_frame == labeled_frame
    for instance in instances:
        assert instance.frame == labeled_frame

    # Test InstancesList.__delitem__
    instance_to_remove = instances[0]
    del instances[0]
    assert instance_to_remove not in instances
    assert instance_to_remove.frame is None

    # Test InstancesList.insert
    instances.insert(0, instance_to_remove)
    assert instances[0] == instance_to_remove
    assert instance_to_remove.frame == instances.labeled_frame

    # Test InstancesList.__setitem__
    new_instance = labeled_frame_1.instances[0]
    new_instance.frame = None
    instances[0] = new_instance
    assert instances[0] == new_instance
    assert new_instance.frame == instances.labeled_frame

    # Test InstancesList.pop
    popped_instance = instances.pop(0)
    assert popped_instance.frame is None

    # Test InstancesList.remove
    instance_to_remove = instances[0]
    instances.remove(instance_to_remove)
    assert instance_to_remove.frame is None
    assert instance_to_remove not in instances

    # Case 5: Create an instances list from an instances list
    instances_1 = InstancesList(list_of_instances, labeled_frame=labeled_frame_1)
    instances = InstancesList(instances_1)
    assert len(instances) == len(instances_1)
    assert instances._labeled_frame is None
    assert instances.labeled_frame is None
    for instance in instances:
        assert instance.frame is None


def test_instances_list_with_labeled_frame(centered_pair_predictions):
    labels: Labels = centered_pair_predictions
    labels_lf_0: LabeledFrame = labels.labeled_frames[0]
    video = labels_lf_0.video
    frame_idx = labels_lf_0.frame_idx

    def test_post_init(labeled_frame: LabeledFrame):
        for instance in labeled_frame.instances:
            assert instance.frame == labeled_frame

    # Create labeled frame from list of instances
    instances = list(labels_lf_0.instances)
    for instance in instances:
        instance.frame = None  # Change frame to None to test if it is set correctly
    labeled_frame = LabeledFrame(video=video, frame_idx=frame_idx, instances=instances)
    assert isinstance(labeled_frame.instances, InstancesList)
    assert len(labeled_frame.instances) == len(instances)
    test_post_init(labeled_frame)

    # Create labeled frame from instances list
    instances = InstancesList(labels_lf_0.instances)
    labeled_frame = LabeledFrame(video=video, frame_idx=frame_idx, instances=instances)
    assert isinstance(labeled_frame.instances, InstancesList)
    assert len(labeled_frame.instances) == len(instances)
    test_post_init(labeled_frame)

    # Test LabeledFrame.__len__
    assert len(labeled_frame.instances) == len(instances)

    # Test LabeledFrame.__getitem__
    assert labeled_frame[0] == instances[0]

    # Test LabeledFrame.index
    assert labeled_frame.index(instances[0]) == instances.index(instances[0]) == 0

    # Test LabeledFrame.__delitem__
    instance_to_remove = labeled_frame[0]
    del labeled_frame[0]
    assert instance_to_remove not in labeled_frame.instances
    assert instance_to_remove.frame is None

    # Test LabeledFrame.__repr__
    print(labeled_frame)

    # Test LabeledFrame.insert
    labeled_frame.insert(0, instance_to_remove)
    assert labeled_frame[0] == instance_to_remove
    assert instance_to_remove.frame == labeled_frame

    # Test LabeledFrame.__setitem__
    new_instance = instances[1]
    new_instance.frame = None
    labeled_frame[0] = new_instance
    assert labeled_frame[0] == new_instance
    assert new_instance.frame == labeled_frame

    # Test instances.setter (empty list)
    labeled_frame.instances = []
    assert len(labeled_frame.instances) == 0
    assert labeled_frame.instances.labeled_frame == labeled_frame
    # Test instances.setter (InstancesList)
    labeled_frame.instances = labels.labeled_frames[1].instances
    assert len(labeled_frame.instances) == len(labels.labeled_frames[1].instances)
    assert labeled_frame.instances.labeled_frame == labeled_frame
    for instance in labeled_frame.instances:
        assert instance.frame == labeled_frame
    # Test instances.setter (populated list)
    labeled_frame.instances = list(labels.labeled_frames[1].instances)
    assert len(labeled_frame.instances) == len(labels.labeled_frames[1].instances)
    assert labeled_frame.instances.labeled_frame == labeled_frame
    for instance in labeled_frame.instances:
        assert instance.frame == labeled_frame
