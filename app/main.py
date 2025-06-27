from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.api.v1 import items, matching
from app.routers import user_router

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
def health_check():
    return {"status": "healthy", "message": "Service is running"}


# Register API routes
app.include_router(items.router)
app.include_router(user_router, prefix="/api/v1")
app.include_router(matching.router, prefix="/api/v1")
