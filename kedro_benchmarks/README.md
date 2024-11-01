This is the benchmark repository of Kedro, which is mainly used internally:

# Installation
`pip install asv`


# Run the benchmark
Run this in the terminal:
`asv run`

You can also run the benchmark for specific commits or a range of commits, for details
checkout the [official documentation](https://asv.readthedocs.io/en/stable/using.html#benchmarking)

For example, `asv run main..mybranch` will run benchmark against every single commits since branching off from
`main`.

## Run commits against two different commit
`asv run --bench runner main..runners --step 2`, this read "Run benchmarks that match a pattern for `runner` for `main` and `runners` branch for every commits, with a total step of 2. This will result in only running the latest commit for `main` and latest commit for `runners`, if you need it to sample more commits you can increase the `step`.

## Compare benchmark for two commits:
Run this in the terminal:
`asv compare v0.1 v0.2`

This run benchmark against two different commits
