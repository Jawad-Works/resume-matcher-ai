from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.routers.api.v1 import items, matching
from app.routers import user_router
from app.database.models import Base
from app.database.database import engine, get_db

# Create DB tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection by executing a simple query
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


# Register API routes
app.include_router(items.router)
app.include_router(user_router, prefix="/api/v1")
app.include_router(matching.router, prefix="/api/v1")
