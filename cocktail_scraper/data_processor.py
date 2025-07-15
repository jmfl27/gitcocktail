import json
import re
import pprint
import dependencies_parser

# Auxiliary function to help rebuid file hierarchy
def build_hierarchy(entries):
    hierarchy = {}
    FILE_KEY = "_files"  # Use a special key that won't conflict with real dirs
    
    for entry in entries:
        path = entry['path']
        parts = path.split('/')
        current_level = hierarchy
        
        for part in parts[:-1]:  # Process directories
            if part not in current_level:
                current_level[part] = {}
            elif isinstance(current_level[part], list):
                # Convert existing files into a dir with _files
                current_level[part] = {FILE_KEY: current_level[part]}
            current_level = current_level[part]
        
        if entry['type'] == 'blob':  # It's a file
            if FILE_KEY not in current_level:
                current_level[FILE_KEY] = []
            current_level[FILE_KEY].append(parts[-1])
        elif entry['type'] == 'tree':  # It's a directory
            if parts[-1] not in current_level:
                current_level[parts[-1]] = {}
            elif isinstance(current_level[parts[-1]], list):
                # Convert existing files into a dir with _files
                current_level[parts[-1]] = {FILE_KEY: current_level[parts[-1]]}
    
    return hierarchy

# Function that rebuilds the repo file path
def convert_to_output_format(hierarchy):
    output = {}
    FILE_KEY = "_files"
    
    for key, value in hierarchy.items():
        if key == FILE_KEY:
            # Handle root files
            if 'root' not in output:
                output['root'] = []
            output['root'].extend(value)
            continue
            
        # Process directories
        dir_contents = []
        
        # Add files if they exist
        if isinstance(value, dict) and FILE_KEY in value:
            dir_contents.extend(value[FILE_KEY])
        
        # Add subdirectories
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if sub_key != FILE_KEY:
                    nested = convert_to_output_format({sub_key: sub_value})
                    if sub_key in nested:
                        if isinstance(nested[sub_key], list):
                            dir_contents.append({sub_key: nested[sub_key]})
                        else:
                            dir_contents.append(nested)
        
        if dir_contents:  # Only add if there's content
            output[key] = dir_contents
    
    return output

# Loads the repo data from a file or from a dictionary
def load_repos(file_path,is_file):
    repo_data = []

    if is_file:
        with open(file_path) as f:
            data = json.load(f)
    else:
        data = file_path

    for repo in data:
        print(repo["name"])
        content = {}
        content["name"] = repo["name"]
        content["description"] = repo["description"]
        content["languages"] = []
        for lang in repo["languages"]:
            content["languages"].append(lang.replace(" ","_"))
        content["readme"] = repo["readme"]
        """
        content["files"] = {"pathlessFiles":[]}
        for file_data in repo["file_path_data"]:
            #print(file_data)
            
            if file_data["type"] == "tree":
                content["files"][file_data["path"]] = []
            elif file_data["type"] == "blob" and ('/' in file_data["path"]):
                match = re.match(r"(.+)/(.+)", file_data["path"])
                if match:
                    path = list(match.groups())
                    content["files"][path[0]].append(path[1])
            elif file_data["type"] == "blob":
                content["files"]["pathlessFiles"].append(file_data["path"])
        """ 
        file_hierarchy = build_hierarchy(repo["file_path_data"])
        content["files"] = convert_to_output_format(file_hierarchy)
        #content["files"] = build_file_structure(repo["file_path_data"])
        if "submodules" in repo: 
            content["submodules"] = repo["submodules"]
            
        if "dependency_file_data" in repo:
            content["dependency_file_data"] = {d: t for d, t in repo["dependency_file_data"].items() if t is not None}
            

        repo_data.append(content)

    return repo_data

# Saves the format that the loaded data was stored in (for debug)
def save_loaded_data(repo_data):
    # File handling
    filename = "loaded_data.json"

    # Write the updated data back to the file
    with open(filename, 'w') as f:
        json.dump(repo_data, f, indent=4)

"""
def eliminate_duplicates(obj):
    # Recursively eliminates all duplicates from all lists in a (possibly nested) dict structure.
    if isinstance(obj, dict):
        return {k: eliminate_duplicates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Use dict.fromkeys to preserve order
        return list(dict.fromkeys(obj))
    else:
        return obj
"""

# Recursively eliminates duplicate dictionaries from all lists in a nested dict structure
def eliminate_duplicates(obj):

    if isinstance(obj, dict):
        # Recursively process each value in the dict
        return {k: eliminate_duplicates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Remove duplicate dicts in the list
        seen = set()
        result = []
        for item in obj:
            if isinstance(item, dict):
                # Convert dict to a hashable representation (e.g., JSON string)
                item_hash = json.dumps(item, sort_keys=True)
                if item_hash not in seen:
                    seen.add(item_hash)
                    result.append(eliminate_duplicates(item))
            else:
                # For non-dict items, just process recursively
                result.append(eliminate_duplicates(item))
        return result
    else:
        # Base case: not a dict or list
        return obj

# Parses a repo's dependency files for ingredients
def parse_dependencies(repo):
    content = {}

    if "pyproject.toml" in repo["dependency_file_data"]:
        # {'dependencies': dependencies{ "necessary"[], "optional"{grupo:[]} || [] }, 'tools': tools[]}
        for file in repo["dependency_file_data"]["pyproject.toml"]:
            dependencies = dependencies_parser.py_pyproject(file["text"])
            if 'dependencies' in dependencies:
                if 'necessary' in dependencies['dependencies']:
                    content.setdefault('necessary', []).extend(dependencies['dependencies']['necessary'])
                # optionals are a special case
                if 'optional' in dependencies['dependencies']:
                    match(dependencies['dependencies']['optional']):
                        case list():
                            content.setdefault('optional',{}).setdefault('none_found', []).extend(dependencies['dependencies']['optional'])
                        case dict():
                            for group in dependencies['dependencies']['optional']:
                                content.setdefault('optional',{}).setdefault(group, []).extend(dependencies['dependencies']['optional'][group])

            if 'tools' in dependencies:
                content.setdefault('tools',[]).extend(dependencies["tools"])

    if "requirements.txt" in repo["dependency_file_data"]:
        # {'dependencies' : dependecies[], 'req_files' : requires[]}
        for file in repo["dependency_file_data"]["requirements.txt"]:
            dependencies = dependencies_parser.py_requirements(file["text"])
            if 'dependencies' in dependencies: 
                content.setdefault('necessary', []).extend(dependencies['dependencies'])
            #TODO: Tratar req_files

    if "package.json" in repo["dependency_file_data"]:
        # {'necessary':[],'devDependencies':[],'peerDependencies':[],'bundledDependencies':[],'optional':[],'os':[]}
        for file in repo["dependency_file_data"]["package.json"]:
            dependencies = dependencies_parser.js_packageJson(file["text"])
            for key in dependencies:
                # optionals are a special case
                if key == 'optional':
                    content.setdefault('optional',{}).setdefault('none_found', []).extend(dependencies['optional'])
                else:
                    content.setdefault(key, []).extend(dependencies[key])          

    if "yarn.lock" in repo["dependency_file_data"]:   
        # []       
        for file in repo["dependency_file_data"]["yarn.lock"]:
            dependencies = dependencies_parser.js_yarnLock(file["text"])
            content.setdefault('others', []).extend(dependencies)

    if "pom.xml" in repo["dependency_file_data"]:
        # []             
        for file in repo["dependency_file_data"]["pom.xml"]:
            dependencies = dependencies_parser.java_pomXML(file["text"])
            content.setdefault('necessary', []).extend(dependencies)

    if "Gemfile" in repo["dependency_file_data"]:
        # {'groupName' : elements[]}
        for file in repo["dependency_file_data"]["Gemfile"]:
            dependencies = dependencies_parser.ruby_gemfile(file["text"])
            for group in dependencies:
                # Parser puts ungrouped dependencies under 'runtime' key; necessary by default
                if group == 'runtime':
                    content.setdefault('necessary', []).extend(dependencies[group])
                else:
                    content.setdefault('groups',{}).setdefault(group, []).extend(dependencies[group])

    if "composer.json" in repo["dependency_file_data"]:     
        # {'necessary':[], 'devDependencies':[]}      
        for file in repo["dependency_file_data"]["composer.json"]:
            dependencies = dependencies_parser.php_composerJson(file["text"])
            for key in dependencies:
                content.setdefault(key, []).extend(dependencies[key])   

    if "go.mod" in repo["dependency_file_data"]: 
        # {'necessary':[], 'indirect':[]}            
        for file in repo["dependency_file_data"]["go.mod"]:
            dependencies = dependencies_parser.go_goMod(file["text"])
            for key in dependencies:
                content.setdefault(key, []).extend(dependencies[key])

    if "go.sum" in repo["dependency_file_data"]:    
        # []        
        for file in repo["dependency_file_data"]["go.sum"]:
            dependencies = dependencies_parser.go_goSum(file["text"])
            content.setdefault('others', []).extend(dependencies)

    if "Cargo.toml" in repo["dependency_file_data"]:
        # {'necessary':[], 'devDependencies':[], 'buildDependencies':[], 'workspaceDependencies':[], 'target':{'targetName': {all previous are possible} } }             
        for file in repo["dependency_file_data"]["Cargo.toml"]:
            if file["path"].endswith("Cargo.toml"):
                dependencies = dependencies_parser.rust_cargoToml(file["text"], recursive=False)
                for key in dependencies:
                    # Some dependencies are organized by 'target'
                    if key == 'target':
                        for target in dependencies['target']:
                            for target_sub in dependencies['target'][target]:
                                content.setdefault('target',{}).setdefault(target, {}).setdefault(target_sub,[]).extend(dependencies['target'][target][target_sub])
                    else:
                        content.setdefault(key, []).extend(dependencies[key])  

    if ".csproj" in repo["dependency_file_data"]:   
        # {'packageReference':[], 'reference':[]}      
        for file in repo["dependency_file_data"][".csproj"]:
            dependencies = dependencies_parser.dotNet_proj(file["text"])
            for key in dependencies:
                content.setdefault('necessary', []).extend(dependencies[key])  

    if "packages.config" in repo["dependency_file_data"]:
        # []     
        for file in repo["dependency_file_data"]["packages.config"]:
            dependencies = dependencies_parser.dotNet_packagesConfig(file["text"])
            content.setdefault('necessary', []).extend(dependencies)
    
    return eliminate_duplicates(content)

# Identifies ingredients and elements of the onotology in the repo data
def process_repo_data(repo_data):
    processed_data = []
    for repo in repo_data:
        content = {}
        content["name"] = repo["name"]
        content["ingredients"] = {}
        # Parse dependencies to get ingedients
        if "dependency_file_data" in repo:
            content["ingredients"]["dependencies"] = parse_dependencies(repo)
        
        if "languages" in repo:
            content["languages"] = repo["languages"]
        
        if "submodules" in repo:
            content["submodules"] = repo["submodules"]
        
        processed_data.append(content)

    return processed_data

# Saves the processed data into a JSON file (for debug)
def save_processed_data(repo_data):
    # File handling
    filename = "processed_data.json"

    # Write the updated data back to the file
    with open(filename, 'w') as f:
        json.dump(repo_data, f, indent=4)

# Processes the scraped data into a more suitable format to build the ontology
def process_data(data):
    repo_data = load_repos(data,False)
    processed_data = process_repo_data(repo_data)
    return processed_data

# Same as above function, but saves the content into a file (for debug)
def test_process_data():
    repo_data = load_repos("repo_data.json",True)
    #pprint.pprint(repo_data)
    save_loaded_data(repo_data)
    processed_data = process_repo_data(repo_data)
    #print("\n\n\n\n\n\n\n\n\n\n")
    #pprint.pprint(processed_data)
    save_processed_data(processed_data)
    return processed_data

#test_process_data()