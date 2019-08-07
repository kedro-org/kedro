# Kedro contrib

The contrib directory is meant to contain user contributions, these
contributions might get merged into core Kedro at some point in the future.

When create a new module in `contrib`, place it exactly where it would be if it
was merged into core Kedro.

For example, data sets are under the core package `kedro.io`. If you are
contributing a Data Set you should have the following directory:
`kedro/contrib/my_project/io/` - i.e., the name of your project before the
`kedro` package path.

This is how a module would look like under `kedro/contrib`:
```
kedro/contrib/my_project/io/
    my_module.py
    README.md
```

You should put you test files in `tests/contrib/my_project`:
```
tests/contrib/my_project
    test_my_module.py
```

## Requirements

If your project has any requirments that are not in the core `requirements.txt`
file. Please add them in `setup.py` like so:
```
...
extras_require={
        'my_project': ['requirement1==1.0.1', 'requirement2==2.0.1'],
    },
```

Please notice that a readme with instructions about how to use your module
and 100% test coverage are required to accept a PR.
