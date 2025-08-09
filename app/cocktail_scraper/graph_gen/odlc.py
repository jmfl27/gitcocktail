#!/opt/homebrew/bin/python3.11

import sys
import graphviz
from lark import Lark, Transformer

class DotTranslator(Transformer):
    def __init__(self):
        self.ontology = ''
        self.concepts = []
        self.individuals = []
        self.relations = []
        self.triples = []

    def string(self, children):
        (s,) = children
        return s[1:-1]

    def number(self, children):
        (n,) = children
        return float(n)

    def start(self, children):
        self.ontology = children[1]

    def concept_decl(self, children):
        concept = f'\"{children[0]}\" [shape=ellipse, style=filled, color=turquoise4];'
        self.concepts.append(concept)

    def individual_decl(self, children):
        individual = f'\"{children[0]}\" [shape=rectangle, style=filled, color=goldenrod];'
        self.individuals.append(individual)

    def relation_decl(self, children):
        (relation,) = children
        self.relations.append(relation)

    def src(self, children):
        (s,) = children
        return s

    def rel(self, children):
        (r,) = children
        return r

    def dst(self, children):
        (d,) = children
        return d

    def triple_decl(self, children):
        edge_properties = ''
        if children[1] == 'iof': edge_properties = ', style=dashed'
        triple = f'"{children[0]}"->"{children[2]}" [label="{children[1]}"{edge_properties}];'
        self.triples.append(triple)

    def dot(self):
        result = f'digraph {self.ontology} {{'
        for concept in self.concepts:
            result += concept
        for individual in self.individuals:
            result += individual
        for triple in self.triples:
            result += triple
        result += "}"
        return result

# Generates the corresponding ontology's graph
def generate_graph(name,ontology,is_cic,to_site,debug=None):
    with open('cocktail_scraper/graph_gen/ontodl.lark') as grammar_file:
        parser = Lark(grammar_file.read())
        #with open(sys.argv[1]) as source_file:
        tree = parser.parse(ontology)
        translator = DotTranslator()
        translator.transform(tree)
        dot_source = graphviz.Source(translator.dot())
        if is_cic:
            if to_site:
                return dot_source
            elif debug:
                dot_source.render('generated_ontologies/' + name + '_cic')
            else:
                dot_source.render(name + '_cic', cleanup=True)
        else:
            if debug:
                dot_source.render('generated_ontologies/' + name + '_ontology')
            else:
                dot_source.render(name + '_ontology', cleanup=True)