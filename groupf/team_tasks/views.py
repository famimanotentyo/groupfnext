from django.http import HttpResponse

# Deprecated. Views have been moved to respective apps.
def index(request):
    return HttpResponse("This app has been refactored. Please use new URLs.")