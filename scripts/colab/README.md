Colab run instructions for smart_meeting_assistant Colab service

Quick steps:

1. Clone this repository (or push your changes to GitHub and clone in Colab).
2. Install dependencies:
   ```bash
   pip install -r scripts/colab/requirements-colab.txt
   ```
3. Set tokens:
   - `NGROK_AUTHTOKEN` (from ngrok dashboard)
   - `SUMMARY_REMOTE_AUTH` (secure token shared with gateway)

4. Start the service:
   ```bash
   python -u scripts/colab/colab_entry.py
   ```

Notes:
- `NGROK_AUTHTOKEN` is used to create a public tunnel and is different from the application `SUMMARY_REMOTE_AUTH` token.
- Keep `SUMMARY_REMOTE_AUTH` secret; do not commit it to a public repository.
- This README is a minimal quickstart; use `colab_run_template.ipynb` for an interactive Colab experience.
