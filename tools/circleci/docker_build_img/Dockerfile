FROM cimg/python:3.8

WORKDIR /home/circleci

RUN sudo apt-get update && \
    sudo apt-get install curl pandoc openjdk-8-jdk-headless -y && \
    sudo apt-get clean && \
    sudo update-alternatives --set java /usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java

# Update cacerts: https://stackoverflow.com/a/50103533/1684058
RUN sudo rm /etc/ssl/certs/java/cacerts && \
    sudo update-ca-certificates -f

RUN curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    > miniconda.sh && bash miniconda.sh -b -p /home/circleci/miniconda

RUN sudo rm -rf ~/.pyenv/ /opt/circleci/.pyenv/

ARG PIP_REQS
ARG PY_VERSION
ARG CONDA_ENV_NAME=kedro_builder

# Install/Setup anaconda env
RUN bash -c "source /home/circleci/miniconda/etc/profile.d/conda.sh && \
    echo \"$PIP_REQS\" > /tmp/requirements.txt && \
    conda create --name=$CONDA_ENV_NAME python=$PY_VERSION && \
    conda activate $CONDA_ENV_NAME && \
    pip install --no-cache-dir --prefer-binary --upgrade -r /tmp/requirements.txt"
