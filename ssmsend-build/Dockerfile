FROM registry.hub.docker.com/library/centos:7

RUN yum update -y
# TODO remove openssl after it is made an explicit dependency via https://github.com/apel/ssm/issues/158 
# EPEL is needed for python-dirq
RUN yum install -y openssl epel-release
# UMD repo needed for python-argo-ams-library so APEL ssmsend can use AMS
RUN yum install -y https://repository.egi.eu/sw/production/umd/4/centos7/x86_64/updates/umd-release-4.1.3-1.el7.centos.noarch.rpm
# because UMD repo does not use HTTPS for GPG key
RUN rpm --import https://repository.egi.eu/sw/production/umd/UMD-RPM-PGP-KEY
RUN yum install -y python-dirq python-argo-ams-library https://github.com/apel/ssm/releases/download/3.2.0-1/apel-ssm-3.2.0-1.el7.noarch.rpm
RUN yum clean all

