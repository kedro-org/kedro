FROM ubuntu:16.04

RUN apt-get update && \
    apt-get install -y cmake build-essential gcc g++ git wget libgl1-mesa-glx

RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections
RUN apt-get install -y --no-install-recommends msttcorefonts

# python-package
# miniconda
RUN wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    /bin/bash Miniconda3-latest-Linux-x86_64.sh -f -b -p /opt/conda && \
    export PATH="/opt/conda/bin:$PATH"

ENV PATH /opt/conda/bin:$PATH

RUN conda install -y numpy scipy scikit-learn pandas matplotlib

RUN pip install kedro


# clean
RUN apt-get autoremove -y && apt-get clean && \
    conda clean -i -l -t -y && \
    rm -rf /usr/local/src/*

