"""
  Basic URLs to the C12 sim APIs.
"""

HOST_URL = "127.0.0.1"  # "57.128.19.83"  # "api.dev-simulator.c12qe.net"
PORT = 9999  # Used for testing purposes

API_BASE_URL = f"http://{HOST_URL}{'' if PORT is None else ':'+str(PORT)}/api"

API_SIMULATOR_URL = API_BASE_URL + "/c12sim"
API_HEALTH_URL = API_BASE_URL + "/health"


API_QUERY_URL = API_SIMULATOR_URL + "/query"
API_BACKENDS_URL = API_SIMULATOR_URL + "/backends"
API_PARAMS_URL = API_SIMULATOR_URL + "/params"
API_MAXJOBS_URL = API_SIMULATOR_URL + "/maxjobs"
API_JOB_STATUS_URL = API_QUERY_URL + "/status"
API_USER_JOBS = API_SIMULATOR_URL + "/jobs"
API_GET_JOB = API_SIMULATOR_URL + "/job"
