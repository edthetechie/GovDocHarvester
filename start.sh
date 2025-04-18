#!/bin/bash
# Install the required dependencies
pip install -r requirements.txt

# Start the app using Gunicorn
python -m gunicorn web_app:app