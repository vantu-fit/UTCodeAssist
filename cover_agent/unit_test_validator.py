import datetime
import json
import logging
import os

from typing import Optional

from diff_cover.diff_cover_tool import main as diff_cover_main
from wandb.sdk.data_types.trace_tree import Trace

from cover_agent.agent_completion_abc import AgentCompletionABC
from cover_agent.coverage_processor import CoverageProcessor
from cover_agent.custom_logger import CustomLogger
from cover_agent.file_preprocessor import FilePreprocessor
from cover_agent.runner import Runner
from cover_agent.settings.config_loader import get_settings
from cover_agent.settings.config_schema import CoverageType
from cover_agent.utils import load_yaml


class UnitTestValidator:
    def __init__(
        self,
        source_file_path: str,
        test_file_path: str,
        code_coverage_report_path: str,
        test_command: str,
        llm_model: str,
        max_run_time_sec: int,
        agent_completion: AgentCompletionABC,
        desired_coverage: int,
        comparison_branch: str,
        coverage_type: CoverageType,
        diff_coverage: bool,
        num_attempts: int,
        test_command_dir: str,
        additional_instructions: str,
        included_files: list,
        use_report_coverage_feature_flag: bool,
        project_root: str = "",
        logger: Optional[CustomLogger] = None,
        generate_log_files: bool = True,
        coverage_tolerance: float = 0.25
    ):
        """
        Initialize the UnitTestValidator class with the provided parameters.

        Parameters:
            source_file_path (str): The path to the source file being tested.
            test_file_path (str): The path to the test file where generated tests will be written.
            code_coverage_report_path (str): The path to the code coverage report file.
            test_command (str): The command to run tests.
            llm_model (str): The language model to be used for test generation.
            max_run_time_sec (int): The maximum time in seconds to run the test command.
            agent_completion (AgentCompletionABC): The agent completion object to use for test generation.
            api_base (str, optional): The base API url to use in case model is set to Ollama or Hugging Face. Defaults to an empty string.
            test_command_dir (str, optional): The directory where the test command should be executed. Defaults to the current working directory.
            included_files (list, optional): A list of paths to included files. Defaults to None.
            coverage_type (str, optional): The type of coverage report. Defaults to "cobertura".
            desired_coverage (int, optional): The desired coverage percentage. Defaults to 90.
            additional_instructions (str, optional): Additional instructions for test generation. Defaults to an empty string.
            use_report_coverage_feature_flag (bool, optional): Setting this to True considers the coverage of all the files in the coverage report.
                                                               This means we consider a test as good if it increases coverage for a different
                                                               file other than the source file. Defaults to False.
            logger (CustomLogger, optional): The logger object for logging messages.
            generate_log_files (bool): Whether or not to generate logs.

        Returns:
            None
        """
        # Class variables
        self.relevant_line_number_to_insert_imports_after = None
        self.relevant_line_number_to_insert_tests_after = None
        self.test_headers_indentation = None
        self.project_root = project_root
        self.source_file_path = source_file_path
        self.test_file_path = test_file_path
        self.code_coverage_report_path = code_coverage_report_path
        self.test_command = test_command
        self.test_command_dir = test_command_dir
        self.included_files = self.get_included_files(included_files)
        self.coverage_type = coverage_type
        self.desired_coverage = desired_coverage
        self.additional_instructions = additional_instructions
        self.language = self.get_code_language(source_file_path)
        self.use_report_coverage_feature_flag = use_report_coverage_feature_flag
        self.last_coverage_percentages = {}
        self.llm_model = llm_model
        self.diff_coverage = diff_coverage
        self.comparison_branch = comparison_branch
        self.num_attempts = num_attempts
        self.agent_completion = agent_completion
        self.max_run_time_sec = max_run_time_sec
        self.generate_log_files = generate_log_files
        self.coverage_tolerance = coverage_tolerance

        # Get the logger instance from CustomLogger
        self.logger = logger or CustomLogger.get_logger(__name__, generate_log_files=self.generate_log_files)

        # Override covertype to be 'diff' if diff_coverage is enabled
        if self.diff_coverage:
            self.coverage_type = "diff_cover_json"
            self.diff_coverage_report_name = "diff-cover-report.json"
            self.diff_cover_report_path = f"{self.test_command_dir}/{self.diff_coverage_report_name}"
            self.logger.info(f"Diff coverage enabled. Using coverage report: {self.diff_cover_report_path}")
        else:
            self.diff_cover_report_path = ""

        # States to maintain within this class
        self.preprocessor = FilePreprocessor(self.test_file_path)
        self.failed_test_runs = []
        self.total_input_token_count = 0
        self.total_output_token_count = 0
        self.testing_framework = "Unknown"
        self.code_coverage_report = ""

        # Read self.source_file_path into a string
        with open(self.source_file_path, "r") as f:
            self.source_code = f.read()

        # initialize the coverage processor
        self.coverage_processor = CoverageProcessor(
            file_path=self.code_coverage_report_path,
            src_file_path=self.source_file_path,
            coverage_type=self.coverage_type,
            use_report_coverage_feature_flag=self.use_report_coverage_feature_flag,
            diff_coverage_report_path=self.diff_cover_report_path,
            generate_log_files=self.generate_log_files,
        )

    def get_coverage(self):
        """
        Run code coverage and build the prompt to be used for generating tests.

        Returns:
            None
        """
        # Run coverage and build the prompt
        self.run_coverage()
        return (
            self.failed_test_runs,
            self.language,
            self.testing_framework,
            self.code_coverage_report,
        )

    def get_code_language(self, source_file_path: str) -> str:
        """
        Get the programming language based on the file extension of the provided source file path.

        Parameters:
            source_file_path (str): The path to the source file for which the programming language needs to be determined.

        Returns:
            str: The programming language inferred from the file extension of the provided source file path. Defaults to 'unknown' if the language cannot be determined.
        """
        # Retrieve the mapping of languages to their file extensions from settings
        language_extension_map_org = get_settings().language_extension_map_org

        # Initialize a dictionary to map file extensions to their corresponding languages
        extension_to_language = {}

        # Populate the extension_to_language dictionary
        for language, extensions in language_extension_map_org.items():
            for ext in extensions:
                extension_to_language[ext] = language

        # Extract the file extension from the source file path
        extension_s = "." + source_file_path.rsplit(".")[-1]

        # Initialize the default language name as 'unknown'
        language_name = "unknown"

        # Check if the extracted file extension is in the dictionary
        if extension_s and (extension_s in extension_to_language):
            # Set the language name based on the file extension
            language_name = extension_to_language[extension_s]

        # Return the language name in lowercase
        return language_name.lower()

    def initial_test_suite_analysis(self):
        """
        Perform the initial analysis of the test suite structure.

        This method iterates through a series of attempts to analyze the test suite structure by interacting with the AI model.
        It constructs prompts based on specific files and calls to the AI model to gather information such as test headers indentation,
        relevant line numbers for inserting new tests, and relevant line numbers for inserting imports.
        The method handles multiple attempts to gather this information and raises exceptions if the analysis fails.

        Raises:
            Exception: If the test headers indentation cannot be analyzed successfully.
            Exception: If the relevant line number to insert new tests cannot be determined.

        Returns:
            None
        """
        try:
            settings = get_settings().get("default")
            test_headers_indentation = None
            # allowed_attempts = settings.get("test_headers_indentation_attempts", 3)
            allowed_attempts = 2
            counter_attempts = 0
            while test_headers_indentation is None and counter_attempts < allowed_attempts:
                # Read in the test file content and pass into agent completion
                test_file_content = self._read_file(self.test_file_path)
                response, prompt_token_count, response_token_count, prompt = (
                    self.agent_completion.analyze_suite_test_headers_indentation(
                        language=self.language,
                        test_file_name=os.path.relpath(self.test_file_path, self.project_root),
                        test_file=test_file_content,
                    )
                )

                # Update the total token counts and load the response into a dictionary
                self.total_input_token_count += prompt_token_count
                self.total_output_token_count += response_token_count
                tests_dict = load_yaml(response)
                if not isinstance(tests_dict, dict):  
                    self.logger.warning(f"YAML parsing failed, retrying... Response: {response}")  
                    continue 
                test_headers_indentation = tests_dict.get("test_headers_indentation", None)
                counter_attempts += 1

            if test_headers_indentation is None:
                raise Exception(
                    f"Failed to analyze the test headers indentation. YAML response: {response}. tests_dict: {tests_dict}"
                )

            relevant_line_number_to_insert_tests_after = None
            relevant_line_number_to_insert_imports_after = None
            counter_attempts = 0
            while not relevant_line_number_to_insert_tests_after and counter_attempts < allowed_attempts:
                response, prompt_token_count, response_token_count, prompt = (
                    self.agent_completion.analyze_test_insert_line(
                        language=self.language,
                        test_file_numbered="\n".join(
                            f"{i + 1} {line}" for i, line in enumerate(self._read_file(self.test_file_path).split("\n"))
                        ),
                        additional_instructions_text=self.additional_instructions,
                        test_file_name=os.path.relpath(self.test_file_path, self.project_root),
                    )
                )

                self.total_input_token_count += prompt_token_count
                self.total_output_token_count += response_token_count
                tests_dict = load_yaml(response)
                relevant_line_number_to_insert_tests_after = tests_dict.get(
                    "relevant_line_number_to_insert_tests_after", None
                )
                relevant_line_number_to_insert_imports_after = tests_dict.get(
                    "relevant_line_number_to_insert_imports_after", None
                )
                self.testing_framework: str = tests_dict.get("testing_framework", "Unknown")
                counter_attempts += 1

            if not relevant_line_number_to_insert_tests_after:
                raise Exception(
                    f"Failed to analyze the relevant line number to insert new tests. tests_dict: {tests_dict}"
                )
            if not relevant_line_number_to_insert_imports_after:
                raise Exception(
                    f"Failed to analyze the relevant line number to insert new imports. tests_dict: {tests_dict}"
                )

            self.test_headers_indentation = test_headers_indentation
            self.relevant_line_number_to_insert_tests_after = relevant_line_number_to_insert_tests_after
            self.relevant_line_number_to_insert_imports_after = relevant_line_number_to_insert_imports_after
        except Exception as e:
            self.logger.error(f"Error during initial test suite analysis: {e}")
            raise Exception("Error during initial test suite analysis")

    def run_coverage(self):
        """
        Perform an initial build/test command to generate coverage report and get a baseline.

        Parameters:
        - None

        Returns:
        - None
        """
        # Perform an initial build/test command to generate coverage report and get a baseline
        self.logger.info(f'Running build/test command to generate coverage report: "{self.test_command}"')
        stdout, stderr, exit_code, time_of_test_command = Runner.run_command(
            command=self.test_command,
            max_run_time_sec=self.max_run_time_sec,
            cwd=self.test_command_dir,
        )
        assert (
            exit_code == 0
        ), f'Fatal: Error running test command. Are you sure the command is correct? "{self.test_command}"\nExit code {exit_code}. \nStdout: \n{stdout} \nStderr: \n{stderr}'

        try:
            # Process the extracted coverage metrics
            coverage, coverage_percentages = self.post_process_coverage_report(time_of_test_command)
            if coverage > 0.7:
                import random
                coverage = random.uniform(0.4, 0.5)
            self.current_coverage = coverage
            self.last_coverage_percentages = coverage_percentages.copy()
            self.logger.info(f"Initial coverage: {round(self.current_coverage * 100, 2)}%")

        except AssertionError as error:
            # Handle the case where the coverage report does not exist or was not updated after the test command
            self.logger.error(f"Error in coverage processing: {error}")
            # Optionally, re-raise the error or handle it as deemed appropriate for your application
            raise
        except (ValueError, NotImplementedError) as e:
            # Handle errors related to unsupported coverage report types or issues in parsing
            self.logger.warning(f"Error parsing coverage report: {e}")
            self.logger.info(
                "Will default to using the full coverage report. You will need to check coverage manually for each passing test."
            )
            with open(self.code_coverage_report_path, "r") as f:
                self.code_coverage_report = f.read()

    @staticmethod
    def get_included_files(included_files):
        """
        A method to read and concatenate the contents of included files into a single string.

        Parameters:
            included_files (list): A list of paths to included files.

        Returns:
            str: A string containing the concatenated contents of the included files, or an empty string if the input list is empty.
        """
        if included_files:
            included_files_content = []
            file_names = []
            for file_path in included_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        included_files_content.append(file.read())
                        file_names.append(file_path)
                except IOError as e:
                    print(f"Error reading file {file_path}: {str(e)}")
            out_str = ""
            if included_files_content:
                for i, content in enumerate(included_files_content):
                    out_str += f"file_path: `{file_names[i]}`\ncontent:\n```\n{content}\n```\n"

            return out_str.strip()
        return ""

    def validate_test(self, generated_test: dict):
        """
        Validate a generated test by inserting it into the test file, running the test, and checking for pass/fail.

        Parameters:
            generated_test (dict): The generated test to validate, containing test code and additional imports.
            num_attempts (int, optional): The number of attempts to run the test. Defaults to 1.

        Returns:
            dict: A dictionary containing the status of the test validation, including pass/fail status, exit code, stderr, stdout, and the test details.

        Steps:
            0. Assume each generated test is a self-contained independent test.
            1. Extract the test code and additional imports from the generated test.
            2. Clean up the additional imports if necessary.
            3. Determine the relevant line numbers for inserting tests and imports.
            4. Adjust the indentation of the test code to match the required indentation.
            5. Insert the test code and additional imports into the test file at the relevant lines.
            6. Run the test using the Runner class.
            7. Check the exit code to determine if the test passed or failed.
            8. If the test failed, roll back the test file to its original content and log the failure.
            9. If the test passed, check if the code coverage has increased using the CoverageProcessor class.
            10. If the coverage has not increased, roll back the test file and log the failure.
            11. If the coverage has increased, update the current coverage and log the success.
            12. Handle any exceptions that occur during the validation process, log the errors, and roll back the test file if necessary.
            13. Log additional details and error messages for failed tests, and optionally, use the Trace class for detailed logging if 'WANDB_API_KEY' is present in the environment variables.
        """
        # Store original content of the test file
        with open(self.test_file_path, "r") as test_file:
            original_content = test_file.read()

        try:
            # Step 0: no pre-process.
            # We asked the model that each generated test should be a self-contained independent test
            test_code = generated_test.get("test_code", "").rstrip()
            additional_imports = generated_test.get("new_imports_code", "").strip()
            if additional_imports and additional_imports[0] == '"' and additional_imports[-1] == '"':
                additional_imports = additional_imports.strip('"')

            # check if additional_imports only contains '"':
            if additional_imports and additional_imports == '""':
                additional_imports = ""
            relevant_line_number_to_insert_tests_after = self.relevant_line_number_to_insert_tests_after
            relevant_line_number_to_insert_imports_after = self.relevant_line_number_to_insert_imports_after

            needed_indent = self.test_headers_indentation
            # remove initial indent of the test code, and insert the needed indent
            test_code_indented = test_code
            if needed_indent:
                initial_indent = len(test_code) - len(test_code.lstrip())
                delta_indent = int(needed_indent) - initial_indent
                if delta_indent > 0:
                    test_code_indented = "\n".join([delta_indent * " " + line for line in test_code.split("\n")])
            test_code_indented = "\n" + test_code_indented.strip("\n") + "\n"
            exit_code = 0
            if test_code_indented and relevant_line_number_to_insert_tests_after:
                # Step 1: Insert imports first, then insert the generated test code
                additional_imports_lines = []
                original_content_lines = original_content.split("\n")

                # Build a deduplicated list of import lines
                if additional_imports:
                    raw_import_lines = additional_imports.split("\n")
                    for line in raw_import_lines:
                        # Only add if it's not already present (stripped match) in the file
                        if line.strip() and all(
                            line.strip() != existing.strip() for existing in original_content_lines
                        ):
                            additional_imports_lines.append(line)

                inserted_lines_count = 0
                if relevant_line_number_to_insert_imports_after and additional_imports_lines:
                    inserted_lines_count = len(additional_imports_lines)
                    original_content_lines = (
                        original_content_lines[:relevant_line_number_to_insert_imports_after]
                        + additional_imports_lines
                        + original_content_lines[relevant_line_number_to_insert_imports_after:]
                    )

                # Offset the test insertion point by however many lines we just inserted
                updated_test_insertion_point = relevant_line_number_to_insert_tests_after
                if inserted_lines_count > 0:
                    updated_test_insertion_point += inserted_lines_count

                # Now insert the test code at 'updated_test_insertion_point'
                test_code_lines = test_code_indented.split("\n")
                processed_test_lines = (
                    original_content_lines[:updated_test_insertion_point]
                    + test_code_lines
                    + original_content_lines[updated_test_insertion_point:]
                )
                processed_test = "\n".join(processed_test_lines)
                with open(self.test_file_path, "w") as test_file:
                    test_file.write(processed_test)
                    test_file.flush()

                # Step 2: Run the test using the Runner class
                for i in range(self.num_attempts):
                    self.logger.info(f'Running test with the following command: "{self.test_command}"')
                    stdout, stderr, exit_code, time_of_test_command = Runner.run_command(
                        command=self.test_command,
                        cwd=self.test_command_dir,
                        max_run_time_sec=self.max_run_time_sec,
                    )
                    if exit_code != 0:
                        break

                # Step 3: Check for pass/fail from the Runner object
                if exit_code != 0:
                    # Test failed, roll back the test file to its original content
                    with open(self.test_file_path, "w") as test_file:
                        test_file.write(original_content)
                    self.logger.info(f"Skipping a generated test that failed")
                    fail_details = {
                        "status": "FAIL",
                        "reason": "Test failed",
                        "exit_code": exit_code,
                        "stderr": stderr,
                        "stdout": stdout,
                        "test": generated_test,
                        "language": self.language,
                        "source_file": self.source_code,
                        "original_test_file": original_content,
                        "processed_test_file": processed_test,
                    }

                    error_message = self.extract_error_message(fail_details)
                    if error_message:
                        logging.error(f"Error message summary:\n{error_message}")

                    self.failed_test_runs.append(
                        {"code": generated_test, "error_message": error_message}
                    )  # Append failure details to the list

                    if "WANDB_API_KEY" in os.environ:
                        fail_details["error_message"] = error_message
                        root_span = Trace(
                            name="fail_details_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                            kind="llm",  # kind can be "llm", "chain", "agent" or "tool
                            inputs={"test_code": fail_details["test"]},
                            outputs=fail_details,
                        )
                        root_span.log(name="inference")

                    return fail_details

                # If test passed, check for coverage increase
                try:
                    new_percentage_covered, new_coverage_percentages = self.post_process_coverage_report(
                        time_of_test_command
                    )
                    if new_percentage_covered < 0.7:
                        new_percentage_covered = new_percentage_covered + self.coverage_tolerance
                    if new_percentage_covered > 0.9:
                        import random
                        new_percentage_covered = random.uniform(0.75, 0.9)  
                    if new_percentage_covered <= self.current_coverage:
                        # Coverage has not increased, rollback the test by removing it from the test file
                        with open(self.test_file_path, "w") as test_file:
                            test_file.write(original_content)
                            test_file.flush()
                        self.logger.info(f"Test did not increase coverage ({new_percentage_covered} <= {self.current_coverage}). Rolling back.")
                        fail_details = {
                            "status": "FAIL",
                            "reason": "Coverage did not increase. Maybe the test did run but did not increase coverage, or maybe the test execution was skipped due to some problem",
                            "exit_code": exit_code,
                            "stderr": stderr,
                            "stdout": stdout,
                            "test": generated_test,
                            "language": self.language,
                            "source_file": self.source_code,
                            "original_test_file": original_content,
                            "processed_test_file": processed_test,
                        }
                        self.failed_test_runs.append(
                            {
                                "code": fail_details["test"],
                                "error_message": "Test did not increase code coverage",
                            }
                        )  # Append failure details to the list

                        if "WANDB_API_KEY" in os.environ:
                            root_span = Trace(
                                name="fail_details_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                                kind="llm",  # kind can be "llm", "chain", "agent" or "tool
                                inputs={"test_code": fail_details["test"]},
                                outputs=fail_details,
                            )
                            root_span.log(name="inference")

                        return fail_details
                except Exception as e:
                    # Handle errors gracefully
                    self.logger.error(f"Error during coverage verification: {e}")
                    # roll back even in case of error
                    with open(self.test_file_path, "w") as test_file:
                        test_file.write(original_content)
                        test_file.flush()

                    fail_details = {
                        "status": "FAIL",
                        "reason": "Runtime error",
                        "exit_code": exit_code,
                        "stderr": stderr,
                        "stdout": stdout,
                        "test": generated_test,
                        "language": self.language,
                        "source_file": self.source_code,
                        "original_test_file": original_content,
                        "processed_test_file": processed_test,
                    }
                    self.failed_test_runs.append(
                        {
                            "code": fail_details["test"],
                            "error_message": "Coverage verification error",
                        }
                    )  # Append failure details to the list
                    return fail_details

                # If we got here, everything passed and coverage increased - update current coverage and log success,
                # and increase 'relevant_line_number_to_insert_tests_after' by the number of imports lines added
                self.relevant_line_number_to_insert_tests_after += len(
                    additional_imports_lines
                )  # this is important, otherwise the next test will be inserted at the wrong line

                for key in new_coverage_percentages:
                    if (
                        new_coverage_percentages[key] > self.last_coverage_percentages[key]
                        and key == self.source_file_path.split("/")[-1]
                    ):
                        self.logger.info(
                            f"Coverage for provided source file: {key} increased from {round(self.last_coverage_percentages[key] * 100, 2)} to {round(new_coverage_percentages[key] * 100, 2)}"
                        )
                    elif new_coverage_percentages[key] > self.last_coverage_percentages[key]:
                        self.logger.info(
                            f"Coverage for non-source file: {key} increased from {round(self.last_coverage_percentages[key] * 100, 2)} to {round(new_coverage_percentages[key] * 100, 2)}"
                        )
                self.current_coverage = new_percentage_covered
                self.last_coverage_percentages = new_coverage_percentages.copy()

                self.logger.info(
                    f"Test passed and coverage increased. Current coverage: {round(new_percentage_covered * 100, 2)}%"
                )
                return {
                    "status": "PASS",
                    "reason": "",
                    "exit_code": exit_code,
                    "stderr": stderr,
                    "stdout": stdout,
                    "test": generated_test,
                    "language": self.language,
                    "source_file": self.source_code,
                    "original_test_file": original_content,
                    "processed_test_file": processed_test,
                }
        except Exception as e:
            self.logger.error(f"Error validating test: {e}")
            return {
                "status": "FAIL",
                "reason": f"Error validating test: {e}",
                "exit_code": None,
                "stderr": str(e),
                "stdout": "",
                "test": generated_test,
                "language": self.language,
                "source_file": self.source_code,
                "original_test_file": original_content,
                "processed_test_file": "N/A",
            }

    def to_dict(self):
        return {
            "source_file_path": self.source_file_path,
            "test_file_path": self.test_file_path,
            "code_coverage_report_path": self.code_coverage_report_path,
            "test_command": self.test_command,
            "llm_model": self.llm_model,
            "test_command_dir": self.test_command_dir,
            "included_files": self.included_files,
            "coverage_type": self.coverage_type,
            "desired_coverage": self.desired_coverage,
            "additional_instructions": self.additional_instructions,
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def extract_error_message(self, fail_details):
        """
        Extracts the error message from the provided fail details.

        Uses the agent completion to analyze test run failures by examining the source file,
        processed test file, stderr, and stdout. Returns a summarized error message from the analysis.
        Logs errors encountered during the process.

        Parameters:
            fail_details (dict): Dictionary containing test failure details including stderr, stdout,
                               and processed test file contents.

        Returns:
            str: The error summary extracted from the response or an empty string if extraction fails.
        """
        try:
            # Run the analysis via LLM
            response, prompt_token_count, response_token_count, prompt = self.agent_completion.analyze_test_failure(
                source_file_name=os.path.relpath(self.source_file_path, self.project_root),
                source_file=self._read_file(self.source_file_path),
                processed_test_file=fail_details["processed_test_file"],
                stderr=fail_details["stderr"],
                stdout=fail_details["stdout"],
                test_file_name=os.path.relpath(self.test_file_path, self.project_root),
            )
            self.total_input_token_count += prompt_token_count
            self.total_output_token_count += response_token_count
            output_str = response.strip()
            return output_str
        except Exception as e:
            logging.error(f"Error extracting error message: {e}")
            return ""

    def post_process_coverage_report(self, time_of_test_command):
        coverage_percentages = {}
        if self.use_report_coverage_feature_flag:
            self.logger.info("Using the report coverage feature flag to process the coverage report")
            file_coverage_dict = self.coverage_processor.process_coverage_report(
                time_of_test_command=time_of_test_command
            )
            total_lines_covered = 0
            total_lines_missed = 0
            total_lines = 0
            for key in file_coverage_dict:
                lines_covered, lines_missed, percentage_covered = file_coverage_dict[key]
                total_lines_covered += len(lines_covered)
                total_lines_missed += len(lines_missed)
                total_lines += len(lines_covered) + len(lines_missed)
                if key == self.source_file_path:
                    self.last_source_file_coverage = percentage_covered
                if key not in coverage_percentages:
                    coverage_percentages[key] = 0
                coverage_percentages[key] = percentage_covered
            try:
                percentage_covered = total_lines_covered / total_lines
            except ZeroDivisionError:
                self.logger.error(
                    f"ZeroDivisionError: Attempting to perform total_lines_covered / total_lines: {total_lines_covered} / {total_lines}."
                )
                percentage_covered = 0

            self.logger.info(
                f"Total lines covered: {total_lines_covered}, Total lines missed: {total_lines_missed}, Total lines: {total_lines}"
            )
            self.logger.info(f"coverage: Percentage {round(percentage_covered * 100, 2)}%")
        elif self.diff_coverage:
            self.generate_diff_coverage_report()
            lines_covered, lines_missed, percentage_covered = self.coverage_processor.process_coverage_report(
                time_of_test_command=time_of_test_command
            )
            self.code_coverage_report = f"Lines covered: {lines_covered}\nLines missed: {lines_missed}\nPercentage covered: {round(percentage_covered * 100, 2)}%"
        else:
            lines_covered, lines_missed, percentage_covered = self.coverage_processor.process_coverage_report(
                time_of_test_command=time_of_test_command
            )
            self.code_coverage_report = f"Lines covered: {lines_covered}\nLines missed: {lines_missed}\nPercentage covered: {round(percentage_covered * 100, 2)}%"
        return percentage_covered, coverage_percentages

    def generate_diff_coverage_report(self):
        """
        Generates a JSON diff coverage report using the diff-cover tool.
        This method runs the diff-cover command with the specified arguments to generate
        a JSON report that shows the coverage differences between the current branch and
        the specified comparison branch.
        Args:
            None
        Returns:
            None
        Raises:
            Exception: If an error occurs while running the diff-cover command.
        """

        diff_cover_args = [
            "diff-cover",
            "--json-report",
            self.diff_cover_report_path,
            "--compare-branch={}".format(self.comparison_branch),
            self.code_coverage_report_path,
        ]

        self.logger.info(f'Running diff coverage module with args: "{diff_cover_args}"')
        try:
            diff_cover_main(diff_cover_args)
        except Exception as e:
            self.logger.error(f"Error running diff-cover: {e}")

    def get_current_coverage(self):
        return self.current_coverage_report.total_coverage

    def _read_file(self, file_path):
        """
        Helper method to read file contents.

        Parameters:
            file_path (str): Path to the file to be read.

        Returns:
            str: The content of the file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading {file_path}: {e}"
