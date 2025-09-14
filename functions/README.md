# Firebase Cloud Functions

Run these commands to deploy:

```bash
cd functions
python3 -m venv venv
source venv/bin/activate 
pip3 install -r requirements.txt
export FUNCTIONS_DISCOVERY_TIMEOUT=30
firebase deploy --only functions
deactivate
```
