import io
import re
import time
import telnetlib
import threading
import queue as queue
import random

from threading import Thread
from lxml.etree import XMLSyntaxError
from jnpr.junos import Device
from jnpr.junos.utils.config import Config

if __name__ == '__main__':
    '''
    tn = telnetlib.Telnet(host='10.10.10.178', port=7001)

    while True:

        data = tn.read_until("\r\n".encode('utf-8'))
        print(data)

        if data.decode('utf-8').strip() in ["Amnesiac (ttyu0)", "Ubuntu 14.04.1 LTS jdm tty1"]:
            print("Box is rebooted since we see: <Amnesiac (ttyu0)>")

            tn.close()
            break
        time.sleep(0.2)
    '''
    #dev = Device(host='10.10.10.178', mode='telnet', port=7004)
    #print('before open')
    #dev.open()
    #print('after open')
    #print('before close')
    #dev.close()

    #print('after close')

    #print('Zerorize device <{0}>'.format('nfx250'))
    #message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': 'zeroizing'}
    #self.emit_message(message=message)

    # try:

    #dev = Device(host='10.10.10.178', mode='telnet', port=7001)
    #print('before open')
    #dev.open()
    #print('after open')
    #print(dev._tty._tn)
    #print('before rpc call')
    # resp = dev.rpc.request_jdm_system_zeroize()
    #resp = dev.zeroize()
    #print('after after rpc call')
    #print(resp)
    # print(etree.tostring(resp, encoding='unicode'))

    #message = {'action': 'update_task_status', 'uuid': task['uuid'], 'status': resp}
    #self.emit_message(message=message)

    #dev._tty.nc.close(force=True)
    #print('before close')
    #dev.close(skip_logout=True)
    #skip_logout=False
    # dev._conn._session.close()
    #print('after close')

    #tn = telnetlib.Telnet(host='10.11.111.251', port=32771)
    #tn.write('cd /tmp'.encode('ascii') + b"\n")
    #tn.write('echo test125 > test123.txt'.encode("ascii") + b"\n")
    #tn.write('cat > test_cert.crt << EOF'.encode('ascii') + b"\n")
    #tn.write('a'.encode("ascii") + b"\n")
    #tn.write('EOF'.encode("ascii") + b"\n")
    #print(tn.read_all().decode("ascii"))
    #tn.close()

    #dev = Device(host='10.10.10.178', mode='telnet', port=7004)
    #print('before open')
    #dev.open()
    #print('after open')
    #cu = Config(dev)

    config_text = """
    system {
        scripts {
            op {
                file test.slax;
            }
        }
    }
    """

    cfg = """
    chassis {
        delete: auto-image-upgrade;
    }
    system {
        root-authentication {
            encrypted-password "$6$nCsDlN7N$qTG9G3zHHBcF8wwIkuH3VAwbwU4oV4kdhwv7CSyenNDA/qReSfZ2kuUPGcQWmnON4mfKAwjC323c8hkKr3iWh1"; ## SECRET-DATA
        }
    }
    """

    #cu.load('delete chassis auto-image-upgrade', format="set", merge=True)
    #cu.load(cfg, format="text", merge=True)
    #cu.commit(confirm=False, sync=False)

    #print('before close')
    #dev.close()
    #target = 'vsrx01'
    #string = "vsrx01 (ttyu0)"
    #re_str1 = r'\(tty.*\)'
    #re_pattern = re.compile(target + ' ' + re_str1)
    #match = re_pattern.match(string)
    #print(match)

    #target = 'vsrx01'
    #if 'vsrx01 (ttyu0)' == re.match(r'\(tty.*\)'):
    #    print('got it')

    def itercount(filename):
        return sum(1 for _ in open(filename, 'rb'))

    #print(itercount('cert.ca'))


    # Print iterations progress
    def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█'):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
        # Print New Line on Complete
        if iteration == total:
            print()


    # A List of Items
    #items = list(range(0, 57))
    #l = len(items)

    # Initial call to print 0% progress
    '''
    printProgressBar(0, l, prefix='Progress:', suffix='Complete', length=50)
    for i, item in enumerate(items):
        # Do stuff...
        time.sleep(0.5)
        # Update Progress Bar
        printProgressBar(i + 1, l, prefix='Progress:', suffix='Complete', length=50)
    '''

    #_file = 'cert.ca'

    #with open(_file, 'r') as fd:
    #    total_lines = sum(1 for _ in open(_file, 'rb'))
    #    print('Total lines: {0}'.format(total_lines))
    #    line_count = 0

    #    for line in fd:
    #        #print(line)
    #        line_count += 1
    #        print('{0}%'.format(int(100 * (line_count / float(total_lines)))))
    #        time.sleep(0.5)

    data = """
    groups {
    global {
        security {
            forwarding-options {
                family {
                    mpls {
                        mode flow-based;
                    }
                }
            }
        }
    }
}
apply-groups global;
system {
    host-name srx300;
    root-authentication {
        encrypted-password "$6$g1.wm$UWjbUq7VJp1KjRPViD9W0xW4NSXGSWlE/f5esQ4xyGep8.nOL4RcPEtRgr/a2zj0dl4Kn9.9CTwViGsRj8Pl81"; ## SECRET-DATA
    }
    name-server {
        192.168.10.10;
    }
    services {
        ftp;
        rlogin;
        ssh;
        telnet;
        netconf {
            ssh;
            rfc-compliant;
        }
    }
    syslog {
        user * {
            any emergency;
        }
        file messages {
            any any;
            authorization info;
        }
        file interactive-commands {
            interactive-commands any;
        }
    }
    license {
        autoupdate {
            url https://ae1.juniper.net/junos/key_retrieval;
        }
    }
    phone-home {
        server https://centralmsvm.example.net;
        ca-certificate-file /var/tmp/ssl_cert.crt;
        rfc-complaint;
    }
}
security {
    log {
        utc-timestamp;
        mode stream;
        format sd-syslog;
        source-address 192.168.0.1;
        transport {
            protocol tcp;
        }
    }
    flow {
        allow-dns-reply;
        allow-embedded-icmp;
        inactive: tcp-mss {
            ipsec-vpn {
                mss 1350;
            }
        }
        tcp-session {
            no-syn-check;
            no-syn-check-in-tunnel;
            no-sequence-check;
        }
    }
    nat {
        source {
            rule-set own-mgmt-traffic-nat {
                from routing-instance default;
                to interface ge-0/0/0.0;
                rule r1 {
                    match {
                        source-address 0.0.0.0/0;
                    }
                    then {
                        source-nat {
                            interface;
                        }
                    }
                }
            }
            rule-set syslognat {
                from routing-instance default;
                to zone untrust;
                rule syslognatr1 {
                    match {
                        source-address 192.168.0.1/32;
                        destination-address 0.0.0.0/0;
                    }
                    then {
                        source-nat {
                            interface;
                        }
                    }
                }
            }
        }
    }
    policies {
        from-zone trust to-zone untrust {
            policy allow_all {
                match {
                    source-address any;
                    destination-address any;
                    application any;
                }
                then {
                    permit;
                }
            }
        }
        from-zone trust to-zone trust {
            policy allow_all {
                match {
                    source-address any;
                    destination-address any;
                    application any;
                }
                then {
                    permit;
                }
            }
        }
    }
    zones {
        security-zone trust {
            host-inbound-traffic {
                system-services {
                    all;
                }
                protocols {
                    all;
                }
            }
        }
        security-zone oam {
            host-inbound-traffic {
                system-services {
                    all;
                }
                protocols {
                    all;
                }
            }
            interfaces {
                lo0.0;
            }
        }
        security-zone untrust {
            host-inbound-traffic {
                system-services {
                    all;
                }
                protocols {
                    all;
                }
            }
            interfaces {
                ge-0/0/0.0;
                ge-0/0/1.0;
            }
        }
    }
}
interfaces {
    ge-0/0/0 {
        unit 0 {
            family inet {
                address 192.168.170.2/24;
            }
        }
    }
    ge-0/0/1 {
        unit 0 {
            family inet {
                dhcp-client {
                    lease-time infinite;
                }
            }
        }
    }
    lo0 {
        description "Loopback Interface";
        unit 0 {
            family inet {
                address 192.168.0.1/24;
            }
        }
    }
    st0 {
        per-unit-scheduler;
    }
}
routing-options {
    static {
        route 0.0.0.0/0 {
            next-hop 192.168.170.1;
            no-readvertise;
        }
    }
}
"""

    #dev = Device(host='10.10.10.178', mode='telnet', port=7006, user='root', password='Embe1mpls')
    #dev.open()
    #cu = Config(dev)
    #cu.load(data, overwrite=True)
    #cu.commit(confirm=False, sync=False)

    #try:

    #except XMLSyntaxError as err:
    #    print(err)

    #dev.close()

    #src = ['ca.crt','licenses/srx.lic']
    #dst = ['/etc/ssl/ca.crt', 'tmp/srx.lic']

    #print(map(src, dst))
    #print(list(zip(src, dst)))

    #re_pattern = re.compile(r'add license failed \(1 errors\)')
    #term_str = re_pattern.match('add license failed (1 errors)')
    # print(repr(_data))
    # print(_data == term_str)
    #print(term_str)

    '''
    q = queue.Queue()
    threads = []
    results = {}

    def do_work():
        time.sleep(random.randint(1,5))

    def worker(name, result):
        do_work()
        result[name] = 'Finished'

    for i in range(3):
        name = 'Thread-{0}'.format(i)
        t = threading.Thread(target=worker, name=name, args=[name, results])
        t.start()
        threads.append(t)

    for item in threads:
        item.join()

    print(results)
    '''

    #task = {'name': 'Copy', 'src': ['sourceA'], 'dst': ['destinationA']}

    #for item in list(zip(task['src'], task['dst'])):
    #   print('[{0}][{1}]: Copy file <{2}> to <{3}>'.format('TargetA', task['name'], item[0], item[1]))

    def escape_ansi(line=None):
        ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
        return ansi_escape.sub('', line)

    test123 = [
        b' * Starting workaround for missing events in container\x1b[74G[ OK ]\r\n',
        b' * Stopping load fallback graphics devices\x1b[74G[ OK ]\r\n',
        b' * Stopping workaround for missing events in container\x1b[74G[ OK ]\r\n',
        b' * Starting set console font\x1b[74G[ OK ]\r\n',
        b' * Starting set console font\x1b[74G[\x1b[31mfail\x1b[39;49m]\r\n',
        b' * Starting userspace bootsplash\x1b[74G[ OK ]\r\n',
        b' * Starting configure network device security\x1b[74G[ OK ]\r\n',
        b' * Stopping userspace bootsplash\x1b[74G[ OK ]\r\n',
        b' * Starting Send an event to indicate plymouth is up\x1b[74G[ OK ]\r\n',
        b' * Stopping Send an event to indicate plymouth is up\x1b[74G[ OK ]\r\n',
        b' * Starting mount available cgroup filesystems\x1b[74G[ OK ]\r\n',
        b' * Starting Mount network filesystems\x1b[74G[ OK ]\r\n',
        b' * Stopping Mount network filesystems\x1b[74G[ OK ]\r\n',
        b' * Starting Bridge socket events into upstart\x1b[74G[ OK ]\r\n',
        b' * Starting configure network device\x1b[74G[ OK ]\r\n',
        b' * Stopping Populate /dev filesystem\x1b[74G[ OK ]\r\n',
        b' * Starting Signal sysvinit that virtual filesystems are mounted\x1b[74G[ OK ]\r\n',
        b' * Starting Signal sysvinit that virtual filesystems are mounted\x1b[74G[ OK ]\r\n',
        b' * Starting Signal sysvinit that local filesystems are mounted\x1b[74G[ OK ]\r\n',
        b' * Starting configure network device security\x1b[74G[ OK ]\r\n',
        b' * Starting Signal sysvinit that remote filesystems are mounted\x1b[74G[ OK ]\r\n',
        b' * Stopping Mount filesystems on boot\x1b[74G[ OK ]\r\n',
        b' * Starting Failsafe Boot Delay\x1b[74G[ OK ]\r\n',
        b' * Starting flush early job output to logs\x1b[74G[ OK ]\r\n',
        b' * Stopping flush early job output to logs\x1b[74G[ OK ]\r\n',
        b' * Starting D-Bus system message bus\x1b[74G[ OK ]\r\n',
        b' * Starting Bridge file events into upstart\x1b[74G[ OK ]\r\n',
        b' * Starting SystemD login management service\x1b[74G[ OK ]\r\n',
        b' * Starting system logging daemon\x1b[74G[ OK ]\r\n',
        b' * Starting Mount network filesystems\x1b[74G[ OK ]\r\n',
        b' * Stopping Mount network filesystems\x1b[74G[ OK ]\r\n',
        b' * Starting Mount network filesystems\x1b[74G[ OK ]\r\n',
        b' * Stopping Mount network filesystems\x1b[74G[ OK ]\r\n',
        b' * Stopping Failsafe Boot Delay\x1b[74G[ OK ]\r\n',
        b' * Starting System V initialisation compatibility\x1b[74G[ OK ]\r\n',
        b' * Starting configure virtual network devices\x1b[74G[ OK ]\r\n',
        b' * Stopping System V initialisation compatibility\x1b[74G[ OK ]\r\n',
        b' * Starting System V runlevel compatibility\x1b[74G[ OK ]\r\n',
        b' * Starting xinetd daemon\x1b[74G[ OK ]\r\n',
        b' * Starting save kernel messages\x1b[74G[ OK ]\r\n',
        b' * Starting ISC DHCP IPv4 server\x1b[74G[ OK ]\r\n',
        b' * Starting regular background program processing daemon\x1b[74G[ OK ]\r\n',
        b' * Stopping ISC DHCP IPv6 server\x1b[74G[ OK ]\r\n',
        b' * Stopping libvirt daemon\x1b[74G[ OK ]\r\n',
        b' * Stopping save kernel messages\x1b[74G[ OK ]\r\n',
        b' * Starting ISC DHCP IPv4 server\x1b[74G[ OK ]\r\n',
    ]

    #"jdm login:"

    #for line in test123:
        #print(type(line))
        #data.decode('utf-8').strip())
    #    print(line.decode('utf-8').strip())
    data = b' * Stopping System V runlevel compatibility\x1b[74G[ OK ]\r\n'
    print(repr(escape_ansi(line=data.decode().strip())))
    print(escape_ansi(line=data.decode().strip()) == '* Stopping System V runlevel compatibility[ OK ]')
    #print('* Stopping System V runlevel compatibility[ OK ]' == 'Stopping System V runlevel compatibility')
    #print('* Stopping System V runlevel compatibility[ OK ]' == '* Stopping System V runlevel compatibility[ OK ]')
    #print('* Stopping System V runlevel compatibility[ OK ]' == '* Stopping System V runlevel compatibility[ OK ]')
