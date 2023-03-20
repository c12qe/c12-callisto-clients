from typing import Union, List
from qiskit.providers.provider import ProviderV1
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from c12simulator_clients.api.client import Request
from c12simulator_clients.qiskit_back.c12sim_backend import C12SimBackend
from c12simulator_clients.qiskit_back.exceptions import C12SimApiError
from c12simulator_clients.api.exceptions import ApiError
from c12simulator_clients.user_configs import UserConfigs


class C12SimProvider(ProviderV1):
    """
    Class that represent a Provider class for C12 simulator.
    It gives (provides) access to C12SIM backend.

    """

    _request: Request = None
    _user_configs: UserConfigs = None

    def __init__(self, user_config: UserConfigs):
        self._user_configs = user_config
        self._request = Request(self._user_configs.token, self._user_configs.verbose)

    @property
    def user_configs(self):
        return self._user_configs

    def backends(self, name=None, **kwargs) -> List[str]:
        """
        Return all available backends for the current user.

        :param name: string of backend name
        :param kwargs: optional args
        :return: list of backend objects

        :raise C12SimApiError if an error occurred during the API request

        """

        try:
            backends = self._request.get_backends()
            if name is not None:
                backends = [item for item in backends if (name in item["backend_name"])]
            return backends
        except PermissionError:
            return []
        except ApiError as api_err:
            raise C12SimApiError(
                "Unexpected error happened during the accessing the remote server"
            ) from api_err

    def get_backend(self, name=None, **kwargs) -> Union[C12SimBackend, None]:
        """
        Function to get a backend from a current provider.

        :param name: string representing the name of a backend
        :param kwargs:
        :return: C12SIMBackend instance

        :raise QiskitBackendNotFoundError if there is no backend available
               C12SimApiError if there is a problem in communication with remote server
        """

        if name is None:
            return None

        list_backends = self.backends(name)

        if len(list_backends) == 0:
            raise QiskitBackendNotFoundError("There is no available backends.")

        try:
            properties = [item for item in list_backends if (name in item["backend_name"])]
        except KeyError as kerr:
            raise QiskitBackendNotFoundError(f"There is no backend with a name {name}") from kerr

        if len(properties) == 0:
            raise QiskitBackendNotFoundError(f"There is no backend with a name {name}")

        if self._user_configs.verbose:
            print(f"Backend properties {properties}")

        backend = C12SimBackend(
            provider=self, name=name, request=self._request, properties=properties[0]
        )

        return backend
