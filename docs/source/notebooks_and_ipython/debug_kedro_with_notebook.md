# Debug Kedro Pipeline with `%load_node` magic
`%load_node` is useful for debugging Kedro Pipeline. It will create multiple new cells
in the notebook includes:
- script to load Dataset and Parameters
- import statements
- function body


## Example with `spaceflights-pandas`
The following example assume you are working on the `spaceflights-pandas` project. You
can follow the full tutorial with this [Spaceflights tutorial](../tutorial/spaceflights_tutorial.md).

If you don't have a working project, you can quickly create one with this command:
```bash
kedro new --name=spaceflights-pandas --tools=none --example=yes
cd spaceflights-pandas
```
![debug.gif](../meta/images/debug.gif)
