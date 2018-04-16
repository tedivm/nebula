# Nebula

The Nebula project lets users manage their own machines on AWS utilizing profiles defined by your Ops team.

![Nebula Dashboard](/docs/images/server_listing.png)

## Why?

In an organization that wants to give its developers and researchers access to AWS instances the typical process involves creating IAM roles, adding new IAM users, and then training those users on the AWS Console or providing them with command line tools. This can be burdensome to say the least.

The Nebula dashboard integrates into an organization's existing LDAP structure without the need for new IAM users. Nebula provides a system where admins can define different profiles (including the `AMI` and instance `userdata`) that users can then launch and manage on their own. Users are given the tools to monitor the costs of their instances, such as alerts when they pass certain thresholds, and can even schedule instance shutdown in advance.

Nebula also saves the Ops team from having to deal with SSH keys by letting users manage them on their own.

## Documentation

If you're looking for the documentation look no further than the [Nebula Wiki](https://github.com/tedivm/nebula/wiki).


## Features

### LDAP Integration

Nebula uses LDAP as its user database.


### Full Instance Control

Users have full control over the Instance Type they launch, with a breakdown of the different features (VCPU, Memory, GPUs) available right in the launch menu.

### Multiple Availability Zone Support

Nebula supports the ability to specify multiple subnets that it can launch into. When instances of a particular type are unavailable in one (the dreaded `INSUFFICIENT_CAPACITY` error) it will continue trying in other subnets until it either launches the instances or runs out of subnets.

### Instance Blacklist

Nebula admins have the ability to blacklist instances they do not want their users to launch.


### Scheduled Shutdowns

Instances can be given a specific shutdown time. This can be used as a failsafe to prevent machines from being left up or to shutdown machines after running experiments or long running tasks.


### Transparent Pricing

Both the User and Amin Dashboards contain to the second cost for all running instances and the volumes of every instance. All users can easily sort by cost to see which of their instances have cost the most money.


### SSH Key Management and OpenSSH Integration

Users can add and remove their own public ssh keys on their own. Admins also have the ability to view, add, and remove User keys.

A provided [integration script](https://github.com/tedivm/nebula/wiki/OpenSSH-Integration) lets OpenSSH pull from this list of keys directly.


### Web API for Continuous Deployment

Launch profiles can have their AMI updated automated using the [Profiles API](https://github.com/tedivm/nebula/wiki/Profile-API). This allows organizations which have automated their build process to always provide the most up to date version of the AMI available. This API can also be used to create and remove profiles.


### Autoupdating Instance Metadata

Instance data is pulled from the [ec2details API](https://tedivm.github.io/ec2details/), so new instances and updates pricing information are available to Nebula without having to update the project itself. The ec2details API itself is populated directly from the [AWS Bulk API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-ppslong.html).


### AWS Cost Explorer Integration

Nebula makes extensive use of resource tags. Every Instance, ENI (network device), and EBS volume gets tagged with the User, Profile, and [Site Name](https://github.com/tedivm/nebula/wiki/Configuration#general). This allows AWS admins to get per penny billing reports on exactly what money is being spent by who on their Nebula install.

### Docker Containers

Nebula makes it easy to [install with docker](https://github.com/tedivm/nebula/wiki/Install-With-Docker), with its two images hosted on Docker Hub ([Nebula App](https://hub.docker.com/r/tedivm/nebula_app/) and [Nebula Worker](https://hub.docker.com/r/tedivm/nebula_worker/)).

### Simple Development Environment

Nebula has an easy to use [development environment](https://github.com/tedivm/nebula/wiki/Install-Development-Environment) that also makes for a great demo.
