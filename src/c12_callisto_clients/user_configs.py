from pydantic import BaseSettings


class UserConfigs(BaseSettings):
    token: str
    verbose: bool = False
