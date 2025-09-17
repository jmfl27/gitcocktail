import requests
import json
import os
import base64
import pprint
import re

# Loads the data.json file as a dictionary
def load_data_json():
    with open('cocktail_scraper/data.json') as json_data:
        data = json.load(json_data)
        json_data.close()

    return data

# Fetches the repo data through the GitHub API
def get_repo_data(repo_url, token=None):
    # Extract owner and repo name from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo_name = parts[-1]

    # Construct API URL
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

    # Headers for authentication
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Make a GET request to GitHub API
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        # Parse JSON response
        repo_data = response.json()
        return repo_data
    else:
        print(f"Error: Unable to fetch repository details (Status code {response.status_code}: {response.text})")
        return response.status_code

# Fetches the contents of the specified file from the specified repo through the GitHub API
def get_file_content(repo_url, path, token=None):
    print('Getting a file content....')
    # Extract owner and repo name from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo_name = parts[-1]

    # Construct API URL
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}"

    # Headers for authentication
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

     # Make a GET request to GitHub API
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        # If file size is over 1MB
        if data['content'] == "":
            raw_headers = headers.copy()
            raw_headers["Accept"] = "application/vnd.github.v3.raw"
            # Re-request with raw Accept header
            raw_response = requests.get(api_url, headers=raw_headers)
            if raw_response.status_code == 200:
                content = raw_response.text
            else:
                print(
                    f"Error: Unable to fetch large file content (Status code {raw_response.status_code}: {raw_response.text})"
                )
                return None
        else:
            content = base64.b64decode(data['content']).decode('utf-8')
        return content
    else:
        print(f"Error: Unable to fetch file content (Status code {response.status_code}: {response.text})")
        return None

# Fetches the languages identified in the specified repo through the GitHub API
def get_repo_languages(repo_url, token=None):
    # Extract owner and repo name from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo_name = parts[-1]

    # Construct API URL
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/languages"

    # Headers for authentication
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Make a GET request to GitHub API
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        # Parse JSON response
        repo_data = response.json()
        return repo_data
    else:
        print(f"Error: Unable to fetch repository languages (Status code {response.status_code}: {response.text})")
        return None

# Fetches the content of the README.md file of the specified repo through the GitHub API
def get_repo_readme(repo_url, token=None):
    # Extract owner and repo name from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo_name = parts[-1]

    # GitHub API endpoint for fetching README
    url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"

    # Headers for authentication
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Send GET request to the API
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # The content is Base64 encoded, so we need to decode it
        content = base64.b64decode(data['content']).decode('utf-8')

        return content
    else:
        return f"Error: Unable to fetch README. Status code {response.status_code}: {response.text}"

# Fetches all of the paths of the files present the specified repo through the GitHub API
def get_repo_files(repo_url, default_branch, token=None):
    # Extract owner and repo name from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo_name = parts[-1]

    # Headers for authentication
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    """
    # GitHub API endpoint for fetching repository information
    repo_api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

    # Make a GET request to fetch repository information
    repo_response = requests.get(repo_api_url, headers=headers)

    if repo_response.status_code != 200:
        return f"Error: Unable to fetch repository information. Status code: {repo_response.status_code}"

    # Get the default branch name
    default_branch = repo_response.json()['default_branch']
    """

    # GitHub API endpoint for fetching the repository tree
    tree_api_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{default_branch}?recursive=1"

    # Make a GET request to GitHub API for the tree
    tree_response = requests.get(tree_api_url, headers=headers)

    if tree_response.status_code == 200:
        # Parse JSON response
        repo_data = tree_response.json()

        # Extract path, type, and url for each item, handling missing keys
        filtered_data = []
        for item in repo_data.get('tree', []):
            filtered_item = {}
            if 'path' in item:
                filtered_item['path'] = item['path']
            if 'type' in item:
                filtered_item['type'] = item['type']
            if 'url' in item:
                filtered_item['url'] = item['url']

            # Only add the item if it has at least one of the desired keys
            if filtered_item:
                filtered_data.append(filtered_item)

        return filtered_data
    else:
        return f"Error: Unable to fetch the repository's file path data. Status code {tree_response.status_code}: {tree_response.text}"

# Fetches the name of the submodules used in the specified repo through a query request to the GitHub GraphQL API
def get_submodules(repo_url, token):
    # Extract owner and repo name from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]

    url = "https://api.github.com/graphql"
    headers = {}
    if token:  # Add token to header if it's provided
        headers["Authorization"] = f"Bearer {token}"

    # GraphQL query with pagination
    query = """
    query($owner: String!, $repo: String!) {
        repository(owner: $owner, name: $repo) {
            object(expression: "HEAD") {
                ... on Commit {
                    submodules(first: 100) {  # Add pagination
                        nodes {
                            name
                        }
                    }
                }
            }
        }
    }
    """
    variables = {"owner": owner, "repo": repo}
    response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)

    if response.status_code == 200:
        data = response.json()
        #pprint.pprint(data)  # Debugging: Print the full response

        # Safely extract submodules
        repository_data = data.get("data", {}).get("repository", {})
        if not repository_data:
            print("Repository not found or access denied.")
            return []

        commit_object = repository_data.get("object", {})
        if not commit_object:
            print("No commit found for the given repository.")
            return []

        submodules = commit_object.get("submodules", {}).get("nodes", [])
        return [submodule["name"] for submodule in submodules]
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return []
    
#  Split a dictionary of {file_type: [paths]} into batches
def split_into_batches(data, batch_size=100):
    all_paths = []
    for file_type, paths in data.items():
        for path in paths:
            all_paths.append((file_type, path))
    
    batches = []
    for i in range(0, len(all_paths), batch_size):
        batch = {}
        for (file_type, path) in all_paths[i:i+batch_size]:
            batch.setdefault(file_type, []).append(path)
        batches.append(batch)
    return batches

# Finds the path of all of the targeted dependency files present in the specified repo
def find_dependency_files(file_path_data,targets):
    target_files = {}


    # Sort them by list
    for file in file_path_data:
        if file['type'] == 'blob':
            for dep_file in targets:
                if dep_file in file['path']:
                    target_files.setdefault(dep_file, []).append(file['path'])
                    break  # Stop after first match
    
    return target_files

# Builds the entire dependency files query
def build_dependency_query(target_files, default_branch):
    file_queries = []
    alias_map = {}
    alias_count = 0
    for file_type, paths in target_files.items():
        for path in paths:
            alias = f"{re.sub(r'[^A-Za-z0-9_]', '_', file_type)}_{alias_count}"
            file_queries.append(
                f'''{alias}: object(expression: "{default_branch}:{path}") {{
                    ... on Blob {{
                        text
                        isTruncated
                    }}
                }}'''
            )
            # Store mapping: alias -> (file_type, path)
            alias_map[alias] = {"file_type": file_type, "path": path}
            alias_count += 1

    file_queries_str = "\n".join(file_queries)
    query = f"""
    query FetchDependencyFiles($owner: String!, $repo: String!) {{
      repository(owner: $owner, name: $repo) {{
        {file_queries_str}
      }}
    }}
    """
    #print(query)
    return query, alias_map

# Fetches the content of the targeted dependency files in the specified repo through a query request to the GitHub GraphQL API
def get_dependencies(repo_url, token, target_files, default_branch):
    # Extract owner and repo name from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]

    url = "https://api.github.com/graphql"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Split target files into batches
    batches = split_into_batches(target_files)

    results = {}    

    for batch in batches:    
        query, alias_map = build_dependency_query(batch, default_branch)
    
        variables = {"owner": owner, "repo": repo}
        response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)

        if response.status_code == 200:
            response = response.json()

            # No errors from the query result
            if 'errors' not in response:
                data = response["data"]["repository"]

                # Build a result dict with file info and content, crossreferencing the content with its path of origi
                for alias, file_info in alias_map.items():
                    blob = data.get(alias)
                    if blob is not None:
                        #if file_info["path"] == 'yarn.lock':
                            #print(blob.get("text"))
                        # If content is not complete, make seperate API call to fetch full contents
                        if blob.get("isTruncated"):
                            content = get_file_content(repo_url,file_info["path"],token)
                            entry = {
                                "path": file_info["path"],
                                "text": content if blob else None,
                                "isTruncated": "Not anymore" if blob else None
                            }
                        else:
                            entry = {
                                "path": file_info["path"],
                                "text": blob.get("text") if blob else None,
                                "isTruncated": blob.get("isTruncated") if blob else None
                            }
                        
                        # Add to list of corresponding file type
                        results.setdefault(file_info["file_type"], []).append(entry)
            else: 
                print("Error in batch or Repository has no dependency files:", response.get('errors'))
        else:
            raise Exception(f"Query failed with status code {response.status_code}. {response.text}")
        
    return results
    
# Old version of previous function
def old_get_dependencies(repo_url, token, languages):
    # Extract owner and repo name from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]

    url = "https://api.github.com/graphql"
    headers = {}
    if token:  # Add token to header if it's provided
        headers["Authorization"] = f"Bearer {token}"
        

    # Start building the GraphQL query
    query = """
    query FetchDependencyFiles($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
    """
    
    # Add Python files if Python is in languages
    if "Python" in languages:
        query += """
        # Python
        requirements: object(expression: "HEAD:requirements.txt") {
          ... on Blob { text }
        }
        pyproject: object(expression: "HEAD:pyproject.toml") {
          ... on Blob { text }
        }
        """
    
    # Add JavaScript/Node.js files if JavaScript is in languages
    if "JavaScript" in languages:
        query += """
        # JavaScript/Node.js
        packageJson: object(expression: "HEAD:package.json") {
          ... on Blob { text }
        }
        yarnLock: object(expression: "HEAD:yarn.lock") {
          ... on Blob { text 
          isTruncated}
        }
        packageLock: object(expression: "HEAD:package-lock.json") {
          ... on Blob { text }
        }
        """
    
    # Add Java files if Java is in languages
    if "Java" in languages:
        query += """
        # Java
        pomXml: object(expression: "HEAD:pom.xml") {
          ... on Blob { text }
        }
        """
    
    # Add Ruby files if Ruby is in languages
    if "Ruby" in languages:
        query += """
        # Ruby
        gemfile: object(expression: "HEAD:Gemfile") {
          ... on Blob { text }
        }
        gemfileLock: object(expression: "HEAD:Gemfile.lock") {
          ... on Blob { text }
        }
        """
    
    # Add PHP files if PHP is in languages
    if "PHP" in languages:
        query += """
        # PHP
        composerJson: object(expression: "HEAD:composer.json") {
          ... on Blob { text }
        }
        composerLock: object(expression: "HEAD:composer.lock") {
          ... on Blob { text }
        }
        """
    
    # Add Go files if Go is in languages
    if "Go" in languages:
        query += """
        # Go
        goMod: object(expression: "HEAD:go.mod") {
          ... on Blob { text }
        }
        goSum: object(expression: "HEAD:go.sum") {
          ... on Blob { text }
        }
        """
    
    # Add Rust files if Rust is in languages
    if "Rust" in languages:
        query += """
        # Rust
        cargoToml: object(expression: "HEAD:Cargo.toml") {
          ... on Blob { text }
        }
        cargoLock: object(expression: "HEAD:Cargo.lock") {
          ... on Blob { text }
        }
        """
    
    # Add .NET files if .NET is in languages
    if "C#" in languages:
        query += """
        # C#
        proj: object(expression: "HEAD:*.csproj") {
          ... on Blob { text }
        }
        packagesConfig: object(expression: "HEAD:packages.config") {
          ... on Blob { text }
        }
        """
    
    # Close the GraphQL query
    query += """
      }
    }
    """
    
    variables = {"owner": owner, "repo": repo}
    response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
    
    if response.status_code == 200:
        response = response.json()

        # No errors from the query result
        if 'errors' not in response:
            return response
        else: 
            return None
    else:
        raise Exception(f"Query failed with status code {response.status_code}. {response.text}")
  
# Save data in .json format localy (for debug)
def save_file(repo_data):
    # File handling
    filename = "repo_data.json"

    # Check if the file exists
    if os.path.exists(filename):
        # If the file exists, read the existing data
        with open(filename, 'r') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []  # Handle empty or corrupted JSON file
    else:
        # If the file doesn't exist, create an empty list
        existing_data = []

    # Append the new data to the existing data
    existing_data.append(repo_data)

    # Write the updated data back to the file
    with open(filename, 'w') as f:
        json.dump(existing_data, f, indent=4)

# Scrap data from the repository
def scrap_data(repo_url,token,debug=None):
    # Load data.json
    data_json = load_data_json()
    
    repo_data = get_repo_data(repo_url,token)

    # If repo exists, is available and data was able to be fetched
    if repo_data and type(repo_data) == dict:
        repo_name = repo_data.get('name')
        print(f"The repository name is: {repo_name}")
        readme_data = get_repo_readme(repo_url,token)
        lang_data = get_repo_languages(repo_url,token)
        file_path_data = get_repo_files(repo_url,repo_data.get('default_branch'),token)
        submodule_data = get_submodules(repo_url,token)
        #dependency_files_data = get_dependencies(repo_url, token, list(lang_data.keys()))
        if lang_data:
            #print(f"Languages used:\n{lang_data}")
            repo_data["languages"] = lang_data
        if readme_data:
            #print(f"README:\n{readme_data}")
            repo_data["readme"] = readme_data
        if file_path_data:
            #print(f"File path data:\n{file_path_data}")
            repo_data["file_path_data"] = file_path_data
            # Load types of dependency files to target
            targets = data_json["dependency_file_targets"]
            target_files = find_dependency_files(file_path_data,targets)
            dependency_files_data = get_dependencies(repo_url, token, target_files, repo_data.get('default_branch'))
            if dependency_files_data:
                #pprint.pprint(dependency_files_data)
                repo_data["dependency_file_data"] = dependency_files_data
                #with open("dependency_data.json", 'w') as f:
                #    json.dump(dependency_files_data, f, indent=4)

        if submodule_data:
            #print(f"Submodules found:\n{submodule_data}")
            repo_data["submodules"] = submodule_data
        #if dependency_files_data:
            #print(f"Dependency file data found:")
            #pprint.pprint(dependency_files_data)
            #repo_data["dependency_file_data"] = dependency_files_data["data"]["repository"]
        #print(json.dumps(repo_data, indent=4))
        if debug:
            save_file(repo_data)
        
        #pprint.pprint(repo_data)
        return repo_data
    else:
        return ('Error',repo_data)

# Test/Utilize the scrapper localy
def test_scraper():
    # Example usage
    token = input("Input your GitHub token (optional, but recomended): ")
    while True:
        repo_url = input("Insert repository URL to fetch (or input nothing to stop): ")
        if repo_url != "":
            scrap_data(repo_url,token,True)
        else:
            break

# ------------------------------- FOR TESTING ONLY -------------------------------
#if __name__ == "__main__":
#    test_scraper()