#!/usr/bin/env bash

buildUi() {
    echo "#########################################################################"
    echo "Build UI container"
    echo "#########################################################################"
    host=$OPTARG
    mkdir -p /tmp/cso-ui/log
    docker build -t cso-ui .
    docker run -d --rm -v /tmp/cso-ui:/tmp/cso-ui -p 8670:8670 --name cso-ui cso-ui
}

buildGitlab() {
    echo "#########################################################################"
    echo "Build Gitlab container"
    echo "#########################################################################"
    host=$OPTARG
    docker build -t cso-ui .
    docker run -d --rm -v /tmp/cso-ui:/tmp/cso-ui -p 8670:8670 --name cso-ui cso-ui
    docker run --detach \
       --hostname "${host}" \
       --name gitlab \
       --restart always \
       --volume /srv/gitlab/config:/etc/gitlab \
       --volume /srv/gitlab/logs:/tmp/gitlab/logs \
       --volume /srv/gitlab/data:/tmp/gitlab/data \
       --publish 9080:9080 --publish 3022:22 --publish 9443:9443 \
       --env GITLAB_OMNIBUS_CONFIG="external_url 'http://${host}:9080'; gitlab_rails['gitlab_shell_ssh_port']=3022; gitlab_rails['initial_root_password']='juniper123'"" \
       gitlab/gitlab-ce:latest
}

cleanup() {
    echo "#########################################################################"
    echo "Cleanup environment"
    echo "#########################################################################"

    if [[ ${VERSION} == "18.04" ]]
    then
        service apparmor teardown
        echo "#########################################################################"
        echo "Stopping container"
        echo "#########################################################################"
        docker container stop $(docker container ps -a -q)
        docker container rm $(docker ps -a -f status=exited -q)
        docker rmi $(docker images -q)
        docker system prune --force --volumes
        systemctl restart apparmor
    elif [[ ${VERSION} == "16.04" ]]
    then
        docker container stop $(docker container ps -a -q)
        docker container rm $(docker ps -a -f status=exited -q)
        docker rmi $(docker images -q)
        docker system prune --force --volumes
    fi
    rm -Rf /tmp/cso-ui
    rm -Rf /srv/gitlab
}

cleanupUi() {
    if [[ ${VERSION} == "18.04" ]]
    then
        service apparmor teardown
        echo "#########################################################################"
        echo "Stopping container"
        echo "#########################################################################"
        docker container stop cso-ui
        #docker container rm cso-ui
        docker images -a | grep "cso-ui" | awk '{print $3}' | xargs docker rmi
        systemctl restart apparmor
    elif [[ ${VERSION} == "16.04" ]]
    then
        echo "#########################################################################"
        echo "Stopping container"
        echo "#########################################################################"
        docker container stop cso-ui
        #docker container rm cso-ui
        docker images -a | grep "cso-ui" | awk '{print $3}' | xargs docker rmi
    fi
    rm -Rf /tmp/cso-ui
}

cleanupGitlab() {
    if [[ ${VERSION} == "18.04" ]]
    then
        service apparmor teardown
        echo "#########################################################################"
        echo "Stopping container"
        echo "#########################################################################"
        docker container stop gitlab
        docker container rm gitlab
        docker images -a | grep "gitlab/gitlab-ce" | awk '{print $3}' | xargs docker rmi
        systemctl restart apparmor
    elif [[ ${VERSION} == "16.04" ]]
    then
        echo "#########################################################################"
        echo "Stopping container"
        echo "#########################################################################"
        docker container stop gitlab
        docker container rm gitlab
        docker images -a | grep "gitlab/gitlab-ce" | awk '{print $3}' | xargs docker rmi
    fi
    rm -Rf /srv/gitlab
}

import() {
    echo "#########################################################################"
    echo "Import repository"
    echo "#########################################################################"
    host=${OPTARG[0]}
    file=${OPTARG[1]}
    echo 'grant_type=password&username=root&password=juniper123' > auth.txt
    curl --data "@auth.txt" --request POST http://${host}:9080/oauth/token > token.json

    if [[ ${VERSION} == "18.04" ]]
    then
        TOKEN=$(/snap/bin/yq r ./token.json access_token)
    elif [[ ${VERSION} == "16.04" ]]
    then
        TOKEN=$(yq r ./token.json access_token)
    fi

    curl --request POST --header "Authorization: Bearer ${TOKEN}" \
       --form path="cso_ops" \
       --form "file=@"${file} http://${host}:9080/api/v4/projects/import
    echo
    curl --request POST --header "Authorization: Bearer ${TOKEN}" \
       -F "title=cso-ui" \
       -F "key=$(cat config/ssh/cso-ui.pub)" http://${host}:9080/api/v4/user/keys
    echo
}

prepare() {
    echo "#########################################################################"
    echo "Prepare environment"
    echo "#########################################################################"
    host=${OPTARG[0]}
    ws=${OPTARG[1]}

    if [[ ${VERSION} == "18.04" ]]
    then
        apt-get update
        apt-get install curl git -y
        apt-get install apt-transport-https ca-certificates curl software-properties-common -y
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
        add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
        apt-get update
        apt-get install docker-ce -y
        snap install yq
        /snap/bin/yq w --inplace config/config.yml ws_client_ip ${ws}
        /snap/bin/yq w --inplace config/config.yml git_host ${host}
    elif [[ ${VERSION} == "16.04" ]]
    then
        add-apt-repository ppa:rmescandon/yq -y
        apt-get update
        apt-get install curl git yq --allow-unauthenticated -y
        yq w --inplace config/config.yml ws_client_ip ${ws}
        yq w --inplace config/config.yml git_host ${host}
    fi

    mkdir -p /tmp/cso-ui/log

cat <<- EOF > config/ssh/config
    Host ${host}
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    IdentityFile /root/.ssh/cso-ui
EOF
}

usage() {
    echo "Usage:"
    echo " $0 [ --prepare <host_ip> <ws_ip>]"
    echo " $0 [ --build=<host_ip> ]"
    echo " $0 [ --buildUi=<host_ip> ]"
    echo " $0 [ --buildGitlab=<host_ip> ]"
    echo " $0 [ --cleanup ]"
    echo " $0 [ --cleanupUi ]"
    echo " $0 [ --cleanupGitlab ]"
    echo " $0 [ --import <host_ip> <file> ]"
    echo " $0 [ --all <host_ip> <file> ]"
    echo " $0 [ --help | -h ]"
    echo
}

# set defaults
all=""
build=""
buildUi=""
buildGitlab=""
import=""
prepare=""
VERSION=`lsb_release -rs`
i=$(($# + 1))
declare -A longoptspec
longoptspec=( [all]=2 [build]=1 [buildUi]=1 [buildGitlab]=1 [import]=2 [prepare]=2 )
optspec=":h-:"

while getopts "$optspec" opt; do
    while true; do
        case "${opt}" in
            -)
                if [[ ${OPTARG} =~ .*=.* ]]
                then
                    opt=${OPTARG/=*/}
                    ((${#opt} <= 1)) && {
                        echo "Syntax error: Invalid long option '$opt'" >&2
                        exit 2
                    }
                    if (($((longoptspec[$opt])) != 1))
                    then
                        echo "Syntax error: Option '$opt' does not support this syntax." >&2
                        exit 2
                    fi
                    OPTARG=${OPTARG#*=}
                else
                    opt="$OPTARG"
                    ((${#opt} <= 1)) && {
                        echo "Syntax error: Invalid long option '$opt'" >&2
                        exit 2
                    }
                    OPTARG=(${@:OPTIND:$((longoptspec[$opt]))})
                    ((OPTIND+=longoptspec[$opt]))
                    echo $OPTIND
                    ((OPTIND > i)) && {
                        echo "Syntax error: Not all required arguments for option '$opt' are given." >&2
                        exit 3
                    }
                fi
                continue
                ;;
            a|all)
                cleanup
                prepare
                buildUi
                buildGitlab
                echo "#########################################################################"
                echo "Need to run import repository to gitlab with --import=<host_ip> manually"
                echo "#########################################################################"
                ;;
            b|build)
                buildUi
                buildGitlab
                ;;
            buildUi)
                buildUi
                ;;
            buildGitlab)
                buildGitlab
                ;;
            c|cleanup)
                cleanup
                ;;
            cleanupUi)
                cleanupUi
                ;;
            cleanupGitlab)
                cleanupGitlab
                ;;
            i|import)
                import
                ;;
            h|help)
                usage
                exit 0
                ;;
            p|prepare)
                prepare
                ;;
            ?)
                echo "Syntax error: Unknown short option '$OPTARG'" >&2
                exit 2
                ;;
            *)
                echo "Syntax error: Unknown long option '$opt'" >&2
                exit 2
                ;;
        esac
    break; done
done

#echo "First non-option-argument (if exists): ${!OPTIND-}"