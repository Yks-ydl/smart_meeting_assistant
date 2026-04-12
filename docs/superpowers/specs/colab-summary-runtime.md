# Colab Summary Runtime Guide

## Purpose

Run high-memory summary inference on Colab and connect local gateway to that remote service.

## Files

- scripts/colab/colab_entry.py
- scripts/colab/colab_summary_service.py
- scripts/colab/colab_model_runtime.py
- scripts/colab/colab_security.py
- scripts/colab/colab_tunnel.py
- scripts/colab/requirements-colab.txt

## Colab Steps

1. Install dependencies.

   pip install -r scripts/colab/requirements-colab.txt

2. Set auth token for remote service.

   export COLAB_SUMMARY_AUTH_TOKEN=your_token

3. Start service and tunnel.

   python -m scripts.colab.colab_entry

4. Copy printed public URL.

   [ColabEntry] set SUMMARY_SERVICE_URL to: https://xxxx.ngrok-free.app/api/v1/summary/generate

## Local Gateway Steps

1. Configure remote summary mode in .env.

   SUMMARY_EXECUTION_MODE=remote
   SUMMARY_SERVICE_URL=https://xxxx.ngrok-free.app/api/v1/summary/generate
   SUMMARY_REMOTE_AUTH_HEADER=Authorization
   SUMMARY_REMOTE_AUTH_SCHEME=Bearer
   SUMMARY_REMOTE_AUTH_TOKEN=your_token
   SUMMARY_REMOTE_TIMEOUT_SEC=90
   SUMMARY_REMOTE_RETRIES=1

2. Start local services.

   python start_all.py

## Validation

1. Health check from local machine.

   GET https://xxxx.ngrok-free.app/health

2. Trigger meeting end in frontend and confirm summary is returned.

3. If remote summary fails, inspect gateway log entries with attempt and URL.
