FROM python:3

RUN mkdir /cso-ui
COPY . /cso-ui
RUN python3 -m pip install --no-cache-dir -r /cso-ui/requirements.txt
RUN mkdir /root/.ansible
COPY ./lib/ansible.cfg /root/.ansible
COPY ./lib/driver/callback/cso.py /root/.ansible
RUN ansible-galaxy install Juniper.junos
WORKDIR /cso-ui
CMD [ "python3", "./main.py" ]