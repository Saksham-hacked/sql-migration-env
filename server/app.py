# server package
import uvicorn
from fastapi import FastAPI

app = FastAPI(title="SQL Migration Env")

@app.get("/")
def root():
    return {"status": "ok", "message": "SQL Migration Env is running"}

def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)

if __name__ == "__main__":
    main()