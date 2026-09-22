# Copy everything in this file into your PythonAnywhere WSGI file (Web tab > WSGI configuration file).
# Replace YOURUSERNAME, the API key and the SECRET_KEY text, then Save and click Reload.
import sys, os

path = '/home/YOURUSERNAME/conrad-app'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['ANTHROPIC_API_KEY'] = 'PASTE-YOUR-ANTHROPIC-KEY-HERE'
os.environ['SECRET_KEY'] = 'type-a-long-random-text-here-at-least-30-characters'
os.environ['CONRAD_DB'] = '/home/YOURUSERNAME/conrad-app/conrad.db'
os.environ['COOKIE_SECURE'] = '1'

from server import app as application
