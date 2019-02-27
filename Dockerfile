FROM python:3

RUN mkdir /cso-ui
COPY . /cso-ui
RUN python3 -m pip install --no-cache-dir -r /cso-ui/requirements.txt
COPY ./config/ssh/config /root/.ssh/config
COPY ./config/ssh/cso-ui /root/.ssh/cso-ui
RUN chmod 400 /root/.ssh/cso-ui
WORKDIR /cso-ui
CMD [ "python3", "./main.py" ]