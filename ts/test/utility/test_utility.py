import pytest
import numpy as np
from ts.utility import Utility


@pytest.mark.parametrize('data, seqLength', [
    (np.linspace(0, 100, 5000), 500),
    (np.linspace(0, 1000, 4350), 1500),
    (np.linspace(0, 100, 1000), 1),
    (np.linspace(0, 1000, 10000), 111),
    (np.random.uniform(0, 100, size=(10000, 20)), 111),
    (np.random.uniform(0, 100, size=(450, 5)), 1)
], ids=['1dim-0', '1dim-1', '1dim-2', '1dim-3', '2dim-0', '2dim-1'])
def test_breakSeq(data: np.ndarray, seqLength: int):
    dataSeq = Utility.breakSeq(data, seqLength)

    # On concatenating the dataSeq, we should get back data
    assert np.array_equal(np.concatenate(dataSeq, axis=0), data)

    # length of each seq except the last should be exactly seqLength
    for seq in dataSeq[:-1]:
        assert seq.shape[0] == seqLength


@pytest.mark.parametrize(
    'targetSeries, exogenousSeries, seqLength, forecastHorizon', [
        (np.linspace(0, 100, 5000), None, 300, None),
        (np.random.uniform(0, 1000, size=(500, 20)), None, 1000, None),
        (np.random.uniform(0, 100, size=(10000, 20)), None, 111, None),
        (
            np.random.uniform(0, 100, size=(10000, 7)),
            np.random.uniform(0, 100, size=(10000, 4)),
            350, 1
        ),
        (
            np.random.uniform(0, 1000, size=(5000,)),
            np.random.uniform(0, 400, size=(5000, 10)),
            735, 15
        ),
        (
            np.random.uniform(0, 200, size=(1000, 8)),
            np.random.uniform(0, 200, size=(1000, 4)),
            1500, 11
        )
    ], ids=['nonexo-0', 'nonexo-1', 'nonexo-2', 'exo-0', 'exo-1', 'exo-2'])
def test_breakTrainSeq(
        targetSeries,
        exogenousSeries,
        seqLength,
        forecastHorizon
):
    n = targetSeries.shape[0]

    trainSequences = Utility.breakTrainSeq(
        targetSeries, exogenousSeries, seqLength, forecastHorizon
    )

    # If exogenousSeries is none, breakTrainSeq behaves differently,
    # here we test that behaviour
    if exogenousSeries is None:
        # On concatenating the trainSequences, we should get back data
        assert np.array_equal(np.concatenate(trainSequences, axis=0), targetSeries)

        # length of each seq except the last should be exactly seqLength
        for seq in trainSequences[:-1]:
            assert seq.shape[0] == seqLength

        return

    # Forecast horizon cannot be None
    assert forecastHorizon is not None

    # Target and Exogenous series must have same number of elements
    assert targetSeries.shape[0] == exogenousSeries.shape[0]

    # Check if the train sequences are correct
    startIdx = 0
    for (targetSeriesSeq, exogenousSeriesSeq) in trainSequences:
        lenTargetSeries = targetSeriesSeq.shape[0]
        lenExogenousSeries = exogenousSeriesSeq.shape[0]

        assert lenTargetSeries == lenExogenousSeries + forecastHorizon

        exoEndIdx = startIdx + lenExogenousSeries
        targetEndIdx = exoEndIdx + forecastHorizon

        # Check if the broken sequence matches the correct part of the
        # original sequence
        assert np.array_equal(
            targetSeriesSeq, targetSeries[startIdx:targetEndIdx]
        )
        assert np.array_equal(
            exogenousSeriesSeq,
            exogenousSeries[startIdx:exoEndIdx]
        )

        startIdx = exoEndIdx

    assert (startIdx + forecastHorizon == n) or (n - startIdx <= forecastHorizon)


@pytest.mark.parametrize(
    'data, train, val', [
        (np.random.uniform(0, 1000, size=(5000,)), 3500, None),
        (np.random.uniform(0, 1000, size=(5000, 10)), 4900, None),
        (np.random.uniform(0, 1000, size=(100, 4)), 1, None),
        (np.random.uniform(0, 1000, size=(5000, 4)), 0.9, None),
        (np.random.uniform(0, 1000, size=(2550, 4)), 0.7, None),
        (np.random.uniform(0, 1000, size=(3000, 4)), 0.1, None),

        (np.random.uniform(0, 1000, size=(5000,)), 3500, 500),
        (np.random.uniform(0, 1000, size=(5000, 10)), 4900, 95),
        (np.random.uniform(0, 1000, size=(100, 4)), 1, 1),
        (np.random.uniform(0, 1000, size=(100, 4)), 1, 0.4),
        (np.random.uniform(0, 1000, size=(5000, 4)), 0.9, 0.05),
        (np.random.uniform(0, 1000, size=(2550, 4)), 0.7, 0.1),
        (np.random.uniform(0, 1000, size=(2550, 4)), 0.7, 0.0),
    ], ids=[
        'no_val-0', 'no_val-1', 'no_val-2', 'no_val-3', 'no_val-4', 'no_val-5',
        'val-0', 'val-1', 'val-2', 'val-3', 'val-4', 'val-5', 'val-6'
    ])
def test_trainTestSplit(data, train, val):

    if train < 1.0:
        train = round(data.shape[0] * train)

    # If validation set is not required
    if val is None:
        dataTrain, dataTest = Utility.trainTestSplit(data, train, None)

        # train and test data together should give entire data
        assert np.array_equal(np.concatenate((dataTrain, dataTest), axis=0), data)

        # Train data must have the required number of elements
        assert dataTrain.shape[0] == train

        return

    dataTrain, dataVal, dataTest = Utility.trainTestSplit(data, train, val)

    # train, val and test data together should give entire data
    assert np.array_equal(
        np.concatenate((dataTrain, dataVal, dataTest), axis=0), data
    )

    if val < 1.0:
        val = round(data.shape[0] * val)

    # Train and Val data must have the required number of elements
    assert dataTrain.shape[0] == train
    assert dataVal.shape[0] == val


@pytest.mark.parametrize('targetSeries, exogenousSeries, train, val', [
    (
        np.random.uniform(0, 1000, size=(5000,)),
        np.random.uniform(0, 1000, size=(5000, 1)),
        4500, None
    ),
    (
        np.random.uniform(0, 2000, size=(5000, 10)),
        np.random.uniform(0, 2000, size=(5000, 5)),
        4999, None
    ),
    (
        np.random.uniform(0, 2000, size=(100, 7)),
        np.random.uniform(0, 2000, size=(100, 3)),
        1, 1
    ),
    (
        np.random.uniform(0, 2000, size=(100, 3)),
        np.random.uniform(0, 2000, size=(100, 7)),
        98, 1
    ),
    (
        np.random.uniform(0, 2000, size=(1000, 4)),
        np.random.uniform(0, 2000, size=(1000, 6)),
        0.7, 0.2
    ),
    (
        np.random.uniform(0, 2000, size=(1000, 5)),
        np.random.uniform(0, 2000, size=(1000, 5)),
        0.5, 0.1
    ),
])
def test_trainTestSplitSeries(targetSeries, exogenousSeries, train, val):

    assert targetSeries.shape[0] == exogenousSeries.shape[0]
    n = targetSeries.shape[0]

    if train < 1.0:
        train = round(n * train)

    # If validation set is not required
    if val is None:
        (targetTrain, exoTrain), (targetTest, exoTest) = \
            Utility.trainTestSplitSeries(targetSeries, exogenousSeries, train, None)

        # train and test data together should give entire data
        assert np.array_equal(
            np.concatenate((targetTrain, targetTest), axis=0), targetSeries
        )
        assert np.array_equal(
            np.concatenate((exoTrain, exoTest), axis=0), exogenousSeries
        )

        assert targetTrain.shape[0] == exoTrain.shape[0] == train

        return

    if val < 1.0:
        val = round(n * val)

    (targetTrain, exoTrain), (targetVal, exoVal), (targetTest, exoTest) = \
        Utility.trainTestSplitSeries(targetSeries, exogenousSeries, train, val)

    # train, val and test data together should give entire data
    assert np.array_equal(
        np.concatenate((targetTrain, targetVal, targetTest), axis=0), targetSeries
    )
    assert np.array_equal(
        np.concatenate((exoTrain, exoVal, exoTest), axis=0), exogenousSeries
    )

    assert targetTrain.shape[0] == exoTrain.shape[0] == train
    assert targetVal.shape[0] == exoVal.shape[0] == val


def test_prepareDataPred():
    pass


def test_prepareDataTrain():
    pass


def test_isExoShapeValid():
    pass


def test_generateMultipleSequence():
    pass
