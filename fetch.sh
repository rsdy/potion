#!/bin/sh
cd $(dirname $0)
source env/bin/activate
PYTHONPATH=$(pwd) python potion/sources/feed.py
