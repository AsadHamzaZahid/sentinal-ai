# Model artifacts

Layout: `models/<engine>/<version>/` containing the model file(s) and `metadata.json`.

Rules
- Never overwrite a released version. New model = new version folder.
- Every version has a filled-in `metadata.json` (data, metrics, threshold, features, limitations).
- `configs/models.yaml` selects the active version per engine.
- Large binaries: if a model is much bigger than ~10 MB, host it externally and download at startup.
