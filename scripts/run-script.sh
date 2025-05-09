#!/bin/bash

go mod vendor
make

[ -d "datas" ] && rm -r datas/*
[ -d "tmp" ] && rm -r tmp/*

chmod +x scripts/run-script.py
chmod +x scripts/plot-gpu-cdf.py
python3 scripts/run-script.py
python3 scripts/plot-gpu-cdf.py tmp/