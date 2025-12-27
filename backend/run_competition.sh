#!/bin/bash
# Run competitive objective generation with virtual environment

cd "$(dirname "$0")"
source venv/bin/activate
python3 generate_objectives_competitive.py
