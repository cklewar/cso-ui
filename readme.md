# Project CSO - SD-WAN POC DEMO UI #

## VM Specs ##

- OS: Ubuntu 16.04 or 18.04
- CPU: 1
- RAM: 1024MB
- STORAGE: Well at least 20MB for libs and actual code

## Installation ##

Install a Ubuntu 16.04 or 18.04 virtual machine and login to this machine via ssh.
Replace __USER__ with user you created during Ubuntu setup and actual __IP__ with machine IP.

```bash
ssh -l <USER> <IP> or ssh <USER>@<IP>
```

All upcoming operations are done with user __root__.

```bash
juniper@cso-ui:~$ sudo su
[sudo] password for juniper:
```

Change directory to user root home directory:

```bash
cd /root
```

Clone the repo with:

```bash
git clone https://git.juniper.net/cpo-solutions/cso-underlay-automation/cso-ui.git
```

Change into directory __cso-ui__

```bash
cd cso-ui
```

Start the installer:

```bash
root@cso-ui:/home/juniper/cso-ui# ./install.sh --help

Usage:
 ./install.sh [ --prepare <host_ip> <ws_ip>]
 ./install.sh [ --build=<host_ip> ]
 ./install.sh [ --buildUi=<host_ip> ]
 ./install.sh [ --buildGitlab=<host_ip> ]
 ./install.sh [ --cleanup ]
 ./install.sh [ --cleanupUi ]
 ./install.sh [ --cleanupGitlab ]
 ./install.sh [ --import <host_ip> <file> ]
 ./install.sh [ --all <host_ip> <ws_ip> <file> ]
 ./install.sh [ --help | -h ]
```

There are several options available within the installer. Since we have a fresh Ubuntu box
we will go with:

```bash
./install --all 10.11.111.180 10.11.111.180 cso_ops_usecases_export.tar.gz
```

* *NOTE:*    
   * The <host_ip> option should be the ip of the host that the docker container is running on.
   * The <ws_ip> option should be the ip of the host that the docker container is running on.
   * The <_file_> option should point to the repo file which should be imported into gitlab. 
     You will find this file inside __<cso_ui>__ directory being called __cso_ops_usecases_export.tar.gz__.

Option __--all__ will run through all the required steps to build the environment.
Example output of running installer:

```bash
./install.sh --all 192.168.10.5 172.30.52.57 cso_ops_usecases_export.tar.gz 

#########################################################################
Prepare environment
#########################################################################
gpg: keyring `/tmp/tmpvw4aw1td/secring.gpg' created
gpg: keyring `/tmp/tmpvw4aw1td/pubring.gpg' created
gpg: requesting key CC86BB64 from hkp server keyserver.ubuntu.com
gpg: /tmp/tmpvw4aw1td/trustdb.gpg: trustdb created
gpg: key CC86BB64: public key "Launchpad PPA for Roberto Mier Escand?n \xee\x83\xbf" imported
gpg: Total number processed: 1
gpg:               imported: 1  (RSA: 1)
'ascii' codec can't decode byte 0xc3 in position 108: ordinal not in range(128)
Hit:1 http://ppa.launchpad.net/rmescandon/yq/ubuntu xenial InRelease
Hit:2 http://archive.ubuntu.com/ubuntu xenial InRelease
Get:3 http://security.ubuntu.com/ubuntu xenial-security InRelease [109 kB]
Get:4 http://archive.ubuntu.com/ubuntu xenial-updates InRelease [109 kB]          
Get:5 http://archive.ubuntu.com/ubuntu xenial-backports InRelease [107 kB]                 
Fetched 325 kB in 0s (629 kB/s)                             
Reading package lists... Done
Reading package lists... Done
Building dependency tree       
Reading state information... Done
curl is already the newest version (7.47.0-1ubuntu2.12).
git is already the newest version (1:2.7.4-0ubuntu1.6).
yq is already the newest version (2.2-1).
0 upgraded, 0 newly installed, 0 to remove and 15 not upgraded.
#########################################################################
Build UI container
#########################################################################
```  

After installer finishes open browser (preferred browser is Google Chrome) and access:

- cso-ui: http://<HOST_IP>:8670
  User: root
  Password: juniper123
- Gitlab: http://<HOST_IP>:9080
  User: root
  Password: juniper123

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