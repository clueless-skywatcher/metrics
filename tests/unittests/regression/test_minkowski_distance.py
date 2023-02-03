from collections import namedtuple
from functools import partial

import pytest
import torch
from scipy.spatial.distance import minkowski as scipy_minkowski

from torchmetrics.functional import minkowski_distance
from torchmetrics.regression import MinkowskiDistance
from torchmetrics.utilities.exceptions import TorchMetricsUserError
from torchmetrics.utilities.imports import _TORCH_GREATER_EQUAL_1_9
from unittests.helpers import seed_all
from unittests.helpers.testers import BATCH_SIZE, NUM_BATCHES, MetricTester

seed_all(42)

num_targets = 5

Input = namedtuple("Input", ["preds", "target"])

_single_target_inputs = Input(
    preds=torch.rand(NUM_BATCHES, BATCH_SIZE),
    target=torch.rand(NUM_BATCHES, BATCH_SIZE),
)

_multi_target_inputs = Input(
    preds=torch.rand(NUM_BATCHES, BATCH_SIZE, num_targets),
    target=torch.rand(NUM_BATCHES, BATCH_SIZE, num_targets),
)


def _single_target_sk_metric(preds, target, p):
    sk_preds = preds.view(-1).numpy()
    sk_target = target.view(-1).numpy()
    res = scipy_minkowski(sk_preds, sk_target, p=p)
    return res


def _multi_target_sk_metric(preds, target, p):
    sk_preds = preds.view(-1).numpy()
    sk_target = target.view(-1).numpy()
    res = scipy_minkowski(sk_preds, sk_target, p=p)
    return res


@pytest.mark.parametrize(
    "preds, target, sk_metric",
    [
        (_single_target_inputs.preds, _single_target_inputs.target, _single_target_sk_metric),
        (_multi_target_inputs.preds, _multi_target_inputs.target, _multi_target_sk_metric),
    ],
)
@pytest.mark.parametrize("p", [1, 2, 4, 1.5])
class TestMinkowskiDistance(MetricTester):
    @pytest.mark.parametrize("ddp", [True, False])
    @pytest.mark.parametrize("dist_sync_on_step", [True, False])
    def test_minkowski_distance_class(self, preds, target, sk_metric, p, ddp, dist_sync_on_step):
        self.run_class_metric_test(
            ddp=ddp,
            preds=preds,
            target=target,
            metric_class=MinkowskiDistance,
            reference_metric=partial(sk_metric, p=p),
            dist_sync_on_step=dist_sync_on_step,
            metric_args={"p": p},
        )

    def test_minkowski_distance_functional(self, preds, target, sk_metric, p):
        self.run_functional_metric_test(
            preds=preds,
            target=target,
            metric_functional=minkowski_distance,
            reference_metric=partial(sk_metric, p=p),
            metric_args={"p": p},
        )

    @pytest.mark.skipif(
        not _TORCH_GREATER_EQUAL_1_9, reason="minkowski half + cpu not supported for older versions of pytorch"
    )
    def test_minkowski_distance_half_cpu(self, preds, target, sk_metric, p):
        self.run_precision_test_cpu(preds, target, MinkowskiDistance, minkowski_distance, metric_args={"p": p})

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="test requires cuda")
    def test_minkowski_distance_half_gpu(self, preds, target, sk_metric, p):
        self.run_precision_test_gpu(preds, target, MinkowskiDistance, minkowski_distance, metric_args={"p": p})


def test_error_on_different_shape():
    metric = MinkowskiDistance(5.1)
    with pytest.raises(RuntimeError, match="Predictions and targets are expected to have the same shape"):
        metric(torch.randn(50), torch.randn(100))


def test_error_on_wrong_p_arg():
    with pytest.raises(TorchMetricsUserError, match="Argument ``p`` must be a float.*"):
        MinkowskiDistance(p=-10)
