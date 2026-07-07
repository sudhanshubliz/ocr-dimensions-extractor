# CAD Dimension Extractor Cloud Deployment

This folder is a deployable Streamlit UI for the CAD dimension extraction engine.

## Recommended Free Options

1. Streamlit Community Cloud
   - Best first option for a Streamlit app.
   - Connect the GitHub repo and set the main file to `app.py`.
   - Uses `requirements.txt` and `packages.txt`.

2. Hugging Face Spaces
   - Good for ML demos and later PaddleOCR/Qwen experiments.
   - Create a Streamlit Space and upload this folder.
   - Uses `requirements.txt` and `packages.txt`.

3. Render Free Web Service
   - Works for Python web services, but free instances are not production-grade and may sleep.
   - Uses `render.yaml` or `Procfile`.

## Local Run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Cloud Notes

- Default OCR mode is `auto`, which falls back to cropped Tesseract if PaddleOCR is not installed.
- For free cloud, keep `--vlm-verifier disabled` unless you configure a provider/model.
- Do not upload sensitive CAD files to public demo deployments.
- Free instances are suitable for demos, not production inspection workflows.

## PaddleOCR Option

For a heavier PaddleOCR build, use:

```bash
python -m pip install -r requirements-paddle.txt
```

This may exceed free-tier memory/boot limits on smaller platforms.
