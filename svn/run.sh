#!/bin/bash

read -p "Enter server address: " server
scp -i ~/Documents/LHR/svn/proto_svn.pem /home/max/Documents/LHR/svn/dav_svn.conf /home/max/Documents/LHR/svn/Dockerfile /home/max/Documents/LHR/svn/svnusers.authz /home/max/Documents/LHR/svn/roster_additions.sh /home/max/Documents/LHR/svn/install_docker.sh ubuntu@$server:~
commands=()
while :
do
        read -n 1 -p "Install Docker? [Y/n] " docker_inst
        echo
        case $docker_inst in
                Y|y)
                        commands+=("sudo apt update && sudo apt -y upgrade")
                        commands+=("sudo apt-get install ca-certificates curl gnupg")
                        commands+=("sudo install -m 0755 -d /etc/apt/keyrings")
                        commands+=("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg")
                        commands+=("sudo chmod a+r /etc/apt/keyrings/docker.gpg")
                        commands+=("echo \
                          \"deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
                          \"$(. /etc/os-release && echo \"$VERSION_CODENAME\")\" stable\" | \
                          sudo tee /etc/apt/sources.list.d/docker.list > /dev/null")
                        commands+=("sudo apt-get update")
                        commands+=("sudo apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin")
                        break
                        ;;
                N|n)
                        break
                        ;;
                *)
                        echo -e "\nInvalid input, please try again.\n"
                        ;;
        esac
done
commands+=("mkdir svn && touch svnusers.htpasswd")
commands+=("sudo docker build -t svn-server .")
commands+=("sudo docker run -d -p 80:80 -p 3690:3690 -v ~/svn:/svn -v ~/svnusers.htpasswd:/etc/svnusers.htpasswd -v ~/svnusers.authz:/etc/svnusers.authz -v ~/dav_svn.conf:/etc/apache2/mods-enabled/dav_svn.conf --name svn_instance svn-server")
commands+=("sudo docker exec -i svn_instance /bin/bash < ./roster_additions.sh")
commands+=("sudo docker exec svn_instance svnadmin create /svn/LHRe")
commands+=("sudo docker exec svn_instance cp /svn/LHRe/hooks/pre-commit.tmpl /svn/LHRe/hooks/pre-commit")
commands+=("sudo docker exec svn_instance chmod +x /svn/LHRe/hooks/pre-commit")
commands+=("sudo docker attach svn_instance")

for i in "${commands[@]}"
do
        ssh -o StrictHostKeyChecking=no -i ~/Documents/LHR/svn/lhre_svn.pem ubuntu@$server $i
done
