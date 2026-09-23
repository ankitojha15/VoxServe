from fastapi import FastAPI

app = FastAPI(title="VoxServe")

@app.get("/")
def root():
    return {"message":"VoxServe is running"}

@app.get("/health")
def health():
    return {"status":"ok"}