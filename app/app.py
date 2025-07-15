from flask import Flask, render_template, jsonify, request, redirect
import requests
from datetime import datetime

app = Flask(__name__)

#render_template('homepage.html', date={"date": formated_iso_date})

# System Date
current_date = datetime.now()
formated_iso_date = current_date.strftime('%Y-%m-%dT%H:%M:%S')

# Página inicial
@app.route('/', methods=['GET'])
def homepage():
    return render_template('homepage.html')

@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')  # make sure you have about.html

if __name__ == '__main__':
    app.run(port=8000, debug=True)