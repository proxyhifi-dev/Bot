from queue import Queue

class EventBus:
    def __init__(self):
        self.events = Queue()

    def put(self, event):
        self.events.put(event)

    def get(self):
        return self.events.get()

    def empty(self):
        return self.events.empty()
