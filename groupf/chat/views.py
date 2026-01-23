from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Placeholder for chat views (since consultation app handles most chat logic currently)
def index(request):
    return render(request, 'index.html') # Default placeholder
