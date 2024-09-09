import logging

from kedro.framework.session.store import BaseSessionStore

FAKE_SESSION_ID = "fake_session_id"
STORE_LOGGER_NAME = "kedro.framework.session.store"


class TestBaseStore:
    def test_init(self, caplog):
        caplog.set_level(logging.DEBUG, logger="kedro")

        path = "fake_path"
        store = BaseSessionStore(path, FAKE_SESSION_ID)
        assert store == {}
        assert store._path == path
        assert store._session_id == FAKE_SESSION_ID

        expected_debug_messages = [
            "'read()' not implemented for 'BaseSessionStore'. Assuming empty store."
        ]
        actual_debug_messages = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == STORE_LOGGER_NAME and rec.levelno == logging.DEBUG
        ]
        assert actual_debug_messages == expected_debug_messages

    def test_save(self, caplog):
        caplog.set_level(logging.DEBUG, logger="kedro")

        path = "fake_path"
        store = BaseSessionStore(path, FAKE_SESSION_ID)
        store.save()
        assert store == {}

        expected_debug_messages = [
            "'read()' not implemented for 'BaseSessionStore'. Assuming empty store.",
            "'save()' not implemented for 'BaseSessionStore'. Skipping the step.",
        ]
        actual_debug_messages = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == STORE_LOGGER_NAME and rec.levelno == logging.DEBUG
        ]
        assert actual_debug_messages == expected_debug_messages
