import pytest

import kedro


def test_import_kedro_with_no_official_support_raise_error(mocker):
    """Test importing kedro with python>=3.12 should fail"""
    mocker.patch("kedro.sys.version_info", (3, 12))

    # We use the parent class to avoid issues with `exec_module`
    with pytest.raises(UserWarning) as excinfo:
        kedro.__loader__.exec_module(kedro)

    assert "Kedro is not yet fully compatible" in str(excinfo.value)


def test_import_kedro_with_no_official_support_emits_warning(mocker):
    """Test importing kedro python>=3.12 and controlled warnings should work"""
    mocker.patch("kedro.sys.version_info", (3, 12))
    mocker.patch("kedro.sys.warnoptions", ["default:Kedro is not yet fully compatible"])

    # We use the parent class to avoid issues with `exec_module`
    with pytest.warns(UserWarning) as record:
        kedro.__loader__.exec_module(kedro)

    assert len(record) == 1
    assert "Kedro is not yet fully compatible" in record[0].message.args[0]
