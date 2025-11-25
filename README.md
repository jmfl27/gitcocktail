# GitCocktail

GitCocktail was developed as part of my Master's Dissertation in Informatics Engineering at Universidade do Minho, where I was supervised by Professor Pedro Rangel Henriques and Alvaro Costa Neto.

## What is GitCocktail?
GitCocktail is a web application developed in Python and the Flask framework that allows users to generate **Cocktail Identity Cards (CIC)** of public or user-owned code repositories hosted on GitHub.

A CIC is a representation of a project's **Programming Cocktail**, an agglomerate of computer programming technologies that are used to develop a specific software application, characterized by its **Ingredients**, the distinct components that comprise it (languages, frameworks, libraries, and tools). They are specified through the use of **OntoCoq**, an ontology built on the **OntoDL** domain-specific language, created by Alvaro Costa Neto for a previous related work.

The application is comprised of three distinct components:

- The **scraper** ([`scraper.py`](app/cocktail_scraper/scraper.py)), responsible for making requests to various endpoints of the GitHub API in order to obtain the relevant data needed to instantiate the CIC;

- The **data processor** ([`data_processor.py`](app/cocktail_scraper/data_processor.py)), that processes the raw data to identify possible Ingredients, mainly through the use of dependency file parsers ([`dependencies_parser.py`](app/cocktail_scraper/dependencies_parser.py));

- Lastly, the **translator** ([`translator.py`](app/cocktail_scraper/translator.py)) utilizes the data to instantiate the complete ontology and the CIC (a shorter version of the complete ontology), as well as, optionally, a graph that represents it.

## Using GitCocktail
GitCocktail can be initialized directly through the execution of the [`app.py`](app/app.py) Python file or through the use of the [`Dockerfile`](Dockerfile) present in the repository, with the web application being exposed on port `50100`. It can also be accessed online at [gitcocktail.epl.di.uminho.pt](https://gitcocktail.epl.di.uminho.pt).

To generate a CIC, a user needs to input the URL corresponding to a GitHub repository of their choosing and a valid personal access token (see [this page](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)). This repository must be public or owned by the account from which the token was generated. Afterwards, a results page will be shown where users can observe the generated CIC, its complete ontology version, download them, and lastly, generate the CIC's graph as an additional feature.

## Related Works

**TBA**
