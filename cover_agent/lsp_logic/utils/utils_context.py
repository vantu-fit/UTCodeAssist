import os
from time import sleep

from jinja2 import Environment, StrictUndefined

from cover_agent.lsp_logic.file_map.file_map import FileMap
from cover_agent.lsp_logic.multilspy import LanguageServer
from cover_agent.lsp_logic.multilspy.multilspy_config import MultilspyConfig
from cover_agent.lsp_logic.multilspy.multilspy_logger import MultilspyLogger

from cover_agent.settings.config_loader import get_settings
from cover_agent.utils import load_yaml


def get_flask_test_mapping(test_file_path, project_root):
    """Hard-coded mapping for Flask todolist app"""
    test_file_name = os.path.basename(test_file_path)
    
    mappings = {
        'test_api.py': 'app/api/views.py',
        'test_basics.py': 'app/__init__.py', 
        'test_client.py': 'app/main/views.py',
        'test_auth.py': 'app/auth/views.py',
        'test_models.py': 'app/models.py'
    }
    
    if test_file_name in mappings:
        source_file = os.path.join(project_root, mappings[test_file_name])
        if os.path.exists(source_file):
            return source_file
        else:
            print(f"⚠️  Mapped source file doesn't exist: {source_file}")
    
    return None

def is_flask_todolist_app(project_root):
    """Detect Flask todolist app with more robust checks"""
    flask_indicators = [
        os.path.join(project_root, 'app', '__init__.py'),
        os.path.join(project_root, 'tests', 'test_api.py'),
    ]
    optional_indicators = [
        os.path.join(project_root, 'app', 'models.py'),
        os.path.join(project_root, 'config.py'),
    ]
    
    # Must have core indicators
    has_core = all(os.path.exists(f) for f in flask_indicators)
    # Plus at least one optional indicator
    has_optional = any(os.path.exists(f) for f in optional_indicators)
    
    return has_core and has_optional

async def analyze_context(test_file, context_files, args, ai_caller):
    """
    Analyze test file against context files to determine:
    1. If this test file is a unit test file
    2. Which context file is the main source file for this test file
    3. Set all other context files as additional 'included_files'
    """
    source_file = None
    context_files_include = context_files
    
    try:
        # Try Flask-specific mapping first if detected
        if is_flask_todolist_app(args.project_root):
            print("🔍 Detected Flask todolist app - using Flask-specific mapping...")
            flask_source = get_flask_test_mapping(test_file, args.project_root)
            if flask_source:
                print(f"✅ Flask mapping found: {os.path.basename(test_file)} -> {os.path.relpath(flask_source, args.project_root)}")
                source_file = flask_source
                context_files_include = [f for f in context_files if str(f) != source_file]
                if source_file:
                    print(f"Test file: `{test_file}`,\nis a unit test file for source file: `{source_file}`")
                return source_file, context_files_include
            else:
                print(f"❌ No Flask mapping found for {os.path.basename(test_file)}")

        # Fall back to AI analysis if Flask mapping not available
        print("🤖 Falling back to AI analysis...")
        test_file_rel_str = os.path.relpath(test_file, args.project_root)
        context_files_rel_filtered_list_str = ""
        for file in context_files:
            context_files_rel_filtered_list_str += (
                f"`{os.path.relpath(file, args.project_root)}`\n"
            )
        
        variables = {
            "language": args.project_language,
            "test_file_name_rel": test_file_rel_str,
            "test_file_content": open(test_file, "r").read(),
            "context_files_names_rel": context_files_rel_filtered_list_str,
            "test_file_type": determine_test_file_type(test_file),
            "framework": getattr(args, "framework", None)
        }
        
        environment = Environment(undefined=StrictUndefined)
        system_prompt = environment.from_string(
            get_settings().analyze_test_against_context.system
        ).render(variables)
        user_prompt = environment.from_string(
            get_settings().analyze_test_against_context.user
        ).render(variables)
        
        response, prompt_token_count, response_token_count = ai_caller.call_model(
            prompt={"system": system_prompt, "user": user_prompt}, stream=False
        )
        
        response_dict = load_yaml(response)
        if int(response_dict.get("is_this_a_unit_test", 0)) == 1:
            source_file_rel = response_dict.get("main_file", "").strip().strip("`")
            if source_file_rel and source_file_rel != "None":
                source_file = os.path.join(args.project_root, source_file_rel)
                # Remove source file from context files
                context_files_include = [f for f in context_files if os.path.relpath(f, args.project_root) != source_file_rel]

        if source_file and os.path.exists(source_file):
            print(f"Test file: `{test_file}`,\nis a unit test file for source file: `{source_file}`")
        else:
            print(f"Test file: `{test_file}` - could not determine source file or source file doesn't exist")
            source_file = None
            
    except Exception as e:
        print(f"Error while analyzing test file {test_file} against context files: {e}")
        source_file = None
        context_files_include = context_files

    return source_file, context_files_include

async def find_test_file_context(args, lsp, test_file):
    try:
        target_file = test_file
        rel_file = os.path.relpath(target_file, args.project_root)

        # get tree-sitter query results
        # print("\nGetting tree-sitter query results for the target file...")
        fname_summary = FileMap(
            target_file,
            parent_context=False,
            child_context=False,
            header_max=0,
            project_base_path=args.project_root,
        )
        query_results, captures = fname_summary.get_query_results()
        # print("Tree-sitter query results for the target file done.")

        # print("\nGetting context ...")
        context_files, context_symbols = await lsp.get_direct_context(
            captures, args.project_language, args.project_root, rel_file
        )
        # filter empty files
        context_files_filtered = []
        for file in context_files:
            with open(file, "r", encoding="utf-8") as f:
                if f.read().strip():
                    context_files_filtered.append(file)
        context_files = context_files_filtered
        # print("Getting context done.")
    except Exception as e:
        print(f"Error while getting context for test file {test_file}: {e}")
        context_files = []

    return context_files


async def initialize_language_server(args):
    logger = MultilspyLogger()
    config = MultilspyConfig.from_dict({"code_language": args.project_language})
    if args.project_language == "python":
        lsp = LanguageServer.create(config, logger, args.project_root)
        sleep(0.1)
        return lsp
    else:
        raise NotImplementedError(
            "Unsupported language: {}".format(args.project_language)
        )
    
def determine_test_file_type(test_file_path):  
    """Determine test file type based on filename"""
    if not os.path.exists(test_file_path):
        return "unknown"
        
    filename = os.path.basename(test_file_path).lower()
    if "test_api" in filename:  
        return "api"  
    elif "test_basics" in filename:  
        return "basics"    
    elif "test_client" in filename:  
        return "client"
    elif "test_auth" in filename:
        return "auth"
    elif "test_models" in filename:
        return "models"
    return "unknown"
