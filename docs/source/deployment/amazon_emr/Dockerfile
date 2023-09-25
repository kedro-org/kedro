FROM public.ecr.aws/emr-serverless/spark/emr-6.10.0:latest AS base

USER root

# Install Python build dependencies for pyenv
RUN yum install -y gcc make patch zlib-devel bzip2 bzip2-devel readline-devel  \
        sqlite sqlite-devel openssl11-devel tk-devel libffi-devel xz-devel tar

# Install git for pyenv installation
RUN yum install -y git

# Add pyenv to PATH and set up environment variables
ENV PYENV_ROOT /usr/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
ENV PYTHON_VERSION=3.9.16

# Install pyenv, initialize it, install desired Python version and set as global
RUN curl https://pyenv.run | bash
RUN eval "$(pyenv init -)"
RUN pyenv install ${PYTHON_VERSION} && pyenv global ${PYTHON_VERSION}

# Copy and install packaged Kedro project
ENV KEDRO_PACKAGE <PACKAGE_WHEEL_NAME>
COPY dist/$KEDRO_PACKAGE /tmp/dist/$KEDRO_PACKAGE
RUN pip install --upgrade pip && pip install /tmp/dist/$KEDRO_PACKAGE  \
    && rm -f /tmp/dist/$KEDRO_PACKAGE

# Copy and extract conf folder
ADD dist/conf.tar.gz /home/hadoop/

# Initialize log files
RUN mkdir -p /home/hadoop/logs
RUN touch /home/hadoop/logs/info.log
RUN touch /home/hadoop/logs/errors.log
RUN chmod -R a+w /home/hadoop/logs

# EMRS will run the image as hadoop
USER hadoop:hadoop