import tensorflow as tf
import numpy as np
import time

from model.loss import loss1, loss2

def runGruOnWindow(
    self,
    X,
    windowStartTime,
):  
    """Run GRU on a Window

    self: The object that called this method
    X: The entire input Sequence, it has shape (n, d)
    windowStartTime: Starting timestep of the window

    It runs the GRU on the window sequence given as 
    X[windowStartTime : windowStartTime + windowSize (exclusive)], 
    and then returns the final state of the GRU, it has shape (H,)
    """
    state = self.gru.get_initial_state(
        batch_size = 1, 
        dtype = tf.float32
    )

    for t in range(
        windowStartTime, 
        windowStartTime + self.windowSize
    ):
        state, _ = self.gru(
            np.expand_dims(X[t], 0), 
            state
        )

    return tf.squeeze(state)

def buildMemory(
    self,
    X, 
    Y, 
    currentTime
):
    """Build the Model Memory

    self: The object that called this method
    X: The entire input Sequence, it has shape (n, d)
    Y: The entire target Sequence, it has shape (n,)
    currentTime: The current timestep we are on, it is a scalar

    It build the memory using only information from
    X[0 : currentTime - 1] and Y[0 : currentTime - 1]. It build
    the memory within the object as self.S and self.q, and does
    not return anything.

    self.S has dim (self.memorySize, self.hiddenStateSize)
    self.q has dim (self.memorySize,)

    It throws an Exception if it cannot construct memory
    """
    if currentTime < self.windowSize + 1:
        raise Exception('Cannot Construct Memory')

    sampleLow = 0
    sampleHigh = currentTime - self.windowSize - 1

    self.S = [None] * self.memorySize
    self.q = [None] * self.memorySize

    for i in range(self.memorySize):
        windowStartTime = np.random.randint(
            sampleLow,
            sampleHigh + 1
        )

        self.S[i] = self.runGruOnWindow(X, windowStartTime)
        if Y[windowStartTime + self.windowSize] > self.threshold:
            self.q[i] = 1.0
        else:
            self.q[i] = 0.0

    self.S = tf.stack(self.S)
    self.q = tf.convert_to_tensor(self.q, dtype = tf.float32)

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
    """Run the Model on One Timestep

    self: The object that called this method
    gruState: Current state of the GRU, it has shape (1, H)
    X: The entire input Sequence, it has shape (n, d)
    Y: The entire target Sequence, it has shape (n,)
    currentTime: Current Timestep on which to train
    outerGradientTape: Gradient tape which corresponds to the
    training the model on the main model loss function loss1
    numNormalEvents: Number of normal events seen uptil now
    numExtremeEvents: Number of extreme events seen uptil now

    It updates the model parameters with respect to the minimization
    of the other loss function loss2, this would help in learning
    better summary for memory sequences. The outer gradient tape
    corresponding to the main loss is made to stop recording so that
    the updates to the parameters corresponding to loss2 are not
    recorded, they are in turn recorded by the inner tape which
    records operations for updating the parameters based on loss2.

    It Returns the following,
        - The current timestep's final output, it is a scalar
        - The current timestep's prediction about how much the 
        current timestep is an extreme event, it is a scalar
        - The next GRU state, it has shape (1, H)
    """
    with outerGradientTape.stop_recording():

        with tf.GradientTape() as innerGradientTape:

            self.buildMemory(X, Y, currentTime)
            pred = tf.squeeze(self.memOut(self.S))
            loss = loss2(
                pred, 
                self.q,
                numNormalEvents,
                numExtremeEvents,
                self.extremeValueIndex
            )

        trainableVars = self.gru.trainable_variables \
            + self.memOut.trainable_variables

        grads = innerGradientTape.gradient(loss, trainableVars)
        self.optimizer.apply_gradients(zip(
            grads,
            trainableVars
        ))

    nextState, _ = self.gru(np.expand_dims(X[currentTime], 0), gruState)
    semiPred = tf.squeeze(self.out(np.expand_dims(nextState, 0)))

    attentionWeights = self.computeAttentionWeights(tf.squeeze(nextState))
    extremePred = tf.math.reduce_sum(
        attentionWeights * self.q, 
        axis = 0
    )

    yPred = semiPred + self.b * extremePred
    return yPred, extremePred, nextState

def trainOneSeq(
    self,
    X, 
    Y, 
    seqStartTime, 
    seqEndTime
):
    """Train Model Over One Sequence

    self: The object that called this method
    X: The entire input Sequence, it has shape (n, d)
    Y: The entire target Sequence, it has shape (n,)
    seqStartTime: Starting timestep of sequence
    seqEndTime: Ending timestep of sequence

    Current sequence is given by X[seqStartTime : seqEndTime + 1]
    and Y[seqStartTime : seqEndTime + 1]. This function trains the
    model parameters on this sequence

    Returns sequence loss value
    """
    with tf.GradientTape() as tape:
        numNormalEvents = numExtremeEvents = 0
        state = self.gru.get_initial_state(
            batch_size = 1, 
            dtype = tf.float32
        )

        yPredSeq = []
        extremePredSeq = []
        extremeTargetSeq = []
        for t in range(seqStartTime, seqEndTime + 1):
            if Y[t] > self.threshold:
                extremeTarget = 1.0
                numExtremeEvents += 1
            else:
                extremeTarget = 0.0
                numNormalEvents += 1

            yPred, extremePred, state = self.trainOneTimestep(
                state,
                X,
                Y,
                t,
                tape,
                numNormalEvents,
                numExtremeEvents
            )

            yPredSeq.append(yPred)
            extremePredSeq.append(extremePred)
            extremeTargetSeq.append(extremeTarget)

        yPredSeq = \
            tf.convert_to_tensor(yPredSeq, dtype = tf.float32)
        extremePredSeq = \
            tf.convert_to_tensor(extremePredSeq, dtype = tf.float32)
        extremeTargetSeq = \
            tf.convert_to_tensor(extremeTargetSeq, dtype = tf.float32)

        loss = loss1(
            yPredSeq,
            Y[seqStartTime : seqEndTime + 1],
            extremePredSeq,
            extremeTargetSeq,
            self.extremeLossWeight,
            numNormalEvents,
            numExtremeEvents,
            self.extremeValueIndex
        )
    
    trainableVars = self.gru.trainable_variables \
        + self.out.trainable_variables \
        + [self.b]

    grads = tape.gradient(loss, trainableVars)
    self.optimizer.apply_gradients(zip(
        grads,
        trainableVars
    ))

    return loss

def trainModel(
    self, 
    X, 
    Y,
    seqLength,
    currTimestep,
    modelFilepath,
    verbose
):
    """Train Model on Dataset

    self: The object that called this method
    X: The entire input Sequence, it has shape (n, d)
    Y: The entire target Sequence, it has shape (n,)
    seqLength: Length of each sequence, imporant: each sequence
    except maybe the last would have length equal to seqLength
    currTimestep: We have to begin from here if not None and
    has value greater than or equall to windowSize, else we begin
    from windowSize + 1
    modelFilepath: Save model parameters to this path after every
    sequence if not None, else don't save
    verbose: 0 - no info, 1 - some info, > 1 - more info

    Train the model using the provided data and information
    """
    seqStartTime = self.windowSize + 1
    if currTimestep is not None:
        seqStartTime = max(seqStartTime, currTimestep)

    n = X.shape[0]
    if seqStartTime >= n:
        raise Exception("Insufficient Data")

    while seqStartTime < n:
        seqEndTime = min(
            n - 1, 
            seqStartTime + seqLength - 1
        )
        
        startTime = time.time()

        loss, squareLoss, extremeLoss = \
            self.trainOneSeq(X, Y, seqStartTime, seqEndTime)

        endTime = time.time()
        timeTaken = endTime - startTime
        if verbose > 0:
            print(
                f'start timestep: {seqStartTime}' \
                + f' | end timestep: {seqEndTime} ' \
                + f' | time taken: {timeTaken : .2f} sec' \
                + f' | Total Loss: {loss}'
                + f' | Square Loss: {squareLoss}'
                + f' | Extreme Loss (wt): {extremeLoss}'
            )

        seqStartTime += seqLength

        if modelFilepath is not None:
            self.saveModel(modelFilepath)

    self.buildMemory(X, Y, n)