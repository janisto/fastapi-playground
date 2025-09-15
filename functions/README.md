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

For a detailed, end-to-end infrastructure and IAM setup (APIs, roles, environment variables, Cloud Build integration, Functions vs Cloud Run guidance) see: [`GCP.md`](../GCP.md).
