FROM gitpod/workspace-full:2023-05-08-21-16-55

# Some datasets work on 3.8 only
RUN pyenv install 3.8.15\
    && pyenv global 3.8.15

# VideoDataSet
RUN sudo apt-get update && sudo apt-get install -y --no-install-recommends libgl1
RUN sudo apt-get install make
RUN npm install -g @mermaid-js/mermaid-cli
