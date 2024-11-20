import sys, os

INTERP = os.path.expanduser("/home/YOUR_USERNAME/virtualenv/YOUR_APP_PATH/3.9/bin/python")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())

from app import app as application 