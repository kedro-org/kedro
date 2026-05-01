::: kedro.framework.session
    options:
      docstring_style: google
      members: false
      show_source: false

| Module                          | Description                                                                 |
|---------------------------------|-----------------------------------------------------------------------------|
| [`AbstractSession`](#kedro.framework.session.abstract_session.AbstractSession) | Base class for all Kedro session implementations.               |
| [`KedroSession`](#kedro.framework.session.session.KedroSession) | Implements Kedro session responsible for project lifecycle.               |
| [`KedroServiceSession`](#kedro.framework.session.service_session.KedroServiceSession) | Implements Kedro service session responsible for project lifecycle.      |
| [`BaseSessionStore`](#kedro.framework.session.store.BaseSessionStore)     | Implements a dict-like store object used to persist Kedro sessions.       |
| [`KedroSessionError`](#kedro.framework.session.abstract_session.KedroSessionError) | Raised by `KedroSession` and `KedroServiceSession` when they encounter an error. |


::: kedro.framework.session.abstract_session.AbstractSession
    options:
      members: true
      show_source: true

::: kedro.framework.session.session.KedroSession
    options:
      members: true
      show_source: true

::: kedro.framework.session.service_session.KedroServiceSession
    options:
      members: true
      show_source: true

::: kedro.framework.session.store.BaseSessionStore
    options:
      members: true
      show_source: true

::: kedro.framework.session.abstract_session.KedroSessionError
    options:
      members: true
      show_source: true
