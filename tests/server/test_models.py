from kedro.server.models import PipelineExecutionError, PipelineExecutionResult


def test_pipeline_execution_result_to_dict_omits_error_when_none():
    result = PipelineExecutionResult(run_id="run-1", status="success", duration_ms=12.3)

    as_dict = result.to_dict()

    assert "error" not in as_dict
    assert as_dict["run_id"] == "run-1"
    assert as_dict["status"] == "success"


def test_pipeline_execution_result_to_dict_omits_none_traceback():
    result = PipelineExecutionResult(
        run_id="run-2",
        status="failure",
        duration_ms=9.4,
        error=PipelineExecutionError(type="ValueError", message="boom", traceback=None),
    )

    as_dict = result.to_dict()

    assert as_dict["error"]["type"] == "ValueError"
    assert as_dict["error"]["message"] == "boom"
    assert "traceback" not in as_dict["error"]


def test_pipeline_execution_result_to_dict_keeps_traceback():
    result = PipelineExecutionResult(
        run_id="run-3",
        status="failure",
        duration_ms=7.1,
        error=PipelineExecutionError(
            type="RuntimeError", message="failed", traceback=["line 1", "line 2"]
        ),
    )

    as_dict = result.to_dict()

    assert as_dict["error"]["traceback"] == ["line 1", "line 2"]
