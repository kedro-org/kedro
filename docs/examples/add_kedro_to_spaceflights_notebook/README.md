# How to extract notebook content to markdown

To publish `add_kedro_to_a_notebook.ipynb` in the Kedro docs, follow these steps.

1. In your virtual environment: `pip install jupytext`
2. In the notebook folder: jupytext --set-formats ipynb,md <notebook_name>.ipynb
3. Move the resultant markdown to the appropriate docs folder


The two steps above create a markdown file with a copy of the contents of the notebook, and we may be able to automate this step as per https://jupytext.readthedocs.io/en/stable/config.html but it's beyond my level of knowledge.