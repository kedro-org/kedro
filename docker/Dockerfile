FROM python:3.7.6

RUN apt-get update
RUN apt-get install -qy libhdf5-serial-dev

WORKDIR /home/kedro

RUN wget https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/test_requirements.txt

RUN wget https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/requirements.txt

RUN pip install -r test_requirements.txt
