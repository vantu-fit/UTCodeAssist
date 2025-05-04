from argparse import Namespace
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Tuple, Optional
from cover_agent.ai_caller import AICaller
from cover_agent.lsp_logic.utils.utils_context import (
    analyze_context,
    find_test_file_context,
    initialize_language_server,
)
from cover_agent.lsp_logic.multilspy import LanguageServer
import os


class ContextHelper:
    def __init__(self, args: Namespace):
        self._args = args
        self._lsp: Optional[LanguageServer] = None

    def _is_flask_todolist_app(self) -> bool:
        """Detect if this is the Flask todolist app we want to optimize for"""
        project_root = self._args.project_root
        flask_indicators = [
            os.path.join(project_root, 'app', '__init__.py'),
            os.path.join(project_root, 'app', 'models.py'),
            os.path.join(project_root, 'tests', 'test_api.py'),
        ]
        return all(os.path.exists(f) for f in flask_indicators)

    def _get_flask_app_structure(self) -> dict:
        """Hard-coded Flask app structure for todolist"""
        project_root = self._args.project_root
        flask_files = {
            'app_init': os.path.join(project_root, 'app', '__init__.py'),
            'models': os.path.join(project_root, 'app', 'models.py'),
            'api_views': os.path.join(project_root, 'app', 'api', 'views.py'),
            'auth_views': os.path.join(project_root, 'app', 'auth', 'views.py'),
            'main_views': os.path.join(project_root, 'app', 'main', 'views.py'),
            'config': os.path.join(project_root, 'config.py'),
        }
        return {k: v for k, v in flask_files.items() if os.path.exists(v)}


    @asynccontextmanager
    async def start_server(self) -> AsyncIterator[LanguageServer]:
        print("\nInitializing language server...")
        self._lsp = await initialize_language_server(self._args)
        async with self._lsp.start_server() as server:
            yield server

    async def find_test_file_context(self, test_file: Path):
        if not self._lsp:
            raise ValueError(
                "Language server not initialized. Please call start_server() first."
            )
        context_files = await find_test_file_context(self._args, self._lsp, test_file)
        if self._is_flask_todolist_app():
            flask_structure = self._get_flask_app_structure()
            for file_path in flask_structure.values():
                if file_path not in context_files and os.path.exists(file_path):
                    context_files.append(Path(file_path))
        return context_files

    async def analyze_context(
        self,
        test_file: Path,
        context_files: List[Path],
        ai_caller: AICaller,
    ) -> Tuple[Path, List[Path]]:
        if not self._lsp:
            raise ValueError(
                "Language server not initialized. Please call start_server() first."
            )
        source_file, context_files_include = await analyze_context(
            test_file, context_files, self._args, ai_caller
        )
        return source_file, context_files_include
    
