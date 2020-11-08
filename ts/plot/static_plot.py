import matplotlib.pyplot as plt
import matplotlib


class Plot:
    """Static Plotting Class"""

    @staticmethod
    def plotDataCols(X, colNames=None, title='Data Plot'):
        """
        Plots each column of X as a time series in a subplot

        :param X: Matrix with each column as a time series, it is a numpy array
        of shape (T, d)
        :param colNames: Names of each column. If it is not None, then this would
        be present as the subplot title for that column
        :param title: Title of the entire plot
        :return: None
        """

        matplotlib.use('TkAgg')

        (T, d) = X.shape
        fig, axes = plt.subplots(d)

        for dim in range(d):
            if d == 1:
                ax = axes
            else:
                ax = axes[0]

            ax.plot(X[:, dim])
            if colNames is not None:
                ax.set_title(colNames[dim])

        fig.suptitle(title)
        plt.show()

    @staticmethod
    def plotLoss(loss, title='Loss Plot', xlabel='Iterations', ylabel='Loss'):
        """
        Plots Loss vs Iterations Curve

        :param loss: 1D List or numpy array of shape (numIters,) of loss values
        which are to be plotted
        :param title: Title of the plot
        :param xlabel: x-axis Label of the plot
        :param ylabel: y-axis Label of the plot
        :return: None
        """

        matplotlib.use('TkAgg')

        plt.plot(loss)
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.show()
