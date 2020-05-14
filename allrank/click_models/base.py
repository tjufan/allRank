import math
from abc import ABC, abstractmethod
from typing import List, Tuple, Callable

import numpy as np


class ClickModel(ABC):
    """
    Base class for all click models. Specifies the contract to be delivered
    """

    @abstractmethod
    def click(self, documents: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        """
        applies a click model and returns the mask for documents.

        :rtype: np.ndarray [ number_of_documents ] -> a  mask of length same as documents -
        representing whether document was clicked (1) or not (0) or remained masked (-1)

        :param documents: Tuple of :
           np.ndarray [ number_of_documents, dimensionality_of_latent_vector ], representing features of documents
           np.ndarray [ number_of_documents ] representing relevancy of documents
        """
        pass


class RandomClickModel(ClickModel):
    """
    this ClickModel clicks a configured number of times on a random documents
    """

    def __init__(self, n_clicks: int):
        """

        :param n_clicks: number of documents that will be clicked
        """
        self.n_clicks = n_clicks

    def click(self, documents: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        X, y = documents
        clicks = np.random.choice(range(len(y)), size=self.n_clicks, replace=False)
        mask = np.repeat(0, len(y))
        mask[clicks] = 1
        return mask


class FixedClickModel(ClickModel):
    """
    this ClickModel clicks on a documents at fixed positions

    """

    def __init__(self, click_positions: List[int]):
        """

        :param click_positions: list of indices of documents that will be clicked
        """
        self.click_positions = click_positions

    def click(self, documents: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        X, y = documents
        clicks = np.repeat(0, len(y))
        clicks[self.click_positions] = 1
        return clicks


class MultipleClickModel(ClickModel):
    """
    This click model is delegating to one from given click models with given probability
    """

    def __init__(self, click_models: List[ClickModel], probabilities: List[float]):
        """

        :param click_models: list of candidate click models
        :param probabilities: list of probabilities - must be of the same length as list of click models and sum to 1.0
        """
        self.click_models = click_models
        assert math.isclose(np.sum(probabilities), 1.0, abs_tol=1e-5), \
            f"probabilities should sum to one, but got {probabilities} which sums to {np.sum(probabilities)}"
        self.probabilities = np.array(probabilities).cumsum()

    def click(self, documents: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        index = np.argmax(np.random.rand() < self.probabilities)
        result = self.click_models[index].click(documents)
        return result


class ConditionedClickModel(ClickModel):
    """
        This click model allows to combine multiple click models with a logical funciton

        """

    def __init__(self, click_models: List[ClickModel], combiner: Callable):
        """

        :param click_models: list of click models to combine
        :param combiner: a function applied to the result of clicks from click models - e.g. np.all or np.any
        """
        self.click_models = click_models
        self.combiner = combiner

    def click(self, documents: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        clicks_from_click_models = [click_model.click(documents) for click_model in self.click_models]
        return self.combiner(clicks_from_click_models, 0)


class MaxClicksModel(ClickModel):
    """
    This click model that takes other click model and limits the number of clicks to given value.
    Effectively keeping top <max_clicks> clicks
    """

    def __init__(self, click_model: ClickModel, max_clicks: int):
        """

        :param click_model: a delegate click model to generate clicks
        :param max_clicks: number of clicks that should be preserved
        """
        self.click_model = click_model
        self.max_clicks = max_clicks

    def click(self, documents: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        underlying_clicks = self.click_model.click(documents)
        if self.max_clicks is not None:
            max_clicks_mask = underlying_clicks.cumsum() <= self.max_clicks
            return underlying_clicks * max_clicks_mask
        return underlying_clicks


class OnlyRelevantClickModel(ClickModel):
    """
    this ClickModel clicks on a document when its relevancy is at least of predefined value

    """

    def __init__(self, relevancy_threshold: float):
        """

        :param relevancy_threshold: a minimum value of relevancy of a document to be clicked (inclusive)
        """
        self.relevancy_threshold = relevancy_threshold

    def click(self, documents: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        X, y = documents
        return np.array(y) >= self.relevancy_threshold