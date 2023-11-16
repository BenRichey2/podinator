from flask import Flask

app = Flask("Podinator")

@app.route("/")
def hello_world():
    return "<p>Hello, Podinator!</p>"