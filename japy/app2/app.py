# Import flask module
from flask import Flask
 
app = Flask(__name__)
 
@app.route('/')
def index():
    return 'Hello to Python App P1 - (Applocatonm 2)!'
 

@app.route('/p1')
def index_1():
    f = open("/app/app.py", "r")
    return f.read()


# main driver function
if __name__ == "__main__":
    app.run()