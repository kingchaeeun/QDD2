"""
Simple script to run the API server.
"""

if __name__ == "__main__":
    import uvicorn
    from quote_backend.config import API_HOST, API_PORT, API_DEBUG
    
    print(f"Starting Quote Detection Backend API server...")
    print(f"Host: {API_HOST}, Port: {API_PORT}, Debug: {API_DEBUG}")
    print(f"API Documentation: http://{API_HOST}:{API_PORT}/docs")
    
    uvicorn.run(
        "quote_backend.api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_DEBUG,
    )

