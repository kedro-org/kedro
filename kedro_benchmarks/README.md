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

## Compare benchmark for two commits:
Run this in the terminal:
`asv compare v0.1 v0.2`

This run benchmark against two different commits