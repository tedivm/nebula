#!/usr/bin/env python3

import os
import yaml

if 'SETTINGS' in os.environ:
    with open(os.environ['SETTINGS'], 'r') as stream:
        settings = yaml.load(stream)
        print(settings['postgres']['host'])
