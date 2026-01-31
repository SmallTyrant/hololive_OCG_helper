#!/usr/bin/env bash
set -euo pipefail

PNG="app/app_icon.png"

flet pack app/main.py --icon "$PNG"
