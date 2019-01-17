deploy_use_case:
  cmd.run:
    - name: ansible-playbook telnet_junos_get_config/{{ pillar['playbook'] }}
    - cwd: /root/junos-automation-with-ansible
