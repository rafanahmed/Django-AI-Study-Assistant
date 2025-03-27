from django.shortcuts import render

def home_view(request):
    """
    Render the home page
    """
    return render(request, 'base/base.html')

def study_sessions_view(request):
    """
    Render the study sessions page
    """
    return render(request, 'base/study_sessions.html')

def resources_view(request):
    """
    Render the resources page
    """
    return render(request, 'base/resources.html')

def about_view(request):
    """
    Render the about page
    """
    return render(request, 'base/about.html')