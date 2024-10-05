1) Ensure system is set up properly:
   1) Run `lsblk` to determine which drive should be mounted as the SVN filesystem
   2) Run `sudo mount /dev/<drive name> ~/svn`
2) Install Docker
3) Port Dockerfile, dav_svn.conf, and svnusers.authz file onto server
scp -i ~/Documents/LHR/svn/proto_svn.pem /home/max/Documents/LHR/svn/dav_svn.conf /home/max/Documents/LHR/svn/Dockerfile /home/max/Documents/LHR/svn/svnusers.authz ubuntu@svn.servebeer.com:~
4) mkdir svn && touch svnusers.htpasswd
5) sudo docker build -t svn-server .
6) sudo docker run -m 200m -p 80:80 -p 3690:3690 -v ~/svn:/svn -v ~/svnusers.htpasswd:/etc/svnusers.htpasswd -v ~/svnusers.authz:/etc/svnusers.authz -v ~/dav_svn.conf:/etc/apache2/mods-enabled/dav_svn.conf svn-server
7) sudo docker exec -it $(sudo docker container ls | grep "svn-server" | grep -oP "^\S+") /bin/bash
8) svnadmin create /svn/LHRe
9) Edit pre-commit hook to include message requirements
10) Use roster_additions.sh script
11) svnserve -d
12) Log out of container, sudo chown -R www-data:www-data ~/svn/LHRe/ && sudo chmod -R g+ws ~/svn/LHRe
13) On local: svn co --username <admin_user> --password <XXXX> http://svn.servebeer.com/svn/LHRe
14) Create folders/setup for downstream access

In case of reboot:
Refer to step 1 regarding mounting of filesystem. Assuming filesystem is remounted, repeat steps 6, 7, and 11