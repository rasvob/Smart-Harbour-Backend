import logging

class AppLogger:
    def __init__(self, name, level=logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def get_logger(self):
        return self.logger