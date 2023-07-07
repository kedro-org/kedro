import importlib
import warnings
import pytest

def test_import_kedro_with_no_official_support_raise_error(mocker, monkeypatch):
    """Test importing kedro should fails with python>=3.11 should fails"""
    import kedro
    with mocker.patch("kedro.sys"):
        kedro.__loader__.exec_module(kedro)

@pytest.mark.filterwarnings("default:Kedro")
def test_import_kedro_success(mocker):
    """Test importing kedro should fails with python>=3.11 should fails"""
    import kedro
    with mocker.patch("kedro.sys"):
        kedro.__loader__.exec_module(kedro)

def test_import_kedro_success_with_env_variable(mocker, monkeypatch):
    """Test importing kedro should fails with python>=3.11 should fails"""
    import kedro
    monkeypatch.setenv("PYTHONWARNINGS", "default:Kedro")
    with mocker.patch("kedro.sys"):
        kedro.__loader__.exec_module(kedro)

def test_import_kedro_success_with_env_variable(mocker, monkeypatch):
    """Test importing kedro should fails with python>=3.11 should fails"""
    import kedro
    with mocker.patch("kedro.sys"):
        kedro.__loader__.exec_module(kedro)
    
@pytest.mark.filterwarnings("default:Kedro")
def test_import_kedro_slient_warning(mocker, monkeypatch):
    """Test importing kedro when warning is silent"""
    import kedro
