class AIServiceError(RuntimeError):
    pass


class AIExhaustedError(AIServiceError):
    pass
