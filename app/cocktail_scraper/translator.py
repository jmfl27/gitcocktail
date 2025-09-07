import json
from .graph_gen.odlc import generate_graph

# for identation
small_tab = "        "
big_tab = "                "

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
                ontology += big_tab + ingredient["name"] + " = iof => Resource;\n"
                ontology += big_tab + ingredient["name"] + " = supports => " + app_name + ";\n"
            else:
                # Remaining triples
                ontology += big_tab + ingredient["name"] + " = iof => " + ingredient["type"] + ";\n"
                ontology += big_tab + ingredient["name"] + " = pof => " + cocktail_name + ";\n"
                
                if "associated_languages" in ingredient:
                    # Library
                    if ingredient["type"] == "Library":
                        for lang in ingredient["associated_languages"]:
                            ontology += big_tab + ingredient["name"] + " = extends => " + lang + ";\n"
                    # Framework
                    elif ingredient["type"] == "Framework":
                        for lang in ingredient["associated_languages"]:
                            ontology += big_tab + ingredient["name"] + " = encloses => " + lang + ";\n"       
                    # Tool
                    else:
                        for lang in ingredient["associated_languages"]:
                            ontology += big_tab + ingredient["name"] + " = supports => " + lang + ";\n"
                
                # "Ingredient" is used in "Task(s)"
                if "associated_tasks" in ingredient:
                    for task in ingredient["associated_tasks"]:
                        ontology += big_tab + ingredient["name"] + " = is_used_for => " + task + ";\n"
        
        already_used.add(ingredient["name"])

    return (ontology,already_used)
            
# Uses the repository data to build the Cocktail Ontology or a Cocktail Identity Card (CIC)
def translate_data(repo_data,is_cic):
    already_used = set()
    ingredient_types = repo_data["ingredient_types"]
    print(ingredient_types)

    # Set names of entities to be used many times in the ontology
    app_name = repo_data["name"]
    dev_name = repo_data["name"] + "Development"
    cocktail_name = repo_data["name"] + "Cocktail"

    ontology = """
    Ontology OntoCoq

        concepts {
    """
    
    # Trim down the ontology for the CIC: no Sys, Ing, Ckt or Dev concepts (individuals take their place)
    if not is_cic:
                ontology += """
                System,
                Ingredient,
                Cocktail,
                Development,
"""
    ontology += """
                Resource,
                Task,
                Language"""
    if not is_cic:
        ontology += """,
                Library,
                Framework,
                Tool
    """
    # Trim down the ontology for the CIC: only instantiate all ingredient type concepts that are present in tuples
    else:
        for type in ingredient_types:
            ontology += ",\n" + big_tab + type
    
    # Tasks
        # if tasks ontology += ",/n% Tasks:"
    ontology += """
        }

        % Individuals
        individuals {
"""
    # Individuals
    # Instantiate the app, its development and its cocktail
    ontology += big_tab + app_name + ",\n" + big_tab + dev_name + ",\n" + big_tab + cocktail_name

    # Instantiate all languages
    if "languages" in repo_data:
        for lang in repo_data["languages"]:
                ontology +=  ",\n" + big_tab + lang

    # Instantiate all ingredients   
    if "ingredients" in repo_data and "dependencies" in repo_data["ingredients"]:
        for dep_type, dep_value in repo_data["ingredients"]["dependencies"].items():
            if dep_type != "target":
                if dep_type in nested_cases:
                    # dep_value is a dict of sub-dependencies
                    for sub in dep_value:
                        for ingredient in dep_value[sub]:
                            if ingredient["name"] not in already_used:
                                ontology += ",\n" + big_tab + ingredient["name"]
                                already_used.add(ingredient["name"])
                else:
                    # dep_value is a list of ingredients
                    for ingredient in dep_value:
                        if ingredient["name"] not in already_used:
                            ontology += ",\n" + big_tab + ingredient["name"]
                            already_used.add(ingredient["name"])
            else:
                # 'target' case for cargo.toml are more nested than usual, thus special treatment
                for target in dep_value:
                        # sub can be 'necessary', 'devDependency', etc...
                        for sub in dep_value[target]:
                            for ingredient in dep_value[target][sub]:
                                if ingredient["name"] not in already_used:
                                    ontology += ",\n" + big_tab + ingredient["name"]
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
    """

    # Complete ontology
    if not is_cic:
        ontology += """
                % Conceptual plan: 
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
    # Trim down the ontology for the CIC: no tuples with the Sys, Ing, Ckt or Dev concepts (individuals take their place)
    #                                     as well as no "extends", "supports" and "encloses" tuples
    else:
        ontology += small_tab + "    " + "% Conceptual plan:\n" + big_tab + "Resource = supports => " + app_name + ";\n"
        ontology += big_tab + "Task = pof => " + dev_name + ";\n\n"
    
    # Triples
    # System triples

    # Complete ontology
    if not is_cic:
        ontology += big_tab + app_name + " = iof => System;\n"
        ontology += big_tab + dev_name + " = iof => Development;\n"
        ontology += big_tab + cocktail_name + " = iof => Cocktail;\n"

    ontology += big_tab + app_name + " = requires => " + dev_name + ";\n"
    ontology += big_tab + dev_name + " = uses => " + cocktail_name + ";\n"

    # Task triples
    if "ingredients" in repo_data and "tasks" in repo_data["ingredients"]:
        for task in repo_data["ingredients"]["tasks"]:
            ontology += big_tab + task + " = isa => Task;\n"
            ontology += big_tab + task + " = pof => " + dev_name + ";\n"

    already_used.clear()

    # Ingredient triples
    #   Language triples
    if "languages" in repo_data:
        for lang in repo_data["languages"]:
                ontology += big_tab + lang + " = iof => Language;\n"
                ontology += big_tab + lang + " = pof => " + cocktail_name +";\n"
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

# Generates a repository's ontology and Cocktail Identity Card
def generate_cic(repo_data):
    ontology = translate_data(repo_data,False)
    cic = translate_data(repo_data,True)
    result = {
        "name": repo_data["name"],
        "ingredient_count": repo_data["ingredient_count"],
        "ontology": ontology,
        "cic": cic
    }

    return result

def generate_graph_dot(name, cic):
    dot = generate_graph(name, cic, True, True, False)
    return dot

# Makes ontologies from data loaded from a JSON file, generates the corresponding graph and saves them localy (for debug, requires empty "generated_ontologies" folder)
def test_ontology():
    ontology_data = []

    with open("processed_data.json") as f:
        data = json.load(f)
        for repo in data:
            print(repo["name"])
            ontology = translate_data(repo,False)
            cic = translate_data(repo,True)
            ontology_data.append({"name":repo["name"],"ontology":ontology,"cic":cic})

            # Save ontology
            onto_filename = "generated_ontologies/" + repo["name"] + "_ontology.txt"

            # Write the data to the file
            with open(onto_filename, 'w', encoding='utf-8') as file:
                file.write(ontology)
            
            generate_graph(repo["name"],ontology,False,True)

            # Save CIC
            cic_filename = "generated_ontologies/" + repo["name"] + "_cic.txt"

            # Write the data to the file
            with open(cic_filename, 'w', encoding='utf-8') as file:
                file.write(cic)
            
            generate_graph(repo["name"],cic,True,True)
            

    # File handling
    filename = "ontology_data.json"

    # Write the updated data back to the file
    with open(filename, 'w') as f:
        json.dump(ontology_data, f, indent=4)  

#test_ontology()