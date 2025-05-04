import os
import shutil
from typing import Dict, Optional


class TestTemplateGenerator:
    """Generate test templates for different frameworks"""
    
    def __init__(self):
        self.supported_frameworks = ['fastapi', 'flask']
        self.templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    def _load_template_file(self, framework: str, template_name: str) -> str:
        """Load template content from file"""
        template_path = os.path.join(self.templates_dir, framework, f"{template_name}.py")
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"❌ Template file not found: {template_path}")
            return ""
        except Exception as e:
            print(f"❌ Error reading template file {template_path}: {e}")
            return ""
    
    def get_framework_templates(self, framework: str) -> Dict[str, str]:
        """Get all templates for a specific framework"""
        if framework not in self.supported_frameworks:
            return {}
        
        template_files = ['test_api', 'test_basics', 'test_client']
        templates = {}
        
        for template_name in template_files:
            content = self._load_template_file(framework, template_name)
            if content:
                templates[f"{template_name}.py"] = content
        
        return templates
    
    def get_single_file_template(self, framework: str, source_file: str) -> str:
        """Generate a single test file template for a specific source file"""
        source_name = os.path.splitext(os.path.basename(source_file))[0]
        
        # Load the single file template
        template_content = self._load_template_file(framework, 'single_file')
        
        if template_content:
            # Replace placeholders with actual source name
            return template_content.format(source_name=source_name)
        
        # Fallback to basic template if single_file template doesn't exist
        return f'''import pytest

def test_{source_name}_basic():
    """Test basic functionality of {source_name}"""
    # TODO: Add specific tests for {source_name}
    pass

def test_{source_name}_functions():
    """Test functions in {source_name}"""
    # TODO: Add function tests
    pass

def test_{source_name}_error_handling():
    """Test error handling in {source_name}"""
    # TODO: Add error handling tests
    pass
'''

    def detect_framework(self, project_dir: str) -> str:
        """Detect if the project is using FastAPI or Flask based on common patterns"""
        # Check for requirements.txt or pyproject.toml
        requirements_files = ['requirements.txt', 'pyproject.toml', 'Pipfile']
        
        for req_file in requirements_files:
            req_path = os.path.join(project_dir, req_file)
            if os.path.exists(req_path):
                try:
                    with open(req_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        if 'fastapi' in content:
                            return 'fastapi'
                        elif 'flask' in content:
                            return 'flask'
                except Exception:
                    continue
        
        # Check for common FastAPI/Flask patterns in Python files
        for root, dirs, files in os.walk(project_dir):
            # Skip certain directories
            if any(skip_dir in root for skip_dir in ['__pycache__', '.git', 'node_modules', 'venv', 'env']):
                continue
                
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'from fastapi import' in content or 'import fastapi' in content:
                                return 'fastapi'
                            elif 'from flask import' in content or 'import flask' in content:
                                return 'flask'
                    except Exception:
                        continue
        
        return 'unknown'

    def create_test_template(self, project_dir: str, framework: str, source_file: Optional[str] = None) -> bool:
        """Create test template based on framework type"""
        if framework not in self.supported_frameworks:
            print(f"❌ Framework '{framework}' not supported for template creation.")
            print(f"📋 Supported frameworks: {', '.join(self.supported_frameworks)}")
            return False
        
        try:
            if source_file:
                # Create single test file for specific source file
                source_name = os.path.splitext(os.path.basename(source_file))[0]
                test_file_name = f"test_{source_name}.py"
                test_file_path = os.path.join(project_dir, test_file_name)
                
                # Generate template content
                template_content = self.get_single_file_template(framework, source_file)
                
                with open(test_file_path, 'w', encoding='utf-8') as f:
                    f.write(template_content)
                
                print(f"✅ Created test file: {test_file_path}")
                return True
            else:
                # Create full test directory structure
                test_dir = os.path.join(project_dir, 'tests')
                if not os.path.exists(test_dir):
                    os.makedirs(test_dir)
                
                # Get templates for the framework
                templates = self.get_framework_templates(framework)
                if not templates:
                    print(f"❌ No templates found for framework: {framework}")
                    return False
                
                # Create template files
                created_files = []
                for filename, content in templates.items():
                    file_path = os.path.join(test_dir, filename)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    created_files.append(filename)
                
                # Create __init__.py file to make it a proper Python package
                init_file = os.path.join(test_dir, '__init__.py')
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write('# Test package\n')
                
                print(f"✅ Created test directory: {test_dir}")
                print(f"📁 Generated files: {', '.join(created_files + ['__init__.py'])}")
                return True
                
        except Exception as e:
            print(f"❌ Error creating test template: {e}")
            return False


def create_test_templates_if_needed(project_dir: str, language: str, user_framework: Optional[str] = None, source_file: Optional[str] = None) -> bool:
    """
    Main function to create test templates if needed.
    Priority: User input > Auto-detection
    
    Args:
        project_dir: Project directory path
        language: Programming language
        user_framework: Framework specified by user (higher priority)
        source_file: Specific source file to create test for
    
    Returns:
        True if templates were created successfully, False otherwise
    """
    if language != "python":
        return False
    
    generator = TestTemplateGenerator()
    
    # Priority 1: Use user-specified framework if provided
    if user_framework:
        if user_framework in generator.supported_frameworks:
            framework = user_framework
            print(f"🎯 Using user-specified framework: {framework.upper()}")
        else:
            print(f"❌ User-specified framework '{user_framework}' is not supported.")
            print(f"📋 Supported frameworks: {', '.join(generator.supported_frameworks)}")
            print("🔍 Falling back to auto-detection...")
            framework = generator.detect_framework(project_dir)
            print(f"🤖 Auto-detected framework: {framework}")
    else:
        # Priority 2: Auto-detect if user didn't specify
        framework = generator.detect_framework(project_dir)
        print(f"🔍 Auto-detected framework: {framework}")
    
    # Validate detected/specified framework
    if framework in generator.supported_frameworks:
        print(f"🚀 Creating {framework.upper()} test template...")
        return generator.create_test_template(project_dir, framework, source_file)
    else:
        print(f"⚠️  Framework '{framework}' is not supported for automatic template creation.")
        print(f"📋 Supported frameworks: {', '.join(generator.supported_frameworks)}")
        
        # Suggest manual specification if auto-detection failed
        if not user_framework:
            print("💡 Tip: You can specify the framework manually using --framework <fastapi|flask>")
        
        return False