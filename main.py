from antlr4 import *
from JavaLexer import JavaLexer
from JavaParser import JavaParser
from antlr4.tree.Trees import Trees
from antlr4 import ParserRuleContext, TerminalNode
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem
import json
from bs4 import BeautifulSoup
import requests
from g4f.client import Client
import spacy
import os

all_imports = set()
nlp = spacy.load("en_core_web_lg")
input_file = "./test_files/input_file.java" # Change last portion to a test file  # Program output file will be stored in test_files by default
program_output_file = open(f'{input_file}_output.txt', 'w')
file_path = "classification_data.txt"
client = Client()

messages = [
    {"role": "system",
     "content": "You are attempting to classify the inputted description into one of the 31 labels based off of the simularity to it."},
    {"role": "system",
     "content": "As you guess this, your final response should only be one concise paragraph with the label chosen and why."},
    {"role": "system",
     "content": "Please do not add any pleasantries, please only output the result and why it fits it that category."},
    {"role": "system",
     "content": "please answer in the format of: Label: givenlabel"
     						"Reason: reasonwhy"}
]

messages_overload_summ = [
	{"role": "system",
	"content" : "You are attempting to comprise, summarize, or paraphrase the content of a programming function method with multiple overloads with individual parameters and descriptions into one concise Method title and summary."},
	{"role": "system", 
	"content": "Please do not add any pleasantries, please only output the result."},
	{"role": "system",
	"content": "Please answer in the format of: Summary: summary"},
	
]

messages_description_summ = [	{"role": "system",
	"content" : "You are attempting to summarize or paraphrase the content of a description into a concise and accurate summary of the passed content."},
	{"role": "system", 
	"content": "As you guess this, your final response should only be one concise paragraph with your paraphrased summary or description without reference links or acknowledgements of prompts."},
	{"role": "system", 
	"content": "Please do not add any pleasantries, please only output the result and why it fits it that category."},
	{"role": "system",
	"content": "Please answer in the format of: description"},
	]

class ParseTreeViewer(QWidget):
    def __init__(self, parse_tree, tree):
        super().__init__()
        self.setWindowTitle("Parse Tree Viewer")
        self.setGeometry(100, 100, 800, 600)
        layout = QVBoxLayout()
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Parse Tree"])
        layout.addWidget(self.tree_widget)
        self.setLayout(layout)
        self.setup_parse_tree_in_widget(parse_tree)  # Adjusted to directly use parse_tree
        self.export_parse_tree_to_json(tree, f"{input_file}_parse_tree.json")

    def setup_parse_tree_in_widget(self, parse_tree, parent_item=None):
        self.tree_widget.setHeaderLabels(["Parse Tree"])
        parent_item = QTreeWidgetItem(self.tree_widget)
        self.add_children(parent_item, parse_tree)
        QTreeWidgetItem(parent_item, ["<EOF>"])  # Add <EOF> as the final part

    def get_node_text(self, node):
        if isinstance(node, TerminalNode):
            return node.getText()
        elif isinstance(node, ParserRuleContext):
            # Use the rule name as text for ParserRuleContext nodes.
            return type(node).__name__
        else:
            # Fallback for any other types of nodes.
            return 'Unknown Node'

    def add_children(self, parent_item, text):
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1]
        newText = ""
        start = 0
        for i in range(start, len(text)):
            if text[i] != ")" and text[i] != "(":
                newText += text[i]
            else:
                break
        item = QTreeWidgetItem(parent_item, [newText])
        start_index = 0
        while True:
            start = text.find("(", start_index)
            if start == -1:
                break
            count = 1
            for i in range(start + 1, len(text)):
                if text[i] == "(":
                    count += 1
                elif text[i] == ")":
                    count -= 1
                    if count == 0:
                        end = i
                        break
            else:
                return
            self.add_children(item, text[start:end + 1])
            start_index = end + 1

    def display_parse_tree(self, parse_tree):
        # Set up the tree widget for displaying the parse tree
        self.tree_widget.setHeaderLabels(["Parse Tree"])
        parent_item = QTreeWidgetItem(self.tree_widget)
        self.add_children(parent_item, parse_tree)
        QTreeWidgetItem(parent_item, ["<EOF>"])  # Add <EOF> as the final part

    def determine_role(node_type):
        # Example role determination logic
        if node_type in ['IfStatement', 'ForStatement', 'WhileStatement']:
            return 'conditional'
        elif 'Function' in node_type or 'Method' in node_type:
            return 'function'
        elif 'compilationUnitContext' in node_type or 'compiler' in node_type or 'compilation' in node_type:
            return 'compiler'
        elif 'QualifiedNameContext' in node_type:
            return 'type reference'
        elif 'ImportDeclarationContext' in node_type:
            return 'import'
        elif 'ClassDeclarationContext' in node_type:
            return 'class declaration'
        elif 'MethodDeclarationContext' in node_type:
            return 'method declaration'
        elif 'VariableDeclaratorContext' in node_type or 'FieldDeclarationContext' in node_type:
            return 'variable declaration'
        elif 'Literal' in node_type:
            return 'literal value'
        elif 'ExpressionContext' in node_type:
            return 'expression'
        elif 'Modifier' in node_type:
            return 'modifier'
        elif 'Annotation' in node_type:
            return 'annotation'
        elif 'Parameter' in node_type:
            return 'parameter'
        elif 'GenericType' in node_type or 'TypeParameter' in node_type:
            return 'generic type'
        elif 'Comment' in node_type:
            return 'comment'
        elif 'SwitchCase' in node_type:
            return 'switch case'
        elif 'TryCatch' in node_type:
            return 'try-catch block'
        # Add more conditions here based on your grammar and AST structure
        else:
            return 'unknown'

    @staticmethod
    def parse_tree_to_dict(node):
        # Determine the node type and its role in the AST
        if isinstance(node, TerminalNode):
            # Terminal nodes often represent literals, identifiers, etc.
            text = node.getText()
            node_type = 'TERMINAL'
            role = 'identifier' if text.isidentifier() else 'literal'
            return {'type': node_type, 'text': text, 'role': role}

        elif isinstance(node, ParserRuleContext):
            node_type = type(node).__name__
            # Here, you would have logic to determine the role based on node_type
            # For example, if node_type indicates a function declaration, role could be 'function'
            role = ParseTreeViewer.determine_role(node_type)  # Placeholder for role determination logic
            children = [ParseTreeViewer.parse_tree_to_dict(child) for child in node.getChildren()]

            return {'type': node_type, 'children': children, 'role': role}

        else:
            return {'type': 'UNKNOWN', 'text': '', 'children': [], 'role': ''}

    @staticmethod
    def export_parse_tree_to_json(parse_tree, filename):
        tree_dict = ParseTreeViewer.parse_tree_to_dict(parse_tree)
        with open(filename, 'w') as file:
            json.dump(tree_dict, file, indent=4)

    # Updated function to traverse the AST and collect found reserved words, found variables, and found node types
    def traverse_ast(self, node, reserved_words, found_reserved_words=[], found_variables=[], found_node_types=[]):
        # Check if the current node is a terminal node
        if isinstance(node, TerminalNode):
            token_text = node.getText()
            if token_text in reserved_words:
                found_reserved_words.append(token_text)
            else:
                # Here you might want to add more conditions to accurately identify variables
                if self.is_java_identifier(token_text) and token_text not in found_variables:
                    found_variables.append(token_text)
            # Regardless of type, the text of a terminal node is its type here
            node_type = 'TERMINAL'
            if node_type not in found_node_types:
                found_node_types.append(node_type)

        # If the node is a ParserRuleContext (non-terminal), collect its type and visit all its children
        elif isinstance(node, ParserRuleContext):
            node_type = type(node).__name__
            if node_type not in found_node_types:
                found_node_types.append(node_type)

            if node.children is not None:  # Check if children is not None
                for child in node.children:
                    self.traverse_ast(child, reserved_words, found_reserved_words, found_variables, found_node_types)

        return found_reserved_words, found_variables, found_node_types

    def is_java_identifier(self, text):
        if not text:  # Check if the text is not empty
            return False
        if text[0].isdigit():  # Check if the first character is not a digit
            return False
        if not (text[0].isalpha() or text[0] == '_' or text[0] == '$'):  # Check if the first character is valid
            return False
        for char in text[1:]:  # Check the rest of the characters
            if not (char.isalnum() or char == '_' or char == '$'):
                return False
        return True


def ask_gpt(description, options):
    # Construct the prompt with the object description and option descriptions
    prompt = f"Object Description: {description}\n"
    prompt += f"Options: {options}\n"
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        stream=True
    )
    return response


def ask_gpt_summary(input_messages):
    response = client.chat.completions.create(
        model = "gpt-3.5-turbo",
        messages = input_messages, 
        stream = True
    )
    return response

def extract_class_usages_from_file(file_path):
    imported_classes = set()
    variable_to_class = {}
    variable_to_methods = {}
    package_names = set()

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line in lines:
        if line.strip().startswith('import '):
            full_class_path = line.strip()[7:].rstrip(';')
            all_imports.add(full_class_path)
            if full_class_path.startswith('java.') or full_class_path.startswith('javafx.') or full_class_path.startswith('javax.'):
                imported_classes.add(full_class_path)
                package_name = '.'.join(full_class_path.split('.')[:-1])
                package_names.add(package_name)

    # Separate parsing of class instance creation from method invocation
    for line in lines:
        for full_class_path in imported_classes:
            class_name = full_class_path.split('.')[-1]
            # Check for new instance creation
            if f'new {class_name}' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    variable_name = parts[0].strip().split()[-1]
                    variable_to_class[variable_name] = full_class_path
            # Check for method invocations for existing variables
            for variable, assigned_class in variable_to_class.items():
                if f'{variable}.' in line:
                    method_start = line.find(f'{variable}.') + len(variable) + 1
                    method_end = line.find('(', method_start)
                    if method_end != -1:
                        method_name = line[method_start:method_end].strip()
                        if variable not in variable_to_methods:
                            variable_to_methods[variable] = set()
                        variable_to_methods[variable].add(method_name)

    # Map classes to methods
    class_to_methods = {}
    for variable, full_class_path in variable_to_class.items():
        if full_class_path not in class_to_methods:
            class_to_methods[full_class_path] = set()
        class_to_methods[full_class_path].update(variable_to_methods.get(variable, set()))

    # Convert sets to lists for output consistency
    for class_path, methods in class_to_methods.items():
        class_to_methods[class_path] = list(methods)

    return list(imported_classes), list(package_names), class_to_methods

def find_module_for_package(package_name, modules_to_packages):
    if package_name.startswith('javafx.'):
        return None  # Return None for JavaFX packages
    for module, packages in modules_to_packages:
        if package_name in packages:
            return module
    return "Package not found in any module"
# https://docs.oracle.com/en/java/javase/22/docs/api/java.base/java/io/BufferedInputStream.html
def fetch_method_descriptions(module_name, full_class_name, methods):
    use_new_html_structure = module_name is not None  # False if JavaFX (None), true otherwise
    def construct_base_url(module, package_name):
        if module is None:  # Indicates a JavaFX class
            return f"https://docs.oracle.com/javafx/2/api/{package_name}/"
        else:
            return f"https://docs.oracle.com/en/java/javase/22/docs/api/{module}/{package_name}/"

    # Split the full class name into its package and class name parts
    parts = full_class_name.split('.')
    package_name = '/'.join(parts[:-1])  # Form the package path
    class_name = parts[-1]  # Get the class name
    base_url = construct_base_url(module_name, package_name)

    # Construct the URL to the class documentation page
    class_url = f"{base_url}{class_name}.html"
    print(f"Fetching documentation from: {class_url}")
    program_output_file.write(f"Fetching documentation from: {class_url}")

    # Fetch the content of the class documentation page
    response = requests.get(class_url)
    #print(f"Response status: {response.status_code}")

    # Parse the HTML content of the page
    soup = BeautifulSoup(response.text, 'html.parser')
    method_descriptions = {}

    # Function to search for method descriptions within the provided soup
    def search_method_descriptions(soup, method, use_new_html_structure):
        descriptions = []  # List to store all found descriptions for this method
        # print(f"DEBUG: Starting search for {method} using {'new' if use_new_html_structure else 'old'} HTML structure.")  # Debug statement
        if use_new_html_structure:
            for method_tag in soup.find_all('code'):
                if method in method_tag.text:
                    # print(f"DEBUG: Found method tag for {method}.")  # Debug statement
                    parent_div = method_tag.find_parent('div')
                    if parent_div:
                        next_div = parent_div.find_next_sibling('div')
                        if next_div:
                            description_tags = next_div.find_all('div', class_='block')
                            if description_tags:
                                full_description = ' '.join(d.text.strip() for d in description_tags)
                                descriptions.append(full_description)
                                # print(f"DEBUG: Added description for {method}.")  # Debug statement
        else:  # Old HTML structure, typically used for JavaFX
            for method_tag in soup.find_all('code'):
                if method in method_tag.text:
                    # print(f"DEBUG: Found method tag for {method} in JavaFX documentation.")  # Debug statement
                    td_tag = method_tag.find_parent('td')
                    if td_tag:
                        description_tags = td_tag.find_all('div', class_='block')
                        if description_tags:
                            full_description = ' '.join(d.text.strip() for d in description_tags)
                            descriptions.append(full_description)
                            # print(f"DEBUG: Added description for {method} in JavaFX documentation.")  # Debug statement
        if not descriptions:
            print(f"No descriptions found for {method}.")  # Debug statement
            program_output_file.write(f"No descriptions found for {method}.")
        return descriptions

    # Search for the documentation of each method in the list
    for method in methods:
        #print(f"Searching for method: {method}")
        descriptions = search_method_descriptions(soup, method, use_new_html_structure)

        # If no description found and not a JavaFX class, look for inherited methods
        if not descriptions and use_new_html_structure:
            # Find the div that contains inherited methods
            inherited_sections = soup.find_all("div", class_="inherited-list")
            for section in inherited_sections:
                # The class name from which methods are inherited is in the 'h3' tag's 'id' attribute
                class_info = section.find('h3')
                if class_info:
                    class_name_from_id = class_info.get('id', '').replace('methods-inherited-from-class-', '').replace(
                        '.', '/')
                    if class_name_from_id:  # Ensure the class name was successfully extracted
                        # print(f"DEBUG: Found inherited section for class: {class_name_from_id}")  # Debug statement
                        # Iterate over all 'a' tags within 'code' elements
                        for link in section.find_all('a'):
                            if method.lower() == link.text.lower():  # Case-insensitive comparison
                                # Extract just the path to the class documentation, not including method specifics
                                inherited_href = link['href']
                                # Assume inherited_href is like "../AbstractQueue.html#element()", need to remove '../' and method specifics
                                inherited_class_path = inherited_href.split('#')[0].replace('../',
                                                                                            '').strip()  # Now should be "AbstractQueue.html"
                                inherited_class = inherited_class_path.replace('.html',
                                                                               '')  # Now should be just "AbstractQueue"

                                # Now we use the class name from the section's id for package structure, which we have already cleaned in class_name_from_id
                                # Assuming class_name_from_id is like "java/util/AbstractQueue", split and join to format correctly
                                if class_name_from_id:
                                    inherited_package_path = '/'.join(class_name_from_id.split('/')[
                                                                      :-1])  # Get the path without the class name itself
                                    inherited_url = f"https://docs.oracle.com/en/java/javase/22/docs/api/{module_name}/{inherited_package_path}/{inherited_class}.html"
                                    # print(f"DEBUG: Fetching documentation from inherited class at {inherited_url}.")
                                    # Proceed with fetching and parsing the inherited documentation
                                inherited_response = requests.get(inherited_url)
                                inherited_soup = BeautifulSoup(inherited_response.text, 'html.parser')
                                descriptions = search_method_descriptions(inherited_soup, method,
                                                                          use_new_html_structure)
                                if descriptions:
                                    # print(f"DEBUG: Found descriptions for {method} in inherited class.")
                                    break  # Stop searching if descriptions are found
                        if descriptions:
                            # print(f"DEBUG: Descriptions found for {method} after checking inherited classes.")
                            break  # Stop searching other inherited sections if found
            if not descriptions:
                print(f"Descriptions for {method} not found in inherited classes either.")  # Debug statement
                program_output_file.write(f"Descriptions for {method} not found in inherited classes either.")

        # Add the found descriptions to the method descriptions dictionary
        if descriptions:
            method_descriptions[method] = descriptions
        else:
            print(f"Method {method} not found in the documentation.")
            program_output_file.write(f"Method {method} not found in the documentation.")

    # Return the collected method descriptions
    return method_descriptions

def fetch_import_description(full_import_name):
    # Split the full class name into its package and class name parts
    parts = full_import_name.split('.')
    package_name = '/'.join(parts[:-1])  # Join all but the last part with '/', to form the package path
    class_name = parts[-1]  # The last part is the class name
    # Determine the base URL based on whether the class is part of JavaFX
    if full_import_name.startswith('javafx.'):
        base_url = f"https://docs.oracle.com/javase/8/javafx/api/{package_name}/"
    else:
        base_url = f"https://docs.oracle.com/javase/8/docs/api/{package_name}/"
    
    class_url = f'{base_url}{class_name}/package-summary.html'
    print(f"Fetching documentation from: {class_url}")  # Debug
    response = requests.get(class_url) 
    print(f"Response status: {response.status_code}")  # Debug
    if response.url != class_url:
    	print(f'Unable to retrieve documentation')
    	class_url = f"{base_url}{class_name}.html"
    	print(f'Fetching documentation from: {class_url}')
    	response = requests.get(class_url)
    	#print(f"Response status: {response.status_code}")
    if response.url == class_url:
        soup = BeautifulSoup(response.text, 'html.parser')
    
        print(f'Fetching description for {full_import_name}: ')
        program_output_file.write(f'\n\nDescription for {full_import_name}:\n')
        description_naming_conventions = [('div', 'docSummary'), ('div', 'description')]
        i = 0
        package_description = False
        while not package_description and i < len(description_naming_conventions):
            package_description = soup.find(description_naming_conventions[i][0], description_naming_conventions[i][1])
            i += 1
        if package_description:
            program_output_file.write(f'Documentation URL: {class_url}\n')
            package_description = package_description.text
            prompt = f'Please summarize the following description concisely and accurately. Description: {package_description}. End of Description.'
            messages_description_summ.append({"role": "user", "content": prompt})
            test = ask_gpt_summary(messages_description_summ)
            answer = ""
            for chunk in test:
                if chunk.choices[0].delta.content:
                    answer += (chunk.choices[0].delta.content.strip('*') or "")
            print(answer.strip('#### '))
            package_description_gpt = answer.strip('#### ')
            package_description = package_description_gpt
            program_output_file.write(answer.strip('#### '))
            messages_description_summ.pop()
            #print(package_description)
        
            options = {
        "Application": "Software components designed by third parties or as plugins to enhance specific functionalities within a system.",
        "Application Performance Manager": "Tools or systems dedicated to monitoring, analyzing, and optimizing the performance of various software applications.",
        "Big Data": "APIs tailored for handling and managing vast amounts of data, encompassing diverse formats and structures.",
        "Cloud": "Software tools and services delivered over the Internet, facilitating remote access, scalability, and flexibility.",
        "Computer Graphics": "Technologies focused on creating, editing, and rendering visual content, encompassing various media formats.",
        "Data Structure": "Patterns and frameworks governing the organization, storage, and manipulation of data, including collections, lists, and trees.",
        "Databases": "Systems and tools for storing, managing, and retrieving structured data and associated metadata.",
        "Software Development and IT": "Libraries and frameworks catering to version control, continuous integration, and deployment processes.",
        "Error Handling": "Strategies and mechanisms designed to detect, respond to, and recover from errors or exceptional conditions within software systems.",
        "Event Handling": "Mechanisms and components responsible for detecting, processing, and responding to events triggered within software applications.",
        "Geographic Information System": "Technologies dealing with the storage, analysis, and visualization of spatially referenced data and geographic information.",
        "Input/Output": "Functionalities and interfaces facilitating the reading from and writing to various data sources and destinations.",
        "Interpreter": "Features and functionalities associated with interpreting and executing code or scripts within a software environment.",
        "Internationalization": "Tools and frameworks enabling the adaptation of software applications to diverse linguistic, cultural, and regional contexts.",
        "Logic": "Frameworks and patterns governing the organization and execution flow of software applications, including control structures and architectural paradigms.",
        "Language": "Features and capabilities inherent to programming languages, including syntax, semantics, and data type conversions.",
        "Logging": "Mechanisms for recording and storing activity and status information generated by software applications for monitoring, debugging, and analysis purposes.",
        "Machine Learning": "Tools and libraries supporting the development, training, and deployment of machine learning models based on data analysis and pattern recognition.",
        "Microservices/Services": "Decomposed and independently deployable software components facilitating modular and scalable application architectures and inter-application communication.",
        "Multimedia": "Technologies enabling the representation and manipulation of information across various media formats, including text, audio, and video.",
        "Multithread": "Support for concurrent execution and management of multiple threads within a software application or system.",
        "Natural Language Processing": "Technologies and algorithms enabling the processing, understanding, and generation of human language data within computational systems.",
        "Network": "Protocols, APIs, and tools facilitating communication and data exchange between networked devices and systems.",
        "Operating System": "Interfaces and functionalities providing access to and management of a computer's hardware and software resources, including system-level APIs.",
        "Parser": "Components and algorithms responsible for analyzing and interpreting data or code structures, often breaking them down into identifiable components for further processing.",
        "Search": "APIs and tools facilitating the retrieval and manipulation of information from various data sources, particularly for web-based searching and indexing.",
        "Security": "Technologies, protocols, and practices aimed at safeguarding data, systems, and communications from unauthorized access, breaches, and malicious activities.",
        "Setup": "Configurations, settings, and initialization processes necessary for setting up and configuring software applications or systems.",
        "User Interface": "Components and frameworks defining the visual and interactive elements of software applications, including forms, screens, and graphical controls.",
        "Utility": "Third party libraries for general-purpose functions and utilities.",
        "Test": "Frameworks and tools facilitating the automation, execution, and management of software testing processes and procedures."
    }
            givenOptions = ""
            similarity_results = []
            for option, descriptions in options.items():
                givenOptions += (option + ": " + descriptions)
                class_desc = nlp(package_description)
                given_desc = nlp(option + ": " + descriptions)
                similarity_results.append(class_desc.similarity(given_desc))
            greatest_value = 0
            greatest_value_index = 0
            for i in range(len(similarity_results)):
                if similarity_results[i] > greatest_value:
                    greatest_value = similarity_results[i]
                    greatest_value_index = i
            # print(greatest_value_index)
            print("\nSimilarity Score: " + str(similarity_results[greatest_value_index].__round__(4)))
            program_output_file.write(f"\nSimilarity Score: {str(similarity_results[greatest_value_index].__round__(4))}\n")
            print(list(options.keys())[greatest_value_index] + ": " + list(options.values())[greatest_value_index] + '\n')
            program_output_file.write(list(options.keys())[greatest_value_index] + ": " + list(options.values())[greatest_value_index] + '\n')
            answer = ""
            if not check_package_in_file(full_import_name):
                response = ask_gpt(package_description, givenOptions)
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        answer += (chunk.choices[0].delta.content.strip('*') or "")
                answer = answer.strip('#### ')
                words = answer.split()
                answer = ''
                counter = 0
                for i, word in enumerate(words):
                    if word == "Reason:":
                        answer += '\n'
                        counter -= i
                    answer += word
                    counter += 1
                    if (counter + 1) % 17 == 0:  # Add newline every x words
                        answer += '\n'
                    else:
                        answer += ' '
                save_data_to_text_file(full_import_name, answer)
            else:
                start = False
                with open(file_path, 'r') as file:
                    for line in file:
                        if not start:
                            words = line.split()
                            if full_import_name in words:
                                start = True
                        elif not 'END' in line:
                            answer += line
                        else:
                            start = False
            print(answer + '\n')
            program_output_file.write(answer + '\n')
        
        else: 
    	    print(f'Could not retrieve description for {full_import_name}\n')
    	    program_output_file.write(f'Could not retrieve description for {full_import_name}\n')
    else: 
        print(f'Could not retrieve documentation for {full_import_name}\n')
        program_output_file.write(f'Could not retrieve documentation for {full_import_name}\n')
def save_data_to_text_file(package, description):
    with open(file_path, 'a') as file:
        file.write("\n{}\n".format(package))
        file.write("{}\n".format(description))
        file.write("END\n")

def check_package_in_file(package_name):
    with open(file_path, 'r') as file:
        for line in file:
            words = line.split()
            if package_name in words:
                return True
    return False  
def main():
    # Correctly formatted reserved words list
    reserved_words = [
        "EOF", "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const", "continue",
        "default", "do", "double", "else", "enum", "extends", "final", "finally", "float", "for", "if", "goto",
        "implements", "import", "instanceof", "int", "interface", "long", "native", "new", "package", "private",
        "protected", "public", "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this",
        "throw", "throws", "transient", "try", "void", "volatile", "while", "integerliteral", "floatingpointliteral",
        "booleanliteral", "characterliteral", "stringliteral", "nullliteral", "lparen", "rparen", "lbrace", "rbrace",
        "lbrack", "rbrack", "semi", "comma", "dot", "assign", "gt", "lt", "bang", "tilde", "question", "colon", "equal",
        "le", "ge", "notequal", "and", "or", "inc", "dec", "add", "sub", "mul", "div", "bitand", "bitor", "caret",
        "mod", "add_assign", "sub_assign", "mul_assign", "div_assign", "and_assign", "or_assign", "xor_assign",
        "mod_assign", "lshift_assign", "rshift_assign", "urshift_assign", "identifier", "at", "ellipsis", "ws",
        "comment", "line_comment"
    ]
    Java_modules_to_packages = [
        ('java.base', ['java.io', 'java.lang', 'java.lang.annotation', 'java.lang.constant', 'java.lang.foreign',
                       'java.lang.invoke', 'java.lang.module', 'java.lang.ref', 'java.lang.reflect',
                       'java.lang.runtime', 'java.math',
                       'java.net', 'java.net.spi', 'java.nio', 'java.nio.channels', 'java.nio.channels.spi',
                       'java.nio.charset',
                       'java.nio.charset.spi', 'java.nio.file', 'java.nio.file.attribute', 'java.nio.file.spi',
                       'java.security',
                       'java.security.cert', 'java.security.interfaces', 'java.security.spec', 'java.text',
                       'java.text.spi', 'java.time',
                       'java.time.chrono', 'java.time.format', 'java.time.temporal', 'java.time.zone', 'java.util',
                       'java.util.concurrent', 'java.util.concurrent.atomic', 'java.util.concurrent.locks',
                       'java.util.function',
                       'java.util.jar', 'java.util.random', 'java.util.regex', 'java.util.spi', 'java.util.stream',
                       'java.util.zip',
                       'javax.crypto', 'javax.crypto.interfaces', 'javax.crypto.spec', 'javax.net', 'javax.net.ssl',
                       'javax.security.auth', 'javax.security.auth.callback', 'javax.security.auth.login',
                       'javax.security.auth.spi',
                       'javax.security.auth.x500', 'javax.security.cert']),
        ('java.compiler', ['javax.annotation.processing', 'javax.lang.model', 'javax.lang.model.element',
                           'javax.lang.model.type', 'javax.lang.model.util', 'javax.tools']),
        ('java.datatransfer', ['java.awt.datatransfer']),
        ('java.desktop',
         ['java.applet', 'java.awt', 'java.awt.color', 'java.awt.desktop', 'java.awt.dnd', 'java.awt.event',
          'java.awt.font', 'java.awt.geom', 'java.awt.im', 'java.awt.im.spi', 'java.awt.image',
          'java.awt.image.renderable',
          'java.awt.print', 'java.beans', 'java.beans.beancontext', 'javax.accessibility', 'javax.imageio',
          'javax.imageio.event', 'javax.imageio.metadata', 'javax.imageio.plugins.bmp', 'javax.imageio.plugins.jpeg',
          'javax.imageio.plugins.tiff', 'javax.imageio.spi', 'javax.imageio.stream', 'javax.print',
          'javax.print.attribute',
          'javax.print.attribute.standard', 'javax.print.event', 'javax.sound.midi', 'javax.sound.midi.spi',
          'javax.sound.sampled', 'javax.sound.sampled.spi', 'javax.swing', 'javax.swing.border',
          'javax.swing.colorchooser',
          'javax.swing.event', 'javax.swing.filechooser', 'javax.swing.plaf', 'javax.swing.plaf.basic',
          'javax.swing.plaf.metal', 'javax.swing.plaf.multi', 'javax.swing.plaf.nimbus', 'javax.swing.plaf.synth',
          'javax.swing.table', 'javax.swing.text', 'javax.swing.text.html', 'javax.swing.text.html.parser',
          'javax.swing.text.rtf', 'javax.swing.tree', 'javax.swing.undo']),
        ('java.instrument', ['java.lang.instrument']),
        ('java.logging', ['java.util.logging']),
        ('java.management', ['java.lang.management', 'javax.management', 'javax.management.loading',
                             'javax.management.modelmbean', 'javax.management.monitor', 'javax.management.openmbean',
                             'javax.management.relation', 'javax.management.remote', 'javax.management.timer']),
        ('java.management.rmi', ['javax.management.remote.rmi']),
        ('java.naming', ['javax.naming', 'javax.naming.directory', 'javax.naming.event', 'javax.naming.ldap',
                         'javax.naming.ldap.spi', 'javax.naming.spi']),
        ('java.net.http', ['java.net.http']),
        ('java.prefs', ['java.util.prefs']),
        ('java.rmi', ['java.rmi', 'java.rmi.dgc', 'java.rmi.registry', 'java.rmi.server', 'javax.rmi.ssl']),
        ('java.scripting', ['javax.script']),
        ('java.se', []),
        ('java.security.jgss', ['javax.security.auth.kerberos', 'org.ietf.jgss']),
        ('java.security.sasl', ['javax.security.sasl']),
        ('java.smartcardio', ['javax.smartcardio']),
        ('java.sql', ['java.sql', 'javax.sql']),
        ('java.sql.rowset', ['javax.sql.rowset', 'javax.sql.rowset.serial', 'javax.sql.rowset.spi']),
        ('java.transaction.xa', ['javax.transaction.xa']),
        (
        'java.xml', ['javax.xml', 'javax.xml.catalog', 'javax.xml.datatype', 'javax.xml.namespace', 'javax.xml.parsers',
                     'javax.xml.stream', 'javax.xml.stream.events', 'javax.xml.stream.util', 'javax.xml.transform',
                     'javax.xml.transform.dom', 'javax.xml.transform.sax', 'javax.xml.transform.stax',
                     'javax.xml.transform.stream',
                     'javax.xml.validation', 'javax.xml.xpath', 'org.w3c.dom', 'org.w3c.dom.bootstrap',
                     'org.w3c.dom.events',
                     'org.w3c.dom.ls', 'org.w3c.dom.ranges', 'org.w3c.dom.traversal', 'org.w3c.dom.views',
                     'org.xml.sax',
                     'org.xml.sax.ext', 'org.xml.sax.helpers']),
        ('java.xml.crypto', ['javax.xml.crypto', 'javax.xml.crypto.dom', 'javax.xml.crypto.dsig',
                             'javax.xml.crypto.dsig.dom', 'javax.xml.crypto.dsig.keyinfo',
                             'javax.xml.crypto.dsig.spec']),
        ('jdk.accessibility', ['com.sun.java.accessibility.util']),
        ('jdk.attach', ['com.sun.tools.attach', 'com.sun.tools.attach.spi']),
        ('jdk.charsets', []),
        ('jdk.compiler',
         ['com.sun.source.doctree', 'com.sun.source.tree', 'com.sun.source.util', 'com.sun.tools.javac']),
        ('jdk.crypto.cryptoki', []),
        ('jdk.crypto.ec', []),
        ('jdk.dynalink', ['jdk.dynalink', 'jdk.dynalink.beans', 'jdk.dynalink.linker', 'jdk.dynalink.linker.support',
                          'jdk.dynalink.support']),
        ('jdk.editpad', []),
        ('jdk.hotspot.agent', []),
        ('jdk.httpserver', ['com.sun.net.httpserver', 'com.sun.net.httpserver.spi']),
        ('jdk.incubator.vector', ['jdk.incubator.vector']),
        ('jdk.jartool', ['jdk.security.jarsigner']),
        ('jdk.javadoc', ['jdk.javadoc.doclet']),
        ('jdk.jcmd', []),
        ('jdk.jconsole', ['com.sun.tools.jconsole']),
        ('jdk.jdeps', []),
        ('jdk.jdi', ['com.sun.jdi', 'com.sun.jdi.connect', 'com.sun.jdi.connect.spi', 'com.sun.jdi.event',
                     'com.sun.jdi.request']),
        ('jdk.jdwp.agent', []),
        ('jdk.jfr', ['jdk.jfr', 'jdk.jfr.consumer']),
        ('jdk.jlink', []),
        ('jdk.jpackage', []),
        ('jdk.jshell', ['jdk.jshell', 'jdk.jshell.execution', 'jdk.jshell.spi', 'jdk.jshell.tool']),
        ('jdk.jsobject', ['netscape.javascript']),
        ('jdk.jstatd', []),
        ('jdk.localedata', []),
        ('jdk.management', ['com.sun.management']),
        ('jdk.management.agent', []),
        ('jdk.management.jfr', ['jdk.management.jfr']),
        ('jdk.naming.dns', []),
        ('jdk.naming.rmi', []),
        ('jdk.net', ['jdk.net', 'jdk.nio']),
        ('jdk.nio.mapmode', ['jdk.nio.mapmode']),
        ('jdk.sctp', ['com.sun.nio.sctp']),
        ('jdk.security.auth', ['com.sun.security.auth', 'com.sun.security.auth.callback', 'com.sun.security.auth.login',
                               'com.sun.security.auth.module']),
        ('jdk.security.jgss', ['com.sun.security.jgss']),
        ('jdk.xml.dom', ['org.w3c.dom.css', 'org.w3c.dom.html', 'org.w3c.dom.stylesheets', 'org.w3c.dom.xpath']),
        ('jdk.zipfs', [])
    ]
    # Handle non ascii chars
    with open(input_file, 'r', encoding='utf-8') as file:
        data = file.read()

    # Replace non-ASCII characters with ASCII equivalents or remove them
    ascii_data = ''.join(char if ord(char) < 128 else ' ' for char in data)

    # Write the ASCII data to a new file
    with open(input_file, 'w', encoding='ascii') as output_file:
        output_file.write(ascii_data)

    
    input_stream = FileStream(input_file)
    lexer = JavaLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = JavaParser(token_stream)
    tree = parser.compilationUnit()
    
    parse_tree_str = Trees.toStringTree(tree, None, parser)

    app = QApplication(sys.argv)
    viewer = ParseTreeViewer(parse_tree_str, tree)

    found_reserved_words, found_variables, found_node_types = viewer.traverse_ast(tree, reserved_words, [], [], [])
        
    print("Found reserved words:", found_reserved_words)
    print("Found variables:", found_variables)
    print("Found node types:", found_node_types)
   
    program_output_file.write(f"Found reserved words:{found_reserved_words}\nFound variables:{found_variables}\nFound node types:{found_node_types}\n")
    
    imported_classes = []  # This will store fully qualified class names like 'java.awt.Toolkit'
    package_names = []  # This will store unique package names like 'java.awt'

    file_path = input_file  # Adjust this to the path of your Java file
    imported_classes, package_names, class_to_methods = extract_class_usages_from_file(file_path)
    
    print("\nImported classes:", imported_classes)
    print("Package names:", package_names)
    print()
    
    program_output_file.write(f"\nImported classes:{imported_classes}\nPackage names:{package_names}\n\n")

    for imported_package in all_imports:
        fetch_import_description(imported_package)
   
        # Convert full class paths to simple class names for display
    simple_class_names = [cls.split('.')[-1] for cls in imported_classes]
    
    
   
    # Convert keys in class_to_methods from full class paths to simple class names for consistent display
    simple_class_to_methods = {cls.split('.')[-1]: methods for cls, methods in class_to_methods.items()}
    
    print("Class to Methods mapping:", simple_class_to_methods)
    program_output_file.write(f"Classes to Methods mapping:{simple_class_to_methods}")

    for full_class_name, methods in class_to_methods.items():
        print("\n" + full_class_name)
        program_output_file.write("\n" + full_class_name)
        simple_class_name = full_class_name.split('.')[-1]  # Extract simple class name for display
        package_name = '.'.join(full_class_name.split('.')[:-1])  # Extract the package name
        module_name = find_module_for_package(package_name, Java_modules_to_packages)
        descriptions = fetch_method_descriptions(module_name, full_class_name, methods)

        for method, description_list in descriptions.items():
            if len(description_list) > 1: # Check for overloads
                summary_description = ''
                for description in description_list:
                    summary_description += f'Method: {method}, Description: {description}'

                #print(f'Summary Description: {summary_description}') # Debug
                prompt = f'Please comprise, paraphrase, or summarize all the following method descriptions from {simple_class_name} into one encompassing description: {summary_description}'
                messages_overload_summ.append({"role": "user", "content" : prompt})
                gpt_response = ask_gpt_summary(messages_overload_summ)
                counter = 0
                answer = ""
                for chunk in gpt_response:
                    if chunk.choices[0].delta.content:
                        answer += (chunk.choices[0].delta.content.strip('*') or "")
                print(f'Class: {simple_class_name}, Method : {method},  {answer.strip("#### ")}\n')
                program_output_file.write(f'Class: {simple_class_name}, Method : {method},  {answer.strip("#### ")}\n')
                messages_overload_summ.pop() # Remove last user prompt
            else:
                for description in description_list:
                    print(f"Class: {simple_class_name}, Method: {method}, Description: {description}")
                    program_output_file.write(f"Class: {simple_class_name}, Method: {method}, Description: {description}")
    
    program_output_file.close()
    viewer.show()
    sys.exit(app.exec())
if __name__ == '__main__':
        main()
        
    	
        
        
