#!/bin/bash

go mod vendor
make

rm -r datas/*
rm -r tmp/*

chmod +x scripts/run-script.py
chmod +x scripts/plot-gpu-cdf.py
python3 scripts/run-script.py
python3 scripts/plot-gpu-cdf.py tmp/