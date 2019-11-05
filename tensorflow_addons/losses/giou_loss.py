# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Implements GIoU loss."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf


@tf.keras.utils.register_keras_serializable(package='Addons')
class GIoULoss(tf.keras.losses.Loss):
    """Implements the GIoU loss function.

    GIoU loss was first introduced in the
    [Generalized Intersection over Union paper](https://giou.stanford.edu/GIoU.pdf).
    GIoU is a enhance for model which use IOU in object detection.

    Usage:

    ```python
    gl = tfa.losses.GIoU()
    boxes1 = tf.constant([[4.0, 3.0, 7.0, 5.0], [5.0, 6.0, 10.0, 7.0]])
    boxes2 = tf.constant([[3.0, 4.0, 6.0, 8.0], [14.0, 14.0, 15.0, 15.0]])
    loss = gl(boxes1,boxes2)
    print('Loss: ', loss.numpy())  # Loss: [1.07500000298023224, 1.9333333373069763]
    ```
    Usage with tf.keras API:

    ```python
    model = tf.keras.Model(inputs, outputs)
    model.compile('sgd', loss=tf.keras.losses.GIoULoss())
    ```

    Args:
      mode: one of ['giou', 'iou'], decided to calculate giou loss or iou loss.

    Returns:
      GIoU loss float `Tensor`.
    """

    def __init__(self,
                 mode='giou',
                 reduction=tf.keras.losses.Reduction.AUTO,
                 name='giou_loss'):
        super(GIoULoss, self).__init__(name=name, reduction=reduction)
        self.mode = mode

    def get_config(self):
        base_config = super(GIoULoss, self).get_config()
        base_config['mode'] = self.mode
        return base_config

    def call(self, y_true, y_pred):
        return giou_loss(y_true, y_pred, mode=self.mode)


@tf.keras.utils.register_keras_serializable(package='Addons')
@tf.function
def giou_loss(y_true, y_pred, mode='giou'):
    """
    Args:
        y_true: true targets tensor.
        y_pred: predictions tensor.
        mode: one of ['giou', 'iou'], decided to calculate giou loss or iou loss.

    Returns:
        GIoU loss float `Tensor`.
    """
    if mode not in ['giou', 'iou']:
        raise ValueError("Value of mode should be 'iou' or 'giou'")
    y_pred = tf.convert_to_tensor(y_pred)
    y_true = tf.cast(y_true, y_pred.dtype)
    giou = do_giou_calculate(y_pred, y_true, mode)

    # compute the final loss and return
    return 1 - giou


def do_giou_calculate(b1, b2, mode='giou'):
    """
    Args:
        b1: bounding box.
        b2: the other bounding box.
        mode: one of ['giou', 'iou'], decided to calculate giou loss or iou loss.

    Returns:
        GIoU loss float `Tensor`.
    """
    zero = tf.convert_to_tensor(0., b1.dtype)
    b1_ymin = tf.minimum(b1[:, 0], b1[:, 2])
    b1_xmin = tf.minimum(b1[:, 1], b1[:, 3])
    b1_ymax = tf.maximum(b1[:, 0], b1[:, 2])
    b1_xmax = tf.maximum(b1[:, 1], b1[:, 3])
    b2_ymin = tf.minimum(b2[:, 0], b2[:, 2])
    b2_xmin = tf.minimum(b2[:, 1], b2[:, 3])
    b2_ymax = tf.maximum(b2[:, 0], b2[:, 2])
    b2_xmax = tf.maximum(b2[:, 1], b2[:, 3])
    b1_width = tf.maximum(zero, b1_xmax - b1_xmin)
    b1_height = tf.maximum(zero, b1_ymax - b1_ymin)
    b2_width = tf.maximum(zero, b2_xmax - b2_xmin)
    b2_height = tf.maximum(zero, b2_ymax - b2_ymin)
    b1_area = b1_width * b1_height
    b2_area = b2_width * b2_height

    intersect_ymin = tf.maximum(b1_ymin, b2_ymin)
    intersect_xmin = tf.maximum(b1_xmin, b2_xmin)
    intersect_ymax = tf.minimum(b1_ymax, b2_ymax)
    intersect_xmax = tf.minimum(b1_xmax, b2_xmax)
    intersect_width = tf.maximum(zero, intersect_xmax - intersect_xmin)
    intersect_height = tf.maximum(zero, intersect_ymax - intersect_ymin)
    intersect_area = intersect_width * intersect_height

    union_area = b1_area + b2_area - intersect_area
    iou = tf.math.divide_no_nan(intersect_area, union_area)
    if mode == 'iou':
        return iou

    enclose_ymin = tf.minimum(b1_ymin, b2_ymin)
    enclose_xmin = tf.minimum(b1_xmin, b2_xmin)
    enclose_ymax = tf.maximum(b1_ymax, b2_ymax)
    enclose_xmax = tf.maximum(b1_xmax, b2_xmax)
    enclose_width = tf.maximum(zero, enclose_xmax - enclose_xmin)
    enclose_height = tf.maximum(zero, enclose_ymax - enclose_ymin)
    enclose_area = enclose_width * enclose_height
    giou = iou - tf.math.divide_no_nan(
        (enclose_area - union_area), enclose_area)
    return giou