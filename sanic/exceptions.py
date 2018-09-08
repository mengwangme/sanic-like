

class SanicException(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code

class InvalidUsage(SanicException):
    """
    无效用法异常
    """
    status_code = 400



