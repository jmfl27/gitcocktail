from flask import Flask, render_template, flash, jsonify, request, redirect, session, url_for, abort
import requests
import os
import secrets
from dotenv import load_dotenv
from datetime import datetime
import base64
import cocktail_scraper.dependencies_parser
from cocktail_scraper.scraper import scrap_data
from cocktail_scraper.data_processor import process_data
from cocktail_scraper.translator import generate_cic, generate_graph_dot
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
        flash('Missing one or more required fields, please insert them.', 'error')
        return redirect(url_for('homepage'))  # Redirect to homepage
    
    # Process data
    try:
        results = generate_repo_cic(repo_url, github_token)

        # GitHub API returned an error
        if type(results) == tuple:
            print('AN API ERROR WAS FOUND: ' + str(results))
            # Show user what error ocurred:
            if results[1] == 404:
                flash('The repository that you requested is either not available or you do not have '
                'the required permissions to access it.\nPlease make sure that your personal access token ' \
                'is correctly set up and/or that the repository is public and available.', 'error')
                return redirect(url_for('homepage'))  # Redirect to homepage
            elif results[1] == 403 or results[1] == 401:
                flash('Your personal access token may have been incorrectly set up, expired or you may have typed it incorrectly.\n' \
                'Please make sure that your personal access token:\n -  is correctly set up;\n - is still valid;\n'
                '- was correctly typed in.', 'error')
                return redirect(url_for('homepage'))
            elif results[1] == 901:
                flash('It seems that multiple repositories were fetched at once, intstead of only one.\n' \
                'Please try again later.')
        else:
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
                           data={"cocktail": results["cic_data"]}, result_id=result_id)
        
    except Exception as e:
        print(f"Error loading results: {str(e)}")
        return redirect(url_for('homepage'))

def generate_repo_cic(repo_url, github_token):
    repo_data = scrap_data(repo_url,github_token)
    
    # GitHub API Error
    if type(repo_data) == tuple:
        print('GitHub API Error: ' + str(repo_data))
        return repo_data
    else:
        # GitHub API fetching success; proceed with CIC generation
        print("SCRAPER:\n")
        print(repo_data)

        processed_data = process_data([repo_data])
        print("PROCESSOR:\n")
        print(processed_data)

        if len(processed_data) == 1:
            cic = generate_cic(processed_data[0])
            print("TRANSLATOR:\n")
            print(cic)
        else:
            # Multiple repos error treatement (just to be safe)
            print("Error: Fetched multiple repos somehow")
            return (('Error',901))

        results = {
            "scraper_data" : repo_data,
            "processor_data" : processed_data,
            "cic_data" : cic 
        }

        return results

@app.route('/graph_data')
def graph_data():
    # Get the cache ID of the requested CIC data
    result_id = request.args.get('result_id')
    if not result_id:
        return jsonify({"error": "No result_id provided"}), 400

    # Get the CIC data from the cache
    results = cache.get(result_id)
    if not results:
        return jsonify({"error": "No results found"}), 404
    cic_data = results["cic_data"]

    # Generate the GraphViz graph of the CIC
    dot = generate_graph_dot(cic_data["name"],cic_data["cic"])

    # .source gets the DOT string for the browser to genarate the graph
    return jsonify({'dot': dot.source})

if __name__ == '__main__':
    app.run(port=8000, debug=True)