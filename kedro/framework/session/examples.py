"""
Example demonstrating KedroSession and KedroServiceSession usage.

This module shows how to:
1. Use the traditional KedroSession for single runs
2. Use the new KedroServiceSession for concurrent/multi-run workflows
"""

from pathlib import Path
from typing import Any

from kedro.framework.session import KedroSession, KedroServiceSession, RunConfig


def example_single_run() -> None:
    """Example: Using KedroSession for a single run (traditional usage)."""
    print("\n=== Example 1: Single Run with KedroSession ===\n")

    # KedroSession enforces one run per session
    with KedroSession.create(project_path=Path(".")) as session:
        result = session.run(pipeline_names=["__default__"])
        print(f"Single run completed successfully")
        print(f"Outputs: {list(result.keys())}")


def example_sequential_multirun() -> None:
    """Example: Using KedroServiceSession for sequential multirun."""
    print("\n=== Example 2: Sequential Multirun with KedroServiceSession ===\n")

    # KedroServiceSession allows multiple runs
    with KedroServiceSession.create(
        project_path=Path("."),
        max_workers=1,  # Sequential execution
    ) as session:
        # Create multiple run configurations
        configs = [
            session.create_run_config(
                pipeline_names=["pipeline_1"],
                runtime_params={"param_1": value},
            )
            for value in [1, 2, 3]
        ]

        # Execute runs sequentially
        results = session.run_sequential(configs, continue_on_error=False)

        # Print results
        for result in results:
            print(f"Run {result.run_id}: {result.status}")
            if result.status == "success":
                print(f"  Outputs: {list(result.outputs.keys())}")
            else:
                print(f"  Error: {result.exception}")


def example_concurrent_multirun() -> None:
    """Example: Using KedroServiceSession for concurrent multirun."""
    print("\n=== Example 3: Concurrent Multirun with KedroServiceSession ===\n")

    # KedroServiceSession with concurrent workers
    with KedroServiceSession.create(
        project_path=Path("."),
        max_workers=4,  # Concurrent execution with 4 workers
    ) as session:
        # Create multiple run configurations
        configs = [
            session.create_run_config(
                pipeline_names=["data_pipeline"],
                tags=["data"],
                runtime_params={"data_source": f"source_{i}"},
            )
            for i in range(10)
        ]

        # Define progress callback
        def progress_callback(completed: int, total: int) -> None:
            percent = (completed / total) * 100
            print(f"Progress: {completed}/{total} ({percent:.1f}%)")

        # Execute runs concurrently
        results = session.run_all(
            configs,
            continue_on_error=True,  # Continue even if some runs fail
            progress_callback=progress_callback,
        )

        # Aggregate results
        successful = [r for r in results if r.status == "success"]
        failed = [r for r in results if r.status == "failed"]

        print(f"\nSummary:")
        print(f"  Total runs: {len(results)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")

        if failed:
            print(f"\nFailed runs:")
            for result in failed:
                print(f"  {result.run_id}: {result.exception}")


def example_run_with_cross_run_dependencies() -> None:
    """Example: Using KedroServiceSession with cross-run dependencies."""
    print("\n=== Example 4: Cross-Run Dependencies ===\n")

    with KedroServiceSession.create(project_path=Path(".")) as session:
        # Run 1: Train model
        config_1 = session.create_run_config(
            pipeline_names=["training_pipeline"],
            tags=["train"],
        )
        result_1 = session.run(config_1)
        run_id_1 = result_1.run_id

        print(f"Training run {run_id_1} completed: {result_1.status}")

        # Run 2: Evaluate model using outputs from run 1
        config_2 = session.create_run_config(
            pipeline_names=["evaluation_pipeline"],
            tags=["evaluate"],
            load_versions={"model": run_id_1},  # Load model from run 1
        )
        result_2 = session.run(config_2)

        print(f"Evaluation run {result_2.run_id} completed: {result_2.status}")

        # Run 3: Hyperparameter tuning (parallel runs with different params)
        tuning_configs = [
            session.create_run_config(
                pipeline_names=["training_pipeline"],
                runtime_params={"learning_rate": lr, "batch_size": bs},
            )
            for lr in [0.001, 0.01, 0.1]
            for bs in [16, 32, 64]
        ]
        tuning_results = session.run_all(tuning_configs, continue_on_error=True)

        print(f"\nTuning runs completed:")
        for result in tuning_results:
            if result.status == "success":
                print(f"  {result.run_id}: {result.metadata.get('runtime_params')}")


def example_error_handling() -> None:
    """Example: Error handling in multirun scenarios."""
    print("\n=== Example 5: Error Handling in Multirun ===\n")

    with KedroServiceSession.create(
        project_path=Path("."),
        max_workers=2,
    ) as session:
        # Mix valid and invalid configurations
        configs = [
            session.create_run_config(
                pipeline_names=["pipeline_1"],
                runtime_params={"valid": True},
            ),
            session.create_run_config(
                pipeline_names=["nonexistent_pipeline"],  # This will fail
            ),
            session.create_run_config(
                pipeline_names=["pipeline_2"],
                runtime_params={"valid": True},
            ),
        ]

        # Continue on error to see all results
        results = session.run_all(configs, continue_on_error=True)

        print("\nResults with error handling:")
        for i, result in enumerate(results):
            print(f"  Run {i+1} ({result.run_id}): {result.status}", end="")
            if result.exception:
                print(f" - Error: {str(result.exception)[:50]}...")
            else:
                print()


def example_custom_context_per_run() -> None:
    """Example: Using custom environment and runtime params per run."""
    print("\n=== Example 6: Per-Run Environment & Runtime Params ===\n")

    with KedroServiceSession.create(project_path=Path(".")) as session:
        # Run in different environments with different params
        configs = [
            session.create_run_config(
                pipeline_names=["inference_pipeline"],
                env="dev",
                runtime_params={"model_path": "models/dev_model.pkl"},
            ),
            session.create_run_config(
                pipeline_names=["inference_pipeline"],
                env="prod",
                runtime_params={"model_path": "models/prod_model.pkl"},
            ),
        ]

        results = session.run_sequential(configs)

        for result in results:
            env = result.metadata.get("env")
            status = result.status
            print(f"Environment '{env}': {status}")


if __name__ == "__main__":
    # Run examples (commented out by default to avoid execution without proper setup)
    print("Kedro Session Examples")
    print("=" * 60)

    # Uncomment to run individual examples:
    # example_single_run()
    # example_sequential_multirun()
    # example_concurrent_multirun()
    # example_run_with_cross_run_dependencies()
    # example_error_handling()
    # example_custom_context_per_run()

    print("\nNote: Examples are provided for reference and documentation.")
    print("Uncomment the example functions in __main__ to run them.")
