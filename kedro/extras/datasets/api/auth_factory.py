"""``auth_factory`` creates `requests.auth.AuthBase` instances from Catalog configuration.
"""
from requests.auth import AuthBase

from kedro.io import DataSetError
from kedro.utils import load_obj


def create_authenticator(class_type: str, **kwargs):
    """
    Args:
        class_type: path to class that inherits from `requests.auth.AuthBase`.
        **kwargs: constructor parameters for this class.

    Returns:
        An instance of the class that is provided.
    Raises:
        DataSetError: if class cannot be loaded or instantiated,
        or class does not inherit from `requests.auth.AuthBase`
    """
    try:
        class_obj = load_obj(class_type)
    except Exception as err:
        raise DataSetError(
            f"The specified class path {class_type} "
            f"for constructing an Auth object cannot be found."
        ) from err

    try:
        authenticator = class_obj(**kwargs)  # type: ignore
    except TypeError as err:
        raise DataSetError(
            f"\n{err}.\nAuthenticator Object '{class_type}' "
            f"must only contain arguments valid for the "
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
