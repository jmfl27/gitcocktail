import re, json, toml, tempfile, subprocess, os
import xml.etree.ElementTree as ET
import pyarn.lockfile
from gemfileparser2 import GemfileParser
from pprint import pprint

# Used to normalize names to be compared
def normalize(s):
    # Lowercase, replace separators with space, collapse spaces, strip
    s = s.casefold()
    s = re.sub(r"[-_.]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

# Tries to identify an ingredient's type, defaults to 'Library'
def type_indentifier(ingredient,info=None):

    # Try to identify type based on the given info
    if info:
        if info["type"]:
            if info["type"] == 'dotNet_framework':
                results = []
                frameworks_found = set()
                # For each tfm found
                for tfm in ingredient:
                    # Find the associated framework
                    for key in info["data"]:
                        # If tfm matches, identify the Framework
                        if key in tfm:
                            framework = info["data"][key]
                            # Prevent repeated frameworks
                            if framework not in frameworks_found:
                                frameworks_found.add(framework)
                                # Case where framworks share tfm
                                if '/' in framework:
                                    for splited in framework.split('/'):
                                        results.append({"name": splited, 'type': "Framework"})
                                else:
                                    results.append({"name": framework, 'type': "Framework"})
                            break
                
                return results


    else:
        if type(ingredient) != list:
            # Defualt to Library type
            result = {"name" : ingredient, 'type': "Library"}

            return result

# Parses a "requirements.txt" file for dependencies
def py_requirements(req_contents):
    # Regex for flags
    flag_regex = r"^-\w\s+.+"
    # Regex for flag -r
    flag_req_regex = r"^-r\s+(.+)"
    # Regex for valid dependency
    dependency_regex = r"^[a-zA-Z0-9_\-\.]+"
    # Regex for URLs
    url_regex = r"^(https?:\/\/|ftp:\/\/|www\.).+"
    # Regex for file paths (absolute, relative, or containing dirs/extensions)
    filepath_regex = r"^\.?\/?[\w\-]+(\/[\w\-.]+)+(\.[\w\d]+)?$|^\.?\/?[\w\-]+(\.[\w\d]+)"

    dependecies = []
    requires = []

    # Go through each line from the file
    for line in req_contents.splitlines():
        stripped = line.strip()
        # Skip empty lines and comments
        if not stripped or stripped == "#":
            continue
        # If flag "-r", then save the name of the additional requirements file
        req_match = re.match(flag_req_regex, stripped)
        if req_match:
            requires.append(req_match.group(1))
        else:
             # If line is a URL or a file path, skip it
            if re.match(url_regex, stripped) or re.match(filepath_regex, stripped):
                continue
            # If it's another flag or comentary, ignore
            flag_match = re.match(flag_regex, stripped)
            if not flag_match and line.strip()[0] != '#':
                # If dependency, save it's name
                dependency_match = re.match(dependency_regex, stripped)
                if dependency_match:
                    dependecies.append(type_indentifier(dependency_match.group()))
                else:
                    print("Python requirements.txt - Not a dependency match: " + line)
                    input("Press enter to continue")

    results = {'dependencies' : dependecies, 'req_files' : requires}

    #pprint(results)

    return results

# Parses a "pyproject.toml" file for dependencies
def py_pyproject(toml_content):
    #print(toml_content)
    toml_dict = toml.loads(toml_content)
    #pprint(toml_dict)
    dependency_regex = r"^[a-zA-Z0-9_\-\.]+"
    dependencies = {}
    optional_dict = False

    # Fetch "dependencies" block
    if 'project' in toml_dict and 'dependencies' in toml_dict['project']:
        dependencies["necessary"]=[]
        for dependency in toml_dict['project']['dependencies']:
            match = re.match(dependency_regex,dependency.strip())
            if match: 
                dependencies['necessary'].append(match.group())
            else: 
                print("PyProject - Not a dependency match: " + dependency)
                input("Press enter to continue")

    # Fetch "optional-dependencies" block
    if 'project' in toml_dict and toml_dict['project']['optional-dependencies']:
        # If "optional-dependencies" has multiple entries
        if isinstance(toml_dict['project']['optional-dependencies'], dict):
            optional_dict = True
            dependencies["optional"]={}
            for group in toml_dict['project']['optional-dependencies']:
                dependencies['optional'][group] = []
                for dependency in toml_dict['project']['optional-dependencies'][group]:
                    match = re.match(dependency_regex,dependency.strip())
                    if match: 
                        dependencies['optional'][group].append(match.group())
                    else: 
                        print("PyProject - Not an optional depenedency match: " + dependency)
                        input("Press enter to continue")
        else:
            dependencies["optional"]=[]
            for dependency in toml_dict['project']['optional-dependencies']:
                match = re.match(dependency_regex,dependency.strip())
                if match: 
                    dependencies['optional'].append(match.group())
                else: 
                    print("PyProject - Not a match: " + dependency)
                    input("Press enter to continue")

    #classifiers_regex = r"(\w+(\s*\w+)*)\s*::\s*(\w+(\s*\w+)*)(\s*::.+)?"
    classifiers_regex = r"([a-zA-Z0-9_\-\.]+(\s*[a-zA-Z0-9_\-\.]+)*)\s*::\s*([a-zA-Z0-9_\-\.]+(\s*[a-zA-Z0-9_\-\.]+)*)(\s*::.+)?"
    classifiers = []

    # Fetch "classifiers" block
    if 'project' in toml_dict and 'classifiers' in toml_dict['project']:
        for classifier in toml_dict['project']['classifiers']:
            match = re.match(classifiers_regex, classifier)
            if match:
                #type = match.group(1)
                #name = match.group(3)
                classifiers.append((match.group(3),match.group(1)))
            else:
                print("PyProject - Not a classifier match: " + classifier)
                input("Press enter to continue")
    
        # Clean repeated entries
        classifiers = {normalize(k): v for k, v in dict(classifiers).items()}
        
        if "necessary" in dependencies.keys():
            temp = []
            # Get ingredient type from classifiers if it exists
            for dependency in dependencies['necessary']:
                if normalize(dependency) in classifiers:
                    #TODO: Implementar database de ingredientes
                    temp.append({"name" : dependency, "type" : classifiers[normalize(dependency)]})
                else:
                    # If not, try to identify
                    temp.append(type_indentifier(dependency))
            dependencies['necessary'] = temp

        if "optional" in dependencies.keys():
            if optional_dict:
                for group in dependencies['optional']:
                    temp = []
                    # Get ingredient type from classifiers if it exists
                    for dependency in dependencies['optional'][group]:
                        if normalize(dependency) in classifiers:
                            #TODO: Implementar database de ingredientes
                            temp.append({"name" : dependency, "type" : classifiers[normalize(dependency)]})
                        else:
                            # If not, try to identify
                            temp.append(type_indentifier(dependency))
                    dependencies['optional'][group] = temp
            else:
                # Get ingredient type from classifiers if it exists
                for dependency in dependencies['optional']:
                    if normalize(dependency) in classifiers:
                        #TODO: Implementar database de ingredientes
                        temp.append({"name" : dependency, "type" : classifiers[normalize(dependency)]})
                    else:
                        # If not, try to identify
                        temp.append(type_indentifier(dependency))
                dependencies['optional'] = temp
    
    tools = []
    if 'tool' in toml_dict:
        for tool in toml_dict['tool']: 
            tools.append({"name" : tool, "type": 'Tool'})


    #pprint(dependencies)
    #pprint(classifiers)
    #pprint(tools)

    ingredients = {'dependencies':dependencies, 'tools':tools}
    #pprint(ingredients)

    return ingredients

#def py_setup():
#    return

# Parses a "package.json" file for dependencies
def js_packageJson(package_content):
    json_dict = json.loads(package_content)
    #pprint(json_dict)

    # Catches all non-only Git hosted dependencies
    gitless_regex = r"^(?!git(?:\+ssh|\+http|\+https|\+file)?:\/\/).*"
    dependencies = {}

    # For dependencies
    if 'dependencies' in json_dict:
        dependencies['necessary'] = []
        for dependency in json_dict['dependencies']:
            match = re.match(gitless_regex,dependency.strip())
            if match:
                dependencies['necessary'].append(type_indentifier(match.group()))
            else: 
                print("Package.json - Not a git-less dependency match: " + dependency)
                input("Press enter to continue")
    
    # For devDependencies (structured like 'dependencies')
    if 'devDependencies' in json_dict:
        dependencies['devDependencies'] = []
        for dependency in json_dict['devDependencies']:
            match = re.match(gitless_regex,dependency.strip())
            if match:
                dependencies['devDependencies'].append(type_indentifier(match.group()))
            else: 
                print("Package.json - Not a git-less devDependency match: " + dependency)
                input("Press enter to continue")        

    # For peerDependencies (structured like 'dependencies')   
    if 'peerDependencies' in json_dict:
        dependencies['peerDependencies'] = []
        for dependency in json_dict['peerDependencies']:
            match = re.match(gitless_regex,dependency.strip())
            if match:
                dependencies['peerDependencies'].append(type_indentifier(match.group()))
            else: 
                print("Package.json - Not a git-less peerDependency match: " + dependency)
                input("Press enter to continue")

    # For bundledDependencies/bundleDependencies (usually just package names in an array of strings or a single bool, not objects)
    if 'bundledDependencies' in json_dict and type(json_dict['bundledDependencies']) != bool:
        dependencies['bundledDependencies'] = []
        for dependency in json_dict['bundledDependencies']:
            match = re.match(gitless_regex, dependency.strip())
            if match:
                dependencies['bundledDependencies'].append(type_indentifier(match.group()))
            else:
                print("Package.json - Not a git-less bundledDependency match: " + dependency)
                input("Press enter to continue")

    if 'bundleDependencies' in json_dict and type(json_dict['bundleDependencies']) != bool:
        dependencies['bundledDependencies'] = []
        for dependency in json_dict['bundleDependencies']:
            match = re.match(gitless_regex, dependency.strip())
            if match:
                dependencies['bundledDependencies'].append(type_indentifier(match.group()))
            else:
                print("Package.json - Not a git-less bundledDependency match: " + dependency)
                input("Press enter to continue")

    # For optionalDependencies (structured like 'dependencies')
    if 'optionalDependencies' in json_dict:
        dependencies['optional'] = []
        for dependency, version in json_dict['optionalDependencies'].items():
            match = re.match(gitless_regex, dependency.strip())
            if match:
                dependencies['optional'].append(type_indentifier(match.group()))
            else:
                print("Package.json - Not a git-less optionalDependency match: " + dependency)
                input("Press enter to continue")

    # For os (Operating Systems)
    if 'os' in json_dict:
        dependencies['os'] = []
        for op_system in dependencies['os']:
            # If it begins with '!', then it means that that OS is not suported/blocked
            if op_system[0] != '!':
                dependencies['os'].append({"name" : op_system, "type" : 'Resource'})
    
    #print(dependencies)
    #print(len(json_dict['devDependencies'].keys()))
    #print(len(dependencies['devDependencies']))

    return dependencies

# Parses a "yarn.lock" file for dependencies
def js_yarnLock(yarn_content):
    yarn_dict = pyarn.lockfile.Lockfile.from_str(yarn_content)
    #print(yarn_dict.data.keys())

    package_regex = r"([a-zA-Z0-9_\-\.\/@]+)@.+"
    dependencies = []
    names = set()
    # Go through each package info to fetch name
    for package in yarn_dict.data.keys():
        match = re.match(package_regex, package.strip())
        # Prevent repeated entries for packages with multiple version declarations
        if match:
            if match.group(1) not in names:
                #print(match.group(1))
                dependencies.append(type_indentifier(match.group(1)))
                names.add(match.group(1))
        else:
            print("yarn.lock - Not a package match: " + package)
            input("Press enter to continue")
    
    #pprint(dependencies)

    return dependencies

# Auxiliary function used to strip namespaces from XML files
def strip_namespace(xml_content):
    # Remove xmlns definitions
    xml_content = re.sub(r'xmlns="[^"]+"', '', xml_content, count=1)
    return xml_content

# Parses a "pom.xml" file for dependencies
def java_pomXML(xml_content):
    # Remove namespace for easier parsing
    xml_content = strip_namespace(xml_content)
    root = ET.fromstring(xml_content)

    dependencies = []
    names = set()
    # '.' - starting from the root | "//" - any descendant, at any level
    # './/dependency' - every dependency element, no matter how deeply nested it is within the tree
    for dependency in root.findall('.//dependency'):
        group_id = dependency.find('groupId').text
        artifact_id = dependency.find('artifactId').text
        #version = dependency.find('version').text
        #print(f"{group_id}:{artifact_id}:{version}")

        # Prevent repeated dependency entries
        if artifact_id not in names:
            names.add(artifact_id)
            dependencies.append(type_indentifier(artifact_id))

    #printdependencies)    
    return dependencies

#def java_buildGradle():
#    return

#def kotlin_buildGradle():
#    return

# Parses a "Gemfile" file for dependencies
def ruby_gemfile(gemfile_content):
    # Gemfile parsing library only reads from file, use tempfile to create a temporary file with the content fetched
    with tempfile.NamedTemporaryFile('w+', delete=False) as tmp:
        tmp.write(gemfile_content)
        tmp.flush()
        # Iniciate parser
        parser = GemfileParser(tmp.name)
        deps = parser.parse()

    dependencies = {}

    # Gems can be sorted in groups
    for group, gems in deps.items():
        #print(group)
        dependencies[group] = []
        for gem in gems:
            #print(f"  {gem.name} {gem.requirement} {gem.autorequire}")
            dependencies[group].append(type_indentifier(gem.name))
        
        # Eliminate empty groups from the parsed file
        if dependencies[group] == []:
            dependencies.pop(group,None)
    
    #pprint(dependencies)

    return dependencies

# Parses a "composer.json" file for dependencies
def php_composerJson(composer_content):
    json_dict = json.loads(composer_content)
    dependencies = {}
    
    if "require" in json_dict:
        dependencies["necessary"] = []
        for package in json_dict["require"]:
            dependencies["necessary"].append(type_indentifier(package))
    
    if "require-dev" in json_dict:
        dependencies["devDependencies"] = []
        for package in json_dict["require-dev"]:
            dependencies["devDependencies"].append(type_indentifier(package))

    #pprint(dependencies)        

    return dependencies

# Parses a "go.mod" file for dependencies
def go_goMod(go_mod_content):
   # Create a temporary directory to act as the module root
    with tempfile.TemporaryDirectory() as tempdir:
        go_mod_path = os.path.join(tempdir, "go.mod")
        # Write go.mod content to the temp directory
        with open(go_mod_path, "w") as f:
            f.write(go_mod_content)
            f.flush()
        try:
            # Run 'go mod edit -json' with cwd set to the temp directory
            result = subprocess.run(
                ["go", "mod", "edit", "-json"],
                cwd=tempdir,
                capture_output=True,
                text=True,
                check=True
            )
            # Load json data originated from the output of the command
            mod_data = json.loads(result.stdout)
            #print(json.dumps(mod_data, indent=2))
        except subprocess.CalledProcessError as e:
            print("Return code:", e.returncode)
            print("Output:", e.output)
            print("Stderr:", e.stderr)
    
    # Catches the dependency name excluding the version identifier part that some have
    require_regex = r'^(.*?)(?:\/v\d+(\.\d+)*)?$'
    dependencies = {'necessary':[]}

    # All dependencies listed with 'require'
    for dependency in mod_data['Require']:
        # Get name
        match = re.match(require_regex,dependency["Path"])
        if match:
            name = match.group(1)
            # If indirect dependency, then save it seperatly
            if 'Indirect' in dependency and dependency['Indirect']:
                if 'indirect' not in dependencies:
                    dependencies['indirect'] = []
                dependencies['indirect'].append(type_indentifier(name))
            else:
                dependencies['necessary'].append(type_indentifier(name))
        else:
            print("go.mod - Not a match: " + dependency["Path"])
            input("Press enter to continue")
    
    #pprint(dependencies)
    #print('Necessary: ' + str(len(dependencies['necessary'])) + "    Indirect: " + str(len(dependencies['indirect'])))

    return dependencies

# Parses a "go.sum" file for dependencies
def go_goSum(go_sum_content):
    sum_regex = r'^(.*?)(?:\/v\d+(\.\d+)*)?\s+.+'
    dependencies = []
    names = set()

    # Go through each line from the file
    for line in go_sum_content.splitlines():
        # Get name
        match = re.match(sum_regex,line.strip())
        if match:
            name = match.group(1)
            # If name is not a repeat, add to list
            if name not in names:
                names.add(name)
                dependencies.append(type_indentifier(name))
        else:
            print("go.sum - Not a match: " + line)
            input("Press enter to continue")

    #pprint(dependencies)

    return dependencies

# Parses a "cargo.toml" file for dependencies
def rust_cargoToml(toml_content,recursive):
    if not recursive:
        toml_dict = toml.loads(toml_content)
        #pprint(toml_dict)
        #print("||\n\/")
    else:
        toml_dict = toml_content

    dependencies = {}

    # Add dependencies shared by members in a workplace
    if 'workspace' in toml_dict.keys():
        if 'dependencies'in toml_dict['workspace']:
            dependencies['workspaceDependencies'] = []
            for dependency in toml_dict['workspace']['dependencies']:
                dependencies['workspaceDependencies'].append(type_indentifier(dependency))
    
    # Add dependencies present in the cargo
    if 'dependencies' in toml_dict.keys():
        dependencies['necessary'] = []
        for dependency in toml_dict['dependencies']:
            dependencies['necessary'].append(type_indentifier(dependency))
    
    # Add dev dependencies present in the cargo
    if 'dev-dependencies' in toml_dict.keys():
        dependencies['devDependencies'] = []
        for dependency in toml_dict['dev-dependencies']:
            dependencies['devDependencies'].append(type_indentifier(dependency))
    
    # Add build dependencies present in the cargo
    if 'build-dependencies' in toml_dict.keys():
        dependencies['buildDependencies'] = []
        for dependency in toml_dict['build-dependencies']:
            dependencies['buildDependencies'].append(type_indentifier(dependency))

    # Cargos may have dependencies limited by certain targets, like OS
    if 'target' in toml_dict.keys():
        dependencies['target'] = {}
        # Store dependency by target
        for target in toml_dict['target']:
            for dependency in toml_dict['target'][target]:
                # Get target dependencies recursively
                dependencies['target'][target] = rust_cargoToml(toml_dict['target'][target],True)
    
    #if not recursive:
    #    pprint(dependencies)
    #    print("---------------------------------------------------------")

    return dependencies

# Parses a ".cproj",".vbproj" or ".fsproj" file (.Net) for dependencies
def dotNet_proj(xml_content,framework_tfm):
    tfms = set()

    root = ET.fromstring(xml_content)
    dependencies = {}
    
    # Find all of the 'PackageReference' elements
    if root.findall('.//PackageReference'):
        dependencies['packageReference'] = []
    for dependency in root.findall('.//PackageReference'):
        # Package name is in 'Include' atribute
        package = dependency.attrib
        if 'Include' in package:
            print("in PackageReference: " + package['Include'])
            if package['Include'] != None:
                # Separate package name from other atributes in cases where they are specified in the same string
                raw_name = package['Include'].split(',')[0]
                # Eliminate dynamic versions from the dependency name '$({version_sub}).' and groups '@({item_group_name})'
                name = re.sub(r'[\$@]\([^)]*\)\.?', '', raw_name)
                if name != '':
                    dependencies['packageReference'].append(type_indentifier(name))
    
    # Find all of the 'Reference' elements
    if root.findall('.//Reference'):
        dependencies['reference'] = []
    for dependency in root.findall('.//Reference'):
        # Package name is in 'Include' atribute
        package = dependency.attrib
        if 'Include' in package:
            #print(package['Include'])
            print("in Reference: " + package['Include'])
            if package['Include'] != None:
                # Separate package name from other atributes in cases where they are specified in the same string
                raw_name = package['Include'].split(',')[0]
                # Eliminate dynamic versions from the dependency name '$({version_sub}).' and groups '@({item_group_name})'
                name = re.sub(r'[\$@]\([^)]*\)\.?', '', raw_name)
                if name != '':
                    dependencies['reference'].append(type_indentifier(name))

    # Find all of the 'TargetFramework' elements
    if root.findall('.//TargetFramework'):
        dependencies.setdefault('frameworks', [])
        for target in root.findall('.//TargetFramework'):
            if target.text != None:
                tfm = target.text
                tfms.add(tfm)

    # Find all of the 'TargetFrameworks' elements
    if root.findall('.//TargetFrameworks'):
        dependencies.setdefault('frameworks', [])
        for target in root.findall('.//TargetFrameworks'):
            #print("in TargetFrameworks: " + target.text)
            if target.text != None:
                tfm_text = target.text.split(';')
                for tfm in tfm_text:
                    tfms.add(tfm)

    # Identify all of the frameworks from the tfms gathered
    if tfms:
        dotNet_frameworks = type_indentifier(tfms,{'type':'dotNet_framework','data':framework_tfm})
        dependencies['frameworks'] = dotNet_frameworks

    #print(tfms)
    #print(dotNet_frameworks)
    #pprint(dependencies)

    return dependencies

def dotNet_packagesConfig(xml_content,framework_tfm):
    root = ET.fromstring(xml_content)
    dependencies = {}
    tfms = set()
    
    # Find all of the 'package' elements
    if root.findall('.//package'):
        dependencies['package'] = []
    for dependency in root.findall('.//package'):
        # Package name is in 'id' atribute
        package = dependency.attrib
        if 'id' in package:
            #print(package['id'])
            # Separate package name from other atributes in cases where they are specified in the same string
            raw_name = package['id'].split(',')[0]
            # Eliminate dynamic versions from the dependency name '$({version_sub}).' and groups '@({item_group_name})'
            name = re.sub(r'[\$@]\([^)]*\)\.?', '', raw_name)
            if name != '':
                 dependencies['package'].append(type_indentifier(name))
        
        # Gather tfms to use to identify frameworks targeted 
        if 'targetFramework' in package and package['targetFramework'] != None:
            tfms.add(package['targetFramework'])
        
        # Identify all of the frameworks from the tfms gathered
        if tfms:
            dotNet_frameworks = type_indentifier(tfms,{'type':'dotNet_framework','data':framework_tfm})
            dependencies['frameworks'] = dotNet_frameworks
    
    #pprint(dependencies)

    return dependencies

# Loads a file's content (for debug)
def load_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


# ------------------------------- FOR TESTING ONLY -------------------------------

#py_pyproject(load_file("dependency_examples/py/requests.toml"))
#js_packageJson(load_file("dependency_examples/js/package.json"))
#js_yarnLock(load_file("dependency_examples/js/yarn.lock"))
#py_requirements(load_file("dependency_examples/py/requirements.txt"))
#java_pomXML(load_file("dependency_examples/java/pom4.xml"))
#ruby_gemfile(load_file("dependency_examples/ruby/Gemfile"))
#php_composerJson(load_file("dependency_examples/php/composer2.json"))
#go_goMod(load_file("dependency_examples/go/go.mod"))
#go_goSum(load_file("dependency_examples/go/go.sum"))
#rust_cargoToml(load_file("dependency_examples/rust/Cargo.toml"),False)
#rust_cargoToml(load_file("dependency_examples/rust/Cargo2.toml"),False)
#rust_cargoToml(load_file("dependency_examples/rust/Cargo3.toml"),False)
#dotNet_proj(load_file("dependency_examples/dotnet/ex1.csproj"))
#dotNet_proj(load_file("dependency_examples/dotnet/ex2.csproj"))
#dotNet_proj(load_file("dependency_examples/dotnet/ex3.csproj"))
#dotNet_proj(load_file("dependency_examples/dotnet/ex4.csproj"))
#dotNet_proj(load_file("dependency_examples/dotnet/ex5.fsproj"))
#dotNet_proj(load_file("dependency_examples/dotnet/ex6.vbproj"))
#dotNet_packagesConfig(load_file("dependency_examples/dotnet/packages.config"))