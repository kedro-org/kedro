FROM gitpod/workspace-full:2023-05-08-21-16-55

# Some datasets work on 3.8 only
RUN pyenv install 3.8.17\
    && pyenv global 3.8.17

# VideoDataSet
RUN sudo apt-get update && sudo apt-get install -y --no-install-recommends libgl1
RUN sudo apt-get install make
RUN       pip install -e /workspace/kedro \
      && cd /workspace \
     &&  yes project | kedro new -s pandas-iris --checkout main \
   &&   pip install -r /workspace/kedro/test_requirements.txt /workspace/project/src/requirements.txt \
     && cd /workspace/kedro \
     &&  pre-commit install --install-hooks

WORKDIR /workspace