from flask import Flask, render_template, jsonify, request, redirect, session, url_for, abort
import requests
import os
import secrets
from dotenv import load_dotenv
from datetime import datetime
import cocktail_scraper.dependencies_parser
from cocktail_scraper.scraper import scrap_data
from cocktail_scraper.data_processor import process_data
from cocktail_scraper.translator import generate_cic
from pprint import pprint
from flask_caching import Cache

load_dotenv() 

app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']

cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_THRESHOLD': 100, # Max size
    'CACHE_DEFAULT_TIMEOUT': 3600}) # Stores for 1 hour
cache.init_app(app)

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
    return render_template('about.html')

@app.route('/generate', methods=['POST'])
def generate():
    # Get form data
    repo_url = request.form.get('repo_url')
    github_token = request.form.get('github_token')

    session['github_token'] = github_token
    
    # Validate inputs
    if not repo_url or not github_token:
        return "Missing required fields", 400
    
    # Process data
    try:
        results = generate_repo_cic(repo_url, github_token)
        # Generate unique ID and store results
        result_id = secrets.token_hex(8)
        cache.set(result_id, results)
        
        # Redirect with ID instead of full data
        return redirect(url_for('results', result_id=result_id))
    
    except Exception as e:
        print(f"Error generating results: {str(e)}")
        return "Error processing request", 500

@app.route('/results')
def results():
    result_id = request.args.get('result_id')
    results = cache.get(result_id) if result_id else None

    if not results:
        # Redirect if no results
        return redirect(url_for('index'))
    
    try:
        return render_template('results.html', 
                           data={"cocktail": results["cic_data"]})
        
    except Exception as e:
        print(f"Error loading results: {str(e)}")
        return redirect(url_for('homepage'))

def generate_repo_cic(repo_url, github_token):
    repo_data = scrap_data(repo_url,github_token)
    print("SCRAPER:\n")
    print(repo_data)

    processed_data = process_data(repo_data)
    print("PROCESSOR:\n")
    print(processed_data)

    if len(processed_data) == 1:
        cic = generate_cic(processed_data[0])
        print("TRANSLATOR:\n")
        print(cic)
    else:
        print("Error: Fetched multiple repos somehow")

    results = {
        "scraper_data" : repo_data,
        "processor_data" : processed_data,
        "cic_data" : cic 
    }

    return results

if __name__ == '__main__':
    app.run(port=8000, debug=True)