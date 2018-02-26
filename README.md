# Nebula Dashboard

The nebula dashboard allows users to launch and manage servers from a list of
predefined profiles setup by their site administrator, giving users control over
their machines.

This application has two parts- a web application and a backend worker that
handled running user commands (such as launching the server).

The majority of data is saved as tags on the instances themselves, with postgres
being used purely to store server profiles.

Authentication is handled via an ldap server.

## Requirements

* Python3
* virtualenv
* postgres
* rabbitmq

## Development Environment
To locally deploy the nebula dashboard for development purposes, you will need to setup:

1. Environment Variables
2. Vagrant Virtual Machine
3. AWS Credentials

### Environment Variables
Ensure that you have a copy of the `nebula/SETTINGS` file and modify the following lines:

* `LDAP_BIND_DN = 'uid=ldapbind,CN=users,DC=mm1,DC=ucoffice,DC=example'`: replace `ldapbind` with your username.
* `LDAP_BIND_PASSWORD = ''`: enter your password inside the empty string.

### Vagrant Virtual Machine
1. Navigate to the root of this project's directory and run `vagrant up` to create a virtual machine with the correct development environment.
2. SSH into the VM by running `vagrant ssh`
3. Set up AWS credentials (below) before continuing onto the next step.
4. Serve the Flask app locally by running `/vagrant/bin/devserve.sh`.
5. Visit the deployed version at 127.0.0.1:5000.

### AWS Credentials
Generate your personal AWS IAM access key ID and secret key to configre your [AWS credentials](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-config-files). Inside your Vagrant VM, execute the following:

 1. `sudo apt-get install awscli`
 2. `aws configure`
 3. Follow the instructions to enter your access key ID and secret key.

### Miscellaneous
* Log out of the SSH using `logout`.
* Shut down the machine using `vagrant halt`.
* In the scenario that you want to destroy (rather than shut down) a machine, use `vagrant destroy -f`.


# External API

An external API with the following endpoints is available to update certain settings. Requests sent to the API require a LDAP `username` and `password` to be sent in the request headers for authentication.

## Profiles

### List all profiles

The `GET` endpoint to list all profiles: `/api/profiles`.

Example usage: `curl -H "username: user" -H "password: pass" https://nebula.example/api/profiles`

### Create new profile

The `POST` endpoint to create a new profile: `/api/profiles`. A JSON object with the relevant profile data (name, ami, userdata) must be sent along with the request.

Example usage: `curl -H "Content-Type: application/json" -H "username: user" -H "password: pass" -X POST -d '{"name": "Engineering (deploy image builder)", "ami": "ami-ad29fcd", "userdata": "role=deploy"}' https://nebula.example/api/profiles`

### Update an existing profile

The `PUT` endpoint to update an existing profile: `/api/profiles/<profile_id>`. A JSON object with the relevant profile data (name, ami, userdata) must be sent along with the request.

Example usage: `curl -H "Content-Type: application/json" -H "username: user" -H "password: pass" -X PUT -d '{"name": "Engineering (deploy image builder)", "ami": "ami-ad29fcd", "userdata": "role=deploy"}' https://nebula.example/api/profiles`.

### Remove an existing profile

The `DELETE` endpoint to remove an existing profile: `/api/profiles/<profile_id>.

Example usage: `curl -H "username: user" -H "password: pass" -X DELETE https://nebula.example/api/profiles/1`.

### Errors

* If LDAP credentials are not provided, or the credentials are invalid, `401: Unauthorized`.
* If the wrong HTTP verb is used, `405: Method Not Allowed`.
* If JSON data is not properly encoded or sent, `400: Bad Request`.
* If attempting to edit or delete a profile that does not exist, `404: Not Found`.
