import json
import re
import pprint
from . import dependencies_parser
from .scraper import load_data_json

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

# Fetches all of the distinct ingredient types and counts the number of ingredients present
def get_types(obj, types=None, count=None):
    if types is None:
        types = set()
    if count is None:
        count = [0]  # Single-element list as mutable counter
    if isinstance(obj, dict):
        if "type" in obj:
            types.add(obj["type"])
            count[0] += 1
        for v in obj.values():
            get_types(v, types, count)
    elif isinstance(obj, list):
        for item in obj:
            get_types(item, types, count)
    return types, count[0]

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
        if "languages" in repo:
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
"""

def dict_hash(d,key):
    # Hash dictionary, ignoring 'key'
    return json.dumps({k: v for k, v in d.items() if k != key}, sort_keys=True)

def merge_associated_types(d1, d2, key):
    # Merge associated_types lists, avoiding duplicates
    ats1 = set(d1.get(key, []))
    ats2 = set(d2.get(key, []))
    merged = list(ats1 | ats2)
    if merged:
        return {**d1, key: merged}
    else:
        # If the merged list is empty, remove the key (optional)
        d = dict(d1)
        d.pop(key, None)
        return d

# Recursively eliminates duplicate dictionaries from all lists in a nested dict structure, while merging the 'associated_types' of the duplicate entries
def eliminate_and_merge_duplicates(obj):
    if isinstance(obj, dict):
        # Recursively process each value in the dict
        return {k: eliminate_and_merge_duplicates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Remove duplicate dicts in the list
        seen = {}
        result = []
        for item in obj:
            if isinstance(item, dict):
                # Convert dict to a hashable representation (e.g., JSON string)
                h = dict_hash(item,'associated_types')
                item_clean = eliminate_and_merge_duplicates(item)
                if h in seen:
                    # Merge associated_types if duplicate found
                    merged = merge_associated_types(seen[h], item_clean,'associated_types')
                    seen[h] = merged
                else:
                    seen[h] = item_clean
            else:
                # For non-dict items, just process recursively
                result.append(eliminate_and_merge_duplicates(item))
        # Append the merged dicts to the result in deduplicated form
        result.extend(seen.values())
        return result
    else:
        # Base case: not a dict or list
        return obj

# Parses a repo's dependency files for ingredients
def parse_dependencies(repo,languages=None):
    # Load data.json
    data_json = load_data_json()
    
    # Find which compatible .NET languages are present
    if languages:
        dotNet_langs = [item for item in data_json["dotNet_languages"] if item in languages]
    else:
        languages = []

    content = {}

    if "pyproject.toml" in repo["dependency_file_data"]:
        # {'dependencies': dependencies{ "necessary"[], "optional"{grupo:[]} || [] }, 'tools': tools[]}
        for file in repo["dependency_file_data"]["pyproject.toml"]:
            if file["text"] != "":
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
            if file["text"] != "":
                dependencies = dependencies_parser.py_requirements(file["text"])
                if 'dependencies' in dependencies: 
                    content.setdefault('necessary', []).extend(dependencies['dependencies'])
                #TODO: Tratar req_files

    if "package.json" in repo["dependency_file_data"]:
        # {'necessary':[],'devDependencies':[],'peerDependencies':[],'bundledDependencies':[],'optional':[],'os':[]}
        for file in repo["dependency_file_data"]["package.json"]:
            if file["text"] != "":
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
            if file["text"] != "":
                dependencies = dependencies_parser.js_yarnLock(file["text"])
                content.setdefault('others', []).extend(dependencies)

    if "pom.xml" in repo["dependency_file_data"]:
        # []             
        for file in repo["dependency_file_data"]["pom.xml"]:
            if file["text"] != "":
                dependencies = dependencies_parser.java_pomXML(file["text"])
                content.setdefault('necessary', []).extend(dependencies)

    if "Gemfile" in repo["dependency_file_data"]:
        # {'groupName' : elements[]}
        for file in repo["dependency_file_data"]["Gemfile"]:
            if file["text"] != "":
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
            if file["text"] != "":
                dependencies = dependencies_parser.php_composerJson(file["text"])
                for key in dependencies:
                    content.setdefault(key, []).extend(dependencies[key])   

    if "go.mod" in repo["dependency_file_data"]: 
        # {'necessary':[], 'indirect':[]}            
        for file in repo["dependency_file_data"]["go.mod"]:
            if file["text"] != "":
                dependencies = dependencies_parser.go_goMod(file["text"])
                for key in dependencies:
                    content.setdefault(key, []).extend(dependencies[key])

    if "go.sum" in repo["dependency_file_data"]:    
        # []        
        for file in repo["dependency_file_data"]["go.sum"]:
            if file["text"] != "":
                dependencies = dependencies_parser.go_goSum(file["text"])
                content.setdefault('others', []).extend(dependencies)

    if "Cargo.toml" in repo["dependency_file_data"]:
        # {'necessary':[], 'devDependencies':[], 'buildDependencies':[], 'workspaceDependencies':[], 'target':{'targetName': {all previous are possible} } }             
        for file in repo["dependency_file_data"]["Cargo.toml"]:
            if file["text"] != "":
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
        # Load dotNet framework tfm (target framework moniker)
        frameworks_json = data_json["dotNet_framework_tfm"]
        
        # Build lookup for faster checking
        framework_tfm = {}
        for group, tfms in frameworks_json.items():
            for tfm in tfms:
                framework_tfm[tfm] = group

        # {'packageReference':[], 'reference':[], 'frameworks':[]}      
        for file in repo["dependency_file_data"][".csproj"]:
            if file["text"] != "":      
                dependencies = dependencies_parser.dotNet_proj(file["text"],framework_tfm,dotNet_langs)
                for key in dependencies:
                    content.setdefault('necessary', []).extend(dependencies[key])  

    if ".vbproj" in repo["dependency_file_data"]:
        # Load dotNet framework tfm (target framework moniker)
        frameworks_json = data_json["dotNet_framework_tfm"]
        
        # Build lookup for faster checking
        framework_tfm = {}
        for group, tfms in frameworks_json.items():
            for tfm in tfms:
                framework_tfm[tfm] = group

        # {'packageReference':[], 'reference':[], 'frameworks':[]}      
        for file in repo["dependency_file_data"][".vbproj"]:
            if file["text"] != "":        
                dependencies = dependencies_parser.dotNet_proj(file["text"],framework_tfm,dotNet_langs)
                for key in dependencies:
                    content.setdefault('necessary', []).extend(dependencies[key])

    if ".fsproj" in repo["dependency_file_data"]:
        # Load dotNet framework tfm (target framework moniker)
        frameworks_json = data_json["dotNet_framework_tfm"]
        
        # Build lookup for faster checking
        framework_tfm = {}
        for group, tfms in frameworks_json.items():
            for tfm in tfms:
                framework_tfm[tfm] = group

        # {'packageReference':[], 'reference':[], 'frameworks':[]}      
        for file in repo["dependency_file_data"][".fsproj"]:
            if file["text"] != "":        
                dependencies = dependencies_parser.dotNet_proj(file["text"],framework_tfm,dotNet_langs)
                for key in dependencies:
                    content.setdefault('necessary', []).extend(dependencies[key]) 
    
    if "packages.config" in repo["dependency_file_data"]:
        # Load dotNet framework tfm (target framework moniker)
        frameworks_json = data_json["dotNet_framework_tfm"]
        
        # Build lookup for faster checking
        framework_tfm = {}
        for group, tfms in frameworks_json.items():
            for tfm in tfms:
                framework_tfm[tfm] = group

        # {'package':[], 'devDependencies':[], 'frameworks':[]}     
        for file in repo["dependency_file_data"]["packages.config"]:
            if file["text"] != "":
                dependencies = dependencies_parser.dotNet_packagesConfig(file["text"],framework_tfm,dotNet_langs)
                for key in dependencies:
                    content.setdefault('necessary', []).extend(dependencies[key]) 
    
    #return eliminate_duplicates(content)
    return eliminate_and_merge_duplicates(content)

# Identifies ingredients and elements of the onotology in the repo data
def process_repo_data(repo_data):
    processed_data = []
    for repo in repo_data:
        content = {}
        content["name"] = repo["name"]
        content["ingredients"] = {}
        # Parse dependencies to get ingedients
        if "dependency_file_data" in repo:
            if "languages" in repo:
                content["ingredients"]["dependencies"] = parse_dependencies(repo,repo["languages"])
            else:
                content["ingredients"]["dependencies"] = parse_dependencies(repo)
        
        if "languages" in repo:
            content["languages"] = repo["languages"]
        
        if "submodules" in repo:
            content["ingredients"]["submodules"] = []
            for submodule in repo["submodules"]:
                content["ingredients"]["submodules"].append({"name": submodule, 'type': "Library"})

        ingredient_types, ingredient_count = get_types(content["ingredients"])
        content["ingredient_types"] = list(ingredient_types)
        
        if "languages" in repo and content["languages"] != []:
            content["ingredient_types"].append('Language')
            content["ingredient_count"] = ingredient_count + len(content["languages"])
        else:
            content["ingredient_count"] = ingredient_count
        
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

#if __name__ == "__main__":
#    test_process_data()