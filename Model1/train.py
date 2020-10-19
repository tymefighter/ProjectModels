import tensorflow as tf
import numpy as np

from predict import computeAttentionWeights
from loss import loss1, loss2
from saveLoad import saveModel

def runGruOnWindow(
    self,
    X,
    windowStartTime,
):
    state = self.gru.get_initial_state()
    for t in range(
        windowStartTime, 
        windowStartTime + self.windowSize
    ):
        state, _ = self.gru(
            np.expand_dims(X[t], 0), 
            state
        )

    return state

def buildMemory(
    self,
    X, 
    Y, 
    currentTime
):
    if currentTime < self.windowSize:
        raise Exception("Cannot Construct Memory")

    sampleLow = 0
    sampleHigh = currentTime - self.windowSize

    self.S = [None] * self.memorySize
    self.q = [None] * self.memorySize

    for i in range(self.memorySize):
        windowStartTime = np.random.randint(
            sampleLow,
            sampleHigh + 1
        )

        self.S[i] = self.runGruOnWindow(X, windowStartTime)
        if Y[windowStartTime + self.memorySize] > self.epsilon:
            self.q[i] = 1
        else:
            self.q[i] = 0

    self.S = np.array(self.S)
    self.q = np.array(self.q)

def trainOneTimestep(
    self,
    gruState,
    X,
    Y,
    currentTime,
    outerGradientTape,
    numNormalEvents,
    numExtremeEvents
):
    with outerGradientTape.stop_recording():

        with tf.GradientTape() as innerGradientTape:
            self.buildMemory(X, Y, currentTime)
            pred = self.memOut(self.S)
            loss = loss2(
                pred, 
                self.q
                numNormalEvents,
                numExtremeEvents
            )

        trainableVars = self.gru.trainable_variables \
            + self.memOut.trainable_variables

        grads = innerGradientTape.gradient(loss, trainableVars)
        self.optimizer.apply_gradients(zip(
            grads,
            trainableVars
        ))

    nextState, _ = self.gru(X[currentTime], gruState)
    semiPred = self.out(np.expand_dims(nextState, 0))

    attentionWeights = self.computeAttentionWeights(nextState)
    extremePred = tf.math.reduce_sum(
        attentionWeights * self.q, 
        axis = 0
    )

    if Y[i] > self.epsilon:
        extremeTarget = 1
        numExtremeEvents += 1
    else:
        extremeTarget = 0
        numNormalEvents += 1

    yPred = semiPred + self.b * extremePred
    return loss1(
        yPred, 
        Y[currentTime], 
        extremePred, 
        extremeTarget,
        self.extremeLossWeight,
        numNormalEvents,
        numExtremeEvents
    ), nextState, numNormalEvents, numExtremeEvents

def trainOneSeq(
    self,
    X, 
    Y, 
    seqStartTime, 
    seqEndTime
):

    with t.GradientTape() as tape:
        numNormalEvents = numExtremeEvents = 0

        state = self.gru.get_initial_state()
        loss = 0
        for t in range(seqStartTime, seqEndTime + 1):
            currLoss, state, numNormalEvents, numExtremeEvents = \
                self.trainOneTimestep(state)
            loss += currLoss
    
    trainableVars = self.gru.trainable_variables \
        + self.out.trainable_variables \
        + [self.b]

    grads = tape.gradient(loss, trainableVars)
    self.optimizer.apply_gradients(zip(
        grads,
        trainableVars
    ))

def trainModel(
    self, 
    X, 
    Y,
    seqLength,
    currTimestep,
    modelFilepath
):
    seqStartTime = self.windowSize
    if currTimestep is not None:
        seqStartTime = max(seqStartTime, currTimestep)

    n = X.shape[0]
    while seqStartTime < n:
        seqEndTime = min(
            n - 1, 
            seqStartTime + self.windowSize - 1
        )

        self.trainOneSeq(X, Y, seqStartTime, seqEndTime)
        seqStartTime += self.windowSize

        if modelFilepath is not None:
            self.saveModel(modelFilepath)

    self.buildMemory(X, Y, n)