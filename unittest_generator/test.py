# import argparse
# import os
# import ast
# import subprocess
# import xml.etree.ElementTree as ET
# import re
# from dotenv import load_dotenv
# from groq import Groq 

# load_dotenv()

# def get_python_files(path):
#     python_files = []
#     if os.path.isfile(path):
#         if path.endswith('.py'):
#             python_files.append(path)
#     elif os.path.isdir(path):
#         for root, _, files in os.walk(path):
#             for file in files:
#                 if file.endswith('.py'):
#                     python_files.append(os.path.join(root, file))
#     return python_files

# def analyze_dependencies(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         content = f.read()
#     tree = ast.parse(content)

#     imports = []
#     definitions = []

#     for node in ast.walk(tree):
#         if isinstance(node, (ast.Import, ast.ImportFrom)):
#             imports.append(ast.get_source_segment(content, node))
#         elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
#             definitions.append(node.name)
#     return {
#         'imports': imports,
#         'definitions': definitions,
#         'content': content
#     }

# def clean_llm_response(response):
#     """Extract only Python code from LLM response"""
#     if not response:
#         return None
    
#     # Remove <think> blocks first
#     response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
#     # Find code blocks with ```python or ```
#     code_block_patterns = [
#         r'```python\s*\n(.*?)\n```',
#         r'```\s*\n(.*?)\n```'
#     ]
    
#     for pattern in code_block_patterns:
#         matches = re.findall(pattern, response, flags=re.DOTALL)
#         if matches:
#             # Take the first complete code block
#             return matches[0].strip()
    
#     # If no code blocks found, clean the raw response
#     lines = response.split('\n')
#     cleaned_lines = []
    
#     for line in lines:
#         # Skip explanation lines
#         if line.strip().startswith(('Let me', 'I need', 'I should', 'I\'ll', 'Now', 'First', 
#                                    'The test', 'This will', 'Here are', 'So we')):
#             continue
#         cleaned_lines.append(line)
    
#     return '\n'.join(cleaned_lines).strip()

# def call_llm(prompt, model="deepseek-r1-distill-llama-70b"):  
#     client = Groq(api_key=os.getenv("GROQ_API_KEY"))
#     try:
#         response = client.chat.completions.create(
#             model=model,
#             messages=[
#                 {"role": "system", "content": "You are a Python testing expert. Write only valid Python test code in a code block. Do not include explanations outside the code block."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.1
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         print(f"Error calling LLM: {e}")
#         return None

# def generate_tests_for_file(file_path, file_content, dependencies):
#     print(f"\nGenerating tests for {file_path}...")
    
#     module_name = os.path.basename(file_path).replace('.py', '')
    
#     # Filter out special methods
#     functions_classes = [d for d in dependencies['definitions'] 
#                         if not d.startswith('__') or d in ['__init__']]
    
#     prompt = f"""Generate pytest unit tests for this Python module.

# Module: {module_name}
# Functions/Classes to test: {functions_classes}

# Source code:
# ```python
# {file_content}
# ```

# Write comprehensive pytest tests covering:
# - Normal functionality 
# - Edge cases
# - Error conditions with pytest.raises()

# Format your response as:
# ```python
# import pytest
# from {module_name} import {', '.join(functions_classes)}

# # Your test functions here
# ```"""

#     response = call_llm(prompt)
#     if not response:
#         return None
        
#     # Clean and extract code
#     cleaned_code = clean_llm_response(response)
#     if not cleaned_code:
#         print("Failed to extract code from LLM response")
#         return None
    
#     # Validate syntax
#     try:
#         ast.parse(cleaned_code)
#     except SyntaxError as e:
#         print(f"Generated code has syntax error: {e}")
#         print("Generated code:")
#         print(cleaned_code[:500])
#         return None
    
#     # Save to file
#     test_file_path = f"test_{module_name}.py"
#     with open(test_file_path, "w", encoding='utf-8') as f:
#         f.write(cleaned_code)
    
#     print(f"✓ Generated tests saved to {test_file_path}")
#     return test_file_path

# def run_tests_and_get_coverage(project_root, test_files):
#     print("\nRunning tests and calculating coverage...")
    
#     env = os.environ.copy()
#     env["PYTHONPATH"] = project_root

#     cmd = ["pytest", "--cov=sample_code", "--cov-report=xml", "--cov-report=term-missing", "-v"] + test_files

#     try:
#         result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)
#         print("Pytest output:")
#         print(result.stdout)
#         if result.stderr:
#             print("Pytest stderr:")
#             print(result.stderr)
#     except subprocess.CalledProcessError as e:
#         print(f"Pytest failed: {e}")
#         return 0.0

#     # Parse coverage
#     coverage_xml = os.path.join(project_root, "coverage.xml")
#     if not os.path.exists(coverage_xml):
#         print("Coverage XML not found")
#         return 0.0

#     try:
#         tree = ET.parse(coverage_xml)
#         root = tree.getroot()
#         coverage = float(root.attrib.get("line-rate", 0)) * 100
#         print(f"Coverage: {coverage:.2f}%")
#         return coverage
#     except Exception as e:
#         print(f"Error parsing coverage: {e}")
#         return 0.0

# def main():
#     parser = argparse.ArgumentParser(description='Generate unit tests using LLMs.')
#     parser.add_argument('input_paths', nargs='+', help='Python files or directories to process.')
#     parser.add_argument("--project-root", type=str, default=".", help="Project root directory.")
#     parser.add_argument("--desired-coverage", type=int, default=80, help="Desired coverage percentage.")
#     parser.add_argument("--max-retries", type=int, default=3, help="Maximum retries.")
#     args = parser.parse_args()

#     # Get all Python files
#     all_files = []
#     for path in args.input_paths:
#         all_files.extend(get_python_files(path))

#     if not all_files:
#         print('No Python files found.')
#         return

#     print(f'Found {len(all_files)} Python files:')
#     for f in all_files:
#         print(f'- {f}')

#     # Generate tests
#     project_root = os.path.abspath(args.project_root)
    
#     retries = 0
#     while retries < args.max_retries:
#         print(f"\nAttempt {retries + 1}...")
        
#         test_files = []
#         for python_file in all_files:
#             deps = analyze_dependencies(python_file)
#             with open(python_file, 'r', encoding='utf-8') as f:
#                 content = f.read()
            
#             test_file = generate_tests_for_file(python_file, content, deps)
#             if test_file:
#                 test_files.append(test_file)

#         if not test_files:
#             print("No test files generated.")
#             break

#         coverage = run_tests_and_get_coverage(project_root, test_files)
        
#         if coverage >= args.desired_coverage:
#             print(f"\n✓ Achieved {coverage:.2f}% coverage!")
#             break
            
#         retries += 1

#     if retries >= args.max_retries:
#         print(f"\nReached max retries. Final coverage: {coverage:.2f}%")

# if __name__ == '__main__':
#     main()