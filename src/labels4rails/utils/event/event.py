from abc import ABCMeta, abstractmethod
from typing import Callable
from enum import Enum
from typing import Union, Hashable


class IEventHub(metaclass=ABCMeta):
    """
    Call functions with arguments by publishing events.
    """

    @abstractmethod
    def subscribe(self, event_name: Hashable, function: Callable) -> None:
        """
        Subscribe function to an event.
        :param event_name: Name of the event
        :param function: Function to call by event
        """
        pass

    @abstractmethod
    def unsubscribe(self, event_name: Hashable, function: Callable) -> None:
        """
        Unsubscribe function from a event.
        :param event_name: Name of the event
        :param function: Function to unsubscribe
        """
        pass

    @abstractmethod
    def unsubscribe_all(self, function: Callable) -> None:
        """
        Unsubscribe function from all events.
        :param function: Function to unsubscribe
        """
        pass

    @abstractmethod
    def post(self, event_name: Union[str, Enum], *args) -> None:
        """
        Post an event.
        :param event_name: Name of the event.
        :param args: Arguments to call subscribed functions
        """
        pass


class EventHub(IEventHub):
    def __init__(self):
        self.subscribers: dict[Hashable, list[Callable]] = dict()

    def subscribe(self, event_name: Hashable, function: Callable) -> None:
        """
        Subscribe function to an event.
        :param event_name: Name of the event
        :param function: Function to call by event
        """
        if function not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(function)
        

    def unsubscribe(self, event_name: Hashable, function: Callable) -> None:
        """
        Unsubscribe function from a event.
        :param event_name: Name of the event
        :param function: Function to unsubscribe
        """
        if event_name not in self.subscribers:
            return
        # Listener could be subscribed more than once to an event.
        while True:
            try:
                # print(f'UNsubscribed: {event_name=}')
                self.subscribers[event_name].remove(function)
            except ValueError:
                break
        
    def unsubscribe_all(self, function: Callable) -> None:

        """
        Unsubscribe function from all events.
        :param function: Function to unsubscribe
        """

        for event_type, functions in self.subscribers.items():
            if function in functions:
                self.unsubscribe(event_type, function)

    def post(self, event_name: Hashable, *args) -> None:
        """
        Post an event.
        :param event_name: Name of the event.
        :param args: Arguments to call subscribed functions
        """
        if event_name not in self.subscribers:
            return
        for function in self.subscribers[event_name]:
            function(*args)
