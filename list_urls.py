
import os
import django
from django.urls import get_resolver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myfitnessbuddy_backend.settings')
django.setup()

def list_urls(lis, prefix=''):
    for entry in lis:
        if hasattr(entry, 'url_patterns'):
            list_urls(entry.url_patterns, prefix + entry.pattern.regex.pattern.replace('^', ''))
        else:
            print(f"{prefix}{entry.pattern.regex.pattern.replace('^', '')} -> {entry.callback}")

list_urls(get_resolver().url_patterns)
