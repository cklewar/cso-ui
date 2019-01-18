FROM python:3

RUN mkdir /cso-ui
COPY . /cso-ui
RUN python3 -m pip install --no-cache-dir -r /cso-ui/requirements.txt
RUN mkdir -p /root/.ansible/plugins/callbakc
COPY ./lib/ansible.cfg /root/.ansible
COPY ./lib/driver/callback/cso.py /root/.ansible/plugins/callback
RUN ansible-galaxy install Juniper.junos
WORKDIR /cso-ui
CMD [ "python3", "./main.py" ]