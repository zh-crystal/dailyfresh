#!/bin/bash
python manage.py celery worker --loglevel=info
