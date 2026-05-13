# SIA V2

Clean rebuild of the SIA mood bar-o-meter project.

## Server run

1. Create a virtual environment
2. Install dependencies from `requirements-server.txt`
3. Set `DATABASE_URL`
4. Run:

```bash
uvicorn server.main:app --reload
```
