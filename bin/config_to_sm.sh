#!/usr/bin/env bash

# Get real directory in case of symlink
if [[ -L "${BASH_SOURCE[0]}" ]]
then
  DIR="$( cd "$( dirname $( readlink "${BASH_SOURCE[0]}" ) )" && pwd )"
else
  DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
fi

source $DIR/../env/bin/activate
export FLASK_APP=$DIR/../nebula/nebula.py

flask config_to_aws_sm $1 $2
