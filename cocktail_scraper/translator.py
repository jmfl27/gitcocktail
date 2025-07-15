import json
from graph_gen.odlc import generate_graph

# Nested dictionary cases
nested_cases = ['optional','groups','target']

"""
def list_to_tuple(obj):
    if isinstance(obj, list):
        return tuple(list_to_tuple(x) for x in obj)
    return obj

def restore_tuples(repo):
    if "ingredients" in repo and "dependencies" in repo["ingredients"]:    
            restoration = repo["ingredients"]    
            for type in restoration["dependencies"]:
                if type in nested_cases:
                    for sub in restoration["dependencies"][type]:
                        restoration["dependencies"][type][sub] = list_to_tuple(restoration["dependencies"][type][sub])
                else:
                    restoration["dependencies"][type] = list_to_tuple(restoration["dependencies"][type])
            
            repo["ingredients"] = restoration
    
    return repo
"""

# Creates tuples from a list of ingredients found in dependency files
def dependency_tuples(list,already_used,app_name,cocktail_name):
    ontology = ""

    for ingredient in list:
        if ingredient["name"] not in already_used:
            # Resource triples
            if ingredient["type"] == "Resource":
                ontology += ingredient["name"] + " = iof => Resource;\n"
                ontology += ingredient["name"] + " = supports => " + app_name + ";\n"
            else:
                # Remaining triples
                ontology += ingredient["name"] + " = iof => " + ingredient["type"] + ";\n"
                ontology += ingredient["name"] + " = pof => " + cocktail_name + ";\n"
                
                if "associated_languages" in ingredient:
                    # Library
                    if ingredient["type"] == "Library":
                        for lang in ingredient["associated_languages"]:
                            ontology += ingredient["name"] + " = extends => " + lang + ";\n"
                    # Framework
                    elif ingredient["type"] == "Framework":
                        for lang in ingredient["associated_languages"]:
                            ontology += ingredient["name"] + " = encloses => " + lang + ";\n"       
                    # Tool
                    else:
                        for lang in ingredient["associated_languages"]:
                            ontology += ingredient["name"] + " = supports => " + lang + ";\n"
                
                if "associated_tasks" in ingredient:
                    for task in ingredient["associated_tasks"]:
                        ontology += ingredient["name"] + " = is_used_for => " + task + ";\n"
        
        already_used.add(ingredient["name"])

    return (ontology,already_used)
            
# Uses the repository data to build the Cocktail Ontology
def translate_data(repo_data):
    already_used = set()

    # Set names of entities to be used many times in the ontology
    app_name = repo_data["name"]
    dev_name = repo_data["name"] + "Development"
    cocktail_name = repo_data["name"] + "Cocktail"

    ontology = """
        Ontology OntoCoq

concepts {
        System,
        Resource,
        Development,
        Task,
        Cocktail,
        Ingredient,
        Language,
        Library,
        Framework,
        Tool

        % Tasks:
    """
    # Tasks
        # if tasks ontology += ","
    ontology += """
    }

    % Individuals
    individuals {
"""
    # Individuals
    # Instantiate the app, its development and its cocktail
    ontology += app_name + ",\n" + dev_name + ",\n"+ cocktail_name

    # Instantiate all languages
    if "languages" in repo_data:
        for lang in repo_data["languages"]:
                ontology += ",\n" + lang

    # Instantiate all ingredients   
    if "ingredients" in repo_data and "dependencies" in repo_data["ingredients"]:
        for dep_type, dep_value in repo_data["ingredients"]["dependencies"].items():
            if dep_type != "target":
                if dep_type in nested_cases:
                    # dep_value is a dict of sub-dependencies
                    for sub in dep_value:
                        for ingredient in dep_value[sub]:
                            if ingredient["name"] not in already_used:
                                ontology += ",\n" + ingredient["name"]
                                already_used.add(ingredient["name"])
                else:
                    # dep_value is a list of ingredients
                    for ingredient in dep_value:
                        if ingredient["name"] not in already_used:
                            ontology += ",\n" + ingredient["name"]
                            already_used.add(ingredient["name"])
            else:
                # 'target' case for cargo.toml are more nested than usual, thus special treatment
                for target in dep_value:
                        # sub can be 'necessary', 'devDependency', etc...
                        for sub in dep_value[target]:
                            for ingredient in dep_value[target][sub]:
                                if ingredient["name"] not in already_used:
                                    ontology += ",\n" + ingredient["name"]
                                    already_used.add(ingredient["name"])


    ontology += """
    }

    relationships {
        uses,
        contains,
        requires,
        supports,
        is_used_for,
        extends,
        encloses
    }

    triples {
        % Plano conceitual:
        System = requires => Development;
        Resource = supports => System;
        Development = uses => Cocktail;

        Task = pof => Development;
        Ingredient = pof => Cocktail;
        Ingredient = is_used_for => Task;

        Language = isa => Ingredient;
        Library = isa => Ingredient;
        Framework = isa => Ingredient;
        Tool = isa => Ingredient;
        Library = extends => Language;
        Framework = encloses => Language;
        Tool = supports => Language;  
"""
    # Triples
    # System triples
    ontology += app_name + " = iof => System;\n"
    ontology += dev_name + " = iof => Development;\n"
    ontology += cocktail_name + " = iof => Cocktail;\n"

    ontology += app_name + " = requires => " + dev_name + ";\n"
    ontology += dev_name + " = uses => " + cocktail_name + ";\n"

    # Task triples
    if "ingredients" in repo_data and "tasks" in repo_data["ingredients"]:
        for task in repo_data["ingredients"]["tasks"]:
            ontology += task + " = isa => Task;\n"
            ontology += task + " = pof => " + dev_name + ";\n"

    already_used.clear()

    # Ingredient triples
    #   Language triples
    if "languages" in repo_data:
        for lang in repo_data["languages"]:
                ontology += lang + " = iof => Language;\n"
                ontology += lang + " = pof => " + cocktail_name +";\n"
                # is_used_for => Task

    if "ingredients" in repo_data:
        # Dependency ingredient tuples
        if "dependencies" in repo_data["ingredients"]:
            for dep_type, dep_value in repo_data["ingredients"]["dependencies"].items():
                if dep_type != "target":
                    if dep_type in nested_cases:
                        # dep_value is a dict of sub-dependencies
                        for sub in dep_value:
                            result = dependency_tuples(dep_value[sub],already_used,app_name,cocktail_name)
                            # Update ontology with result
                            ontology += result[0]
                            # Update set of used names
                            already_used = result[1]
                    else:
                        result = dependency_tuples(dep_value,already_used,app_name,cocktail_name)
                        ontology += result[0]
                        already_used = result[1]
                else:
                    # 'target' case for cargo.toml are more nested than usual, thus special treatment
                    for target in dep_value:
                            # sub can be 'necessary', 'devDependency', etc...
                            for sub in dep_value[target]:
                                result = dependency_tuples(dep_value[target][sub],already_used,app_name,cocktail_name)
                                ontology += result[0]
                                already_used = result[1]

    ontology += """
    }
.
"""

    return ontology

# Makes ontologies from data loaded from a JSON file, generates the corresponding graph and saves them localy (for debug, requires empty "generated_ontologies" folder)
def test_ontology():
    ontology_data = []

    with open("processed_data.json") as f:
        data = json.load(f)
        for repo in data:
            print(repo["name"])
            ontology = translate_data(repo)
            ontology_data.append({"name":repo["name"],"cocktail":ontology})
            filename = "generated_ontologies/" + repo["name"] + "_ontology.txt"

            # Write the data to the file
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(ontology)
            
            generate_graph(repo["name"],ontology,True)
            

    # File handling
    filename = "ontology_data.json"

    # Write the updated data back to the file
    with open(filename, 'w') as f:
        json.dump(ontology_data, f, indent=4)  

#test_ontology()