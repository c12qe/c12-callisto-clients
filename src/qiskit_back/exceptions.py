class C12SimApiError(Exception):
    """Error that happened during the communication with a server"""

    pass


class C12SimJobError(Exception):
    """Errors raised when a job failed."""

    pass
