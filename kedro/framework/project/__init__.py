# Copyright 2021 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
"""``kedro.framework.project`` module provides utitlity to
configure a Kedro project and access its settings."""
# pylint: disable=redefined-outer-name,unused-argument
import importlib
from warnings import warn

from dynaconf import LazySettings
from dynaconf.utils.functional import LazyObject
from dynaconf.validator import ValidationError, Validator

from kedro.framework.hooks import get_hook_manager
from kedro.framework.hooks.manager import _register_hooks, _register_hooks_setuptools


def _get_default_class(class_import_path):
    module, _, class_name = class_import_path.rpartition(".")

    def validator_func(settings, validators):
        return getattr(importlib.import_module(module), class_name)

    return validator_func


class _IsSubclassValidator(Validator):
    """A validator to check if the supplied setting value is a subclass of the default class"""

    def _validate_items(self, settings, env=None):
        super()._validate_items(settings, env)

        default_class = self.default(settings, self)
        for name in self.names:
            setting_value = getattr(settings, name)
            if not issubclass(setting_value, default_class):
                raise ValidationError(
                    f"Invalid value `{setting_value.__module__}.{setting_value.__qualname__}` "
                    f"received for setting `{name}`. It must be a subclass of "
                    f"`{default_class.__module__}.{default_class.__qualname__}`."
                )


class _ProjectSettings(LazySettings):
    """Define all settings available for users to configure in Kedro,
    along with their validation rules and default values.
    Use Dynaconf's LazySettings as base.
    """

    _CONF_ROOT = Validator("CONF_ROOT", default="conf")
    _HOOKS = Validator("HOOKS", default=tuple())
    _CONTEXT_CLASS = Validator(
        "CONTEXT_CLASS",
        default=_get_default_class("kedro.framework.context.KedroContext"),
    )
    _SESSION_STORE_CLASS = _IsSubclassValidator(
        "SESSION_STORE_CLASS",
        default=_get_default_class("kedro.framework.session.session.BaseSessionStore"),
    )
    _SESSION_STORE_ARGS = Validator("SESSION_STORE_ARGS", default={})
    _DISABLE_HOOKS_FOR_PLUGINS = Validator("DISABLE_HOOKS_FOR_PLUGINS", default=tuple())

    def __init__(self, *args, **kwargs):

        kwargs.update(
            validators=[
                self._CONF_ROOT,
                self._HOOKS,
                self._CONTEXT_CLASS,
                self._SESSION_STORE_CLASS,
                self._SESSION_STORE_ARGS,
                self._DISABLE_HOOKS_FOR_PLUGINS,
            ]
        )
        super().__init__(*args, **kwargs)


class _ProjectPipelines(LazyObject):
    def _setup(self):
        self._wrapped = {}

    def _get_register_pipelines(  # pylint: disable=no-self-use
        self, pipelines_module: str
    ):
        module_obj = importlib.import_module(pipelines_module)
        register_pipelines = getattr(module_obj, "register_pipelines")
        return register_pipelines

    def configure(self, pipelines_module=None, **kwargs):
        """Collect all pipelines from hooks and from
        the project's pipeline registry module.
        """
        try:
            register_pipelines = self._get_register_pipelines(pipelines_module)
        except (ModuleNotFoundError, AttributeError):
            # for backwards compatibility, this is fine
            project_pipelines = {}
        else:
            project_pipelines = register_pipelines()

        # get pipelines registered from external hooks
        hook_manager = get_hook_manager()
        pipelines_dicts = (
            hook_manager.hook.register_pipelines()  # pylint: disable=no-member
        )
        for pipeline_collection in pipelines_dicts:
            duplicate_keys = pipeline_collection.keys() & project_pipelines.keys()
            if duplicate_keys:
                warn(
                    f"Found duplicate pipeline entries. "
                    f"The following will be overwritten: {', '.join(duplicate_keys)}"
                )
            project_pipelines.update(pipeline_collection)

        for pipeline_name, pipeline in project_pipelines.items():
            self[pipeline_name] = pipeline


settings = _ProjectSettings()


pipelines = _ProjectPipelines()


def _validate_module(settings_module):
    """Eagerly validate that the module is importable.
    This ensures that the settings module is syntactically
    correct so that any import errors are surfaced early.
    """
    importlib.import_module(settings_module)


def configure_project(package_name: str):
    """Configure a Kedro project by populating its settings with values
    defined in user's settings.py and pipeline_registry.py.
    """
    settings_module = f"{package_name}.settings"
    _validate_module(settings_module)
    settings.configure(settings_module)

    # set up all hooks so we can discover all pipelines
    hook_manager = get_hook_manager()
    _register_hooks(hook_manager, settings.HOOKS)
    _register_hooks_setuptools(hook_manager, settings.DISABLE_HOOKS_FOR_PLUGINS)

    pipelines_module = f"{package_name}.pipeline_registry"
    pipelines.configure(pipelines_module)
