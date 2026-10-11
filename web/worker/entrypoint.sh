#!/bin/sh
set -e
export PYTHONPATH=$(pwd):$PYTHONPATH
exec python src/main.py
