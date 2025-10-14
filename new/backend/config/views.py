from django.shortcuts import render
from django.conf import settings
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def serve_frontend(request, path=""):
    """
    Serve the React frontend for all non-API routes.
    This allows React Router to handle client-side routing.
    """
    # Get the path to the built React app (FE folder)
    frontend_dir = BASE_DIR.parent.parent / "FE" / "dist"
    index_file = frontend_dir / "index.html"
    
    # If the index.html file doesn't exist, return a 404
    if not index_file.exists():
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound("Frontend not found. Please build the React app.")
    
    # Read and serve the index.html file
    content = index_file.read_text(encoding='utf-8')
    
    from django.http import HttpResponse
    response = HttpResponse(content, content_type='text/html')
    return response
