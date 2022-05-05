'''
    Excepciones de la práctica 3
'''

class P3Exception(Exception):
    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg

    def __str__(self) -> str:
        return "Error: " + self.msg

class DSException(P3Exception):
    def __init__(self, msg=None):
        super().__init__(msg)
    
class SocketError(P3Exception):
    def __init__(self, e: OSError):
        super().__init__(str(e))
