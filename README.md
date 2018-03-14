# Nebula Dashboard

The nebula dashboard allows users to launch and manage servers from a list of predefined profiles setup by their site administrator, giving users control over their machines.

This application has two parts- a web application and a backend worker that handled running user commands (such as launching the server).

The majority of data is saved as tags on the instances themselves, with postgres being used purely to store server profiles.

Authentication is handled via an ldap server.

## Requirements

* Python3
* virtualenv
* postgres
* rabbitmq

## Development Environment

This project includes a `docker-compose.yaml` file which can be used to launch the development environment.

Before running `docker-compose up --build` some configuration is needed-

1. Edit the AWS section of the configuration file in `./docker/app/SETTINGS` to add your `subnet-id` and `Security Group`.
2. On your host machine run `aws configure` to create the AWS credentials file, which will be mounted as a volume in the docker containers.

The docker environment creates an LDAP backend specific to this installation with two accounts built in, `admin` and `user` (with the passwords `admin` and `user`).


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
