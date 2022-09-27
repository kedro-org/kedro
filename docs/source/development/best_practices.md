# Best Practices

Two important steps to achieving high code quality and maintainability in your Kedro project are the use of linting tools and automated tests. Let's take a look at how you can set these up.

## Automated Testing

Software testing is the process of checking that the code you have written fulfils its requirements. Software testing can either be **manual** or **automated**. In the context of Kedro:
- **Manual testing** is when you run part or all of your project and check that the results are what you expect.
- **Automated testing** is writing new code (using code libraries called _testing frameworks_) that runs part or all of your project and automatically checks the results against what you expect.

As a project grows larger, new code will increasingly rely on existing code. Making changes in one part of the code base can unexpectedly break the intended functionality in another part.

The major disadvantage of manual testing is that it is time-consuming. Manual tests are usually run once for new functionality, directly after it has been added. Manual testing is a bad solution to the problem of breaking dependencies.

The solution to this problem is automated testing, which allows many tests across the codebase to be run in seconds, every time a new feature is added or an old one is changed. In this way, breaking changes can be discovered early, before any time is lost in production.

### Set Up Automated Testing with Pytest

There are many testing frameworks available for Python. One of the most popular is a [pytest](https://docs.pytest.org/). Pytest is often used in Python projects for its short, readable tests and powerful set of features. Let's look at how you can start working with pytest in your Kedro project.

#### Installing pytest

Install pytest as you would install other packages with pip, making sure your project's virtual environment is active.

```bash
pip install pytest
```