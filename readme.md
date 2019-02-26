# Project CSO - SD-WAN POC DEMO UI #

## VM Specs ##

- OS: Any Linux we can drive Python3.7 on.
- CPU: 1
- RAM: 512MB
- STORAGE: Well at least 20MB for libs and actual code 😊

## Installation ##

### Standalone ###
We need __Python 3.7__

- Clone git repo 

```bash
git clone https://github.com/cklewar/cso-ui.git
```
- Change directory into new cloned directory

```bash
cd cso_ui
```

- Turn deamon mode on in __constants.py__ by setting option  __DEAMONIZE__ to __True__

```python
DEAMONIZE = True
``` 

- Install required packages

```bash
python3.7 -m pip install -r requirements.txt
```
- Start service

```bash
python3.7 main.py
```

- Access Landing page with:
  + URL: http(s)://\<IP>:\<PORT>
    * User: root / admin
    * PW: juniper123

This will fork and run as daemon. Currently no startup script for Systemd or SysV Init.

### Docker ###
If you want to run cso-ui use case runner in docker environment turn of deamon mode in __config/config.yml__ by setting option 
__DEAMONIZE__ to __False__.

```python
DEAMONIZE = False
``` 

Set Websocket client IP to docker host IP. Change GIT settings to fit your environment.

```yaml
ws_client_protocol: ws
ws_client_ip: 10.10.11.223
ws_client_port: 8670
git_protocol: http
git_host: 192.168.10.5
git_port: 9080
git_repo_url: cso_ops/usecases
```

Create required directories:

- /tmp/cso-ui/log
- /tmp/cso-ui/data

```bash
mkdir -p /tmp/cso-ui/log
mkdir -p /tmp/cso-ui/data

```

Run following commands on docker box:
```bash
docker build -t cso-ui .
docker run -d --rm -v /tmp/cso-ui:/tmp/cso-ui -p 8670:8670 --name cso-ui cso-ui
```

### Landing Page Cards ###

Cards are predefined at the moment to change settings manually edit file __config/items.yml__.

```yaml
useCase1:
  title: Use Case 1 - Local Break Out at Spoke
  playbook: pb.yml
  directory: telnet_junos_get_config/
  description: Local Break Out at Spoke
  image: dummy.png
  delete: false

useCase2:
  title: Use Case 2 - MultiHoming
  playbook: pb.yml
  directory: telnet_junos_get_config/
  description: MultiHoming
  image: dummy.png
  delete: false
```

### SSL ###
To enable SSL support for web server we need to create private key and a certificate. To do so we will use openssl.
When asked for common name put in IP address or DNS name of actual host providing landing page.
Private key and certificate file name are static and should not be changed for now. Both the files have to be placed in
__config__ directory.

```bash
openssl genrsa -out privkey.pem 2048
openssl req -new -x509 -days 365 -key privkey.pem -out cert.pem
```

If not already done copy these files to __config/ssl__.