import importlib

from requests.auth import AuthBase

from kedro.io import DataSetError
from kedro.utils import load_obj


class BaseAuthFactory():

    @staticmethod
    def create(cls, class_type: str, **config):

        try:
            class_obj = load_obj(class_type)
        except Exception as err:
            raise DataSetError(
                f"The specified class path {class_type} for constructing an Auth object cannot be found."
            ) from err

        try:
            authenticator = class_obj(**config)  # type: ignore
        except TypeError as err:
            raise DataSetError(
                f"\n{err}.\nAuthenticator Object '{class_type}' must only contain arguments valid for the "
                f"constructor of '{class_obj.__module__}.{class_obj.__qualname__}'."
            ) from err
        except Exception as err:
            raise DataSetError(
                f"\n{err}.\nFailed to instantiate Authenticator Object '{class_type}' "
                f"of type '{class_obj.__module__}.{class_obj.__qualname__}'."
            ) from err
        else:
            if not isinstance(authenticator, AuthBase):
                raise DataSetError(
                    f"The requests library expects {class_type} to be an instance of AuthBase."
                )
        return authenticator