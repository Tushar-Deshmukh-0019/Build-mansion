#!/bin/bash
# Retrain model on HF Spaces if model files are missing or incompatible
echo "=== Checking model files ==="
python -c "
import joblib, sys
try:
    d = joblib.load('model.sav')
    joblib.load('scaler.sav')
    print('Model files OK')
except Exception as e:
    print(f'Model load failed: {e}')
    print('Retraining...')
    import subprocess
    result = subprocess.run(['python', 'train_model.py'], capture_output=True, text=True)
    print(result.stdout[-500:] if result.stdout else '')
    print(result.stderr[-500:] if result.stderr else '')
    sys.exit(0)
"
