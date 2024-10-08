from pydantic_settings import BaseSettings


class UserConfigs(BaseSettings):
    token: str
    verbose: bool = False
