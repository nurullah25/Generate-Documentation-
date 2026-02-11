# CORE DocGen

A Streamlit app that generates ERP documentation PDFs from form input, with attachments support.

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
python -m streamlit run app.py
