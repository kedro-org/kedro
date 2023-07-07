import importlib
import warnings
import pytest
from unittest.mock import patch

def test_import_kedro_with_no_official_support_raise_error(mocker, monkeypatch):
    """Test importing kedro should fails with python>=3.11 should fails"""
    import kedro
    
@pytest.mark.filterwarnings("default:Kedro")
def test_import_kedro_slient_warning(mocker, monkeypatch):
    """Test importing kedro when warning is silent"""
    import kedro
