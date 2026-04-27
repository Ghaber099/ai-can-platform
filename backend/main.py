from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import upload
from routes import analyze
from routes import vehicle
from routes import dbc


app = FastAPI(
    title="AI CAN Platform",
    description="AI-powered CAN log analysis and DBC decoding platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(vehicle.router)
app.include_router(dbc.router)


@app.get("/")
def home():
    return {
        "message": "AI CAN Platform is running",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}