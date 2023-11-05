1) Install Docker
2) Port Dockerfile, dav_svn.conf, and svnusers.authz file onto server
scp -i ~/Documents/LHR/svn/proto_svn.pem /home/max/Documents/LHR/svn/dav_svn.conf /home/max/Documents/LHR/svn/Dockerfile /home/max/Documents/LHR/svn/svnusers.authz ubuntu@ec2-3-141-198-156.us-east-2.compute.amazonaws.com:~
3) mkdir svn && touch svnusers.htpasswd
4) sudo docker build -t svn-server .
5) sudo docker run -p 80:80 -p 3690:3690 -v ~/svn:/svn -v ~/svnusers.htpasswd:/etc/svnusers.htpasswd -v ~/svnusers.authz:/etc/svnusers.authz -v ~/dav_svn.conf:/etc/apache2/mods-enabled/dav_svn.conf svn-server
6) sudo docker exec -it $(sudo docker container ls | grep "svn-server" | grep -oP "^\S+") /bin/bash