FROM ubuntu/apache2
RUN apt update &&  apt -y upgrade && apt -y install subversion libapache2-mod-svn && mkdir /svn && cd /svn &&  \
    chown -R www-data:www-data /svn && chmod -R 755 /svn && a2enmod dav_svn &&  \
    htpasswd -b -c /etc/svnusers.htpasswd electric 2fast2quick

EXPOSE 80 443 3690