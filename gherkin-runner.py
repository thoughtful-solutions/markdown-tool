#!/usr.bin/env python3
"""
Gherkin Test Runner with Cross-Platform Support
Executes Gherkin feature blocks extracted from Markdown files.
Handles line ending issues and works on both Windows and Linux.
"""

import re
import os
import sys
import shutil
import subprocess
import json
import argparse
from pathlib import Path
from gherkin.parser import Parser

# This script now requires markdown-it-py
try:
    from markdown_it import MarkdownIt
except ImportError:
    print("ERROR: markdown-it-py is not installed. Please run: pip install markdown-it-py", file=sys.stderr)
    sys.exit(2)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def normalize_line_endings(text):
    """
    Normalize line endings to Unix format (LF only).
    This removes Windows CRLF issues that cause bash parsing errors.
    """
    if text is None:
        return ""
    # Replace CRLF with LF, then ensure no stray CR characters remain
    return text.replace('\r\n', '\n').replace('\r', '\n')


def normalize_gherkin_keywords(text):
    """
    Pre-processes Gherkin text to standardize keywords to Title Case,
    allowing the parser to handle uppercase or mixed-case keywords.
    """
    if text is None:
        return ""
    
    # Use re.IGNORECASE and re.MULTILINE for robust, case-insensitive matching
    # at the start of each line.
    text = re.sub(r"^\s*FEATURE:", "Feature:", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*BACKGROUND:", "Background:", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*SCENARIO:", "Scenario:", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*GIVEN\s", "Given ", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*WHEN\s", "When ", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*THEN\s", "Then ", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*AND\s", "And ", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*BUT\s", "But ", text, flags=re.IGNORECASE | re.MULTILINE)
    
    return text


def clean_script_content(script_content):
    """
    Clean, prepare, and strip shebang from script content for execution.
    """
    if not script_content:
        return ""
    
    cleaned = normalize_line_endings(script_content)
    lines = cleaned.split('\n')

    # Strip shebang if present, as the runner calls bash explicitly
    if lines and lines[0].strip().startswith("#!"):
        lines.pop(0)
    
    # Remove trailing whitespace from each line while preserving structure
    cleaned_lines = [line.rstrip() for line in lines]
    
    return '\n'.join(cleaned_lines)


def print_colored(text, color='', end='\n', file=sys.stdout):
    """Print text with color if supported to the specified file stream."""
    # Check if we're in a terminal that supports colors for the given file stream
    if hasattr(file, 'isatty') and file.isatty():
        print(f"{color}{text}{Colors.RESET}", end=end, file=file)
    else:
        print(text, end=end, file=file)


def find_bash_executable():
    """
    Find a suitable bash executable, prioritizing native Windows shells (like Git Bash)
    over WSL to ensure consistent behavior and environment.
    """
    # On non-Windows systems, 'bash' in the PATH is almost always the right choice.
    if sys.platform != "win32":
        return 'bash'

    # --- On Windows, find a native bash, avoiding WSL ---

    # 1. Best Method: Find bash relative to git.exe in the PATH.
    git_path = shutil.which('git')
    if git_path:
        bash_path = os.path.join(os.path.dirname(git_path), 'bash.exe')
        if os.path.exists(bash_path):
            return bash_path

    # 2. Fallback: Check common hardcoded installation paths for Git Bash.
    possible_paths = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Git", "bin", "bash.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Git", "bin", "bash.exe"),
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        possible_paths.append(os.path.join(local_app_data, "Programs", "Git", "bin", "bash.exe"))

    for path in possible_paths:
        if os.path.exists(path):
            return path

    # 3. Last Resort: Check if 'bash' is in the PATH and verify it's not WSL.
    bash_in_path = shutil.which('bash')
    if bash_in_path:
        try:
            result = subprocess.run(
                [bash_in_path, '-c', 'uname -o'],
                capture_output=True, text=True, timeout=3, encoding='utf-8'
            )
            if result.returncode == 0 and 'linux' not in result.stdout.lower():
                return bash_in_path
        except (subprocess.TimeoutExpired, OSError):
            pass

    # 4. Failure: If we've reached this point, no suitable bash was found.
    print_colored("ERROR: A suitable non-WSL bash executable was not found.", Colors.RED, file=sys.stderr)
    print_colored("Please install Git for Windows (https://git-scm.com/downloads) and ensure its 'bin' directory is in your system's PATH.", Colors.YELLOW, file=sys.stderr)
    sys.exit(1)


def execute_shell_script(script_content, variables=None, context=None, debug=False, timeout=60):
    """
    Execute a shell script, passing variables via the environment for robustness.
    """
    if variables is None:
        variables = {}
    if context is None:
        context = {}

    cleaned_script = clean_script_content(script_content)

    if not cleaned_script.strip():
        return subprocess.CompletedProcess(
            args=['bash'], returncode=1, stdout='', stderr='Empty script content'
        )

    bash_executable = find_bash_executable()
    
    try:
        script_env = os.environ.copy()
        all_vars = {**context, **variables}
        
        for key, value in all_vars.items():
            script_env[key] = str(value)

        command = [bash_executable, '-c', cleaned_script]

        if debug:
            print("--- DEBUG: Variables passed to script (as environment) ---")
            print(json.dumps(all_vars, indent=2) if all_vars else "None")
            print(f"--- DEBUG: Using bash executable: {bash_executable} ---")
            print("--- DEBUG: Executing script ---")
            print(cleaned_script)
            print("------------------------------------------")

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            env=script_env
        )
            
        if debug:
            print(f"--- DEBUG: Result (Exit Code: {result.returncode}) ---")
            if result.stdout and result.stdout.strip():
                print(f"  stdout:\n{result.stdout}")
            if result.stderr and result.stderr.strip():
                print(f"  stderr:\n{result.stderr}")
            print("---------------------------------")
            
        return result
            
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=[bash_executable, '-c', '...'], 
            returncode=124, 
            stdout='', 
            stderr=f'Script execution timed out after {timeout} seconds'
        )
    except Exception as e:
        return subprocess.CompletedProcess(
            args=[bash_executable, '-c', '...'], 
            returncode=1, 
            stdout='', 
            stderr=f'Error executing script: {str(e)}'
        )


def load_implementation_file(file_path, debug=False):
    """
    Load implementation file with automatic line ending normalization.
    """
    implementations = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8', newline=None) as f:
            content = f.read()
        
        content = normalize_line_endings(content)
        
        if debug:
            print(f"Loading implementations from: {file_path}")
        
        implements_pattern = r'^IMPLEMENTS\s+(.+?)$'
        lines = content.split('\n')
        
        current_step = None
        current_script = []
        
        for line in lines:
            implements_match = re.match(implements_pattern, line.strip())
            
            if implements_match:
                if current_step and current_script:
                    script_content = '\n'.join(current_script)
                    implementations[current_step] = clean_script_content(script_content)
                
                current_step = implements_match.group(1).strip()
                current_script = []
            elif current_step is not None:
                current_script.append(line)
        
        if current_step and current_script:
            script_content = '\n'.join(current_script)
            implementations[current_step] = clean_script_content(script_content)
        
        if debug:
            print(f"Found {len(implementations)} implementations")
            for step_pattern in implementations.keys():
                print(f"  - {step_pattern}")
            
    except Exception as e:
        print(f"Error loading implementation file {file_path}: {str(e)}")
    
    return implementations


def find_implementation_files(impl_dir, debug=False):
    """
    Find all implementation files in the specified directory.
    """
    impl_dir = Path(impl_dir)
    if not impl_dir.exists():
        if debug:
            print(f"Implementation directory does not exist: {impl_dir}")
        return []
    
    gherkin_files = list(impl_dir.glob('*.gherkin'))
    
    if debug:
        print(f"Searching for implementation files in: {impl_dir.absolute()}")
        print(f"Found {len(gherkin_files)} implementation file(s)")
        for file in gherkin_files:
            print(f"  - {file.name}")
    
    return [str(f) for f in gherkin_files]


def load_all_implementations(impl_files, debug=False):
    """
    Load all implementation files and combine them into a single dictionary.
    """
    all_implementations = {}
    
    print(f"Loading implementations from {len(impl_files)} file(s)...")
    
    for impl_file in impl_files:
        implementations = load_implementation_file(impl_file, debug)
        
        for step_pattern, script in implementations.items():
            if step_pattern in all_implementations:
                print(f"{Colors.YELLOW}Warning: Duplicate implementation for step: {step_pattern}{Colors.RESET}")
            all_implementations[step_pattern] = script
    
    print(f"Found {len(all_implementations)} step implementations.")
    return all_implementations


def run_step(step_text, step_keyword, implementations, context=None, debug=False):
    """
    Run a single step by finding a matching implementation.
    """
    full_step_text = f"{step_keyword} {step_text}".strip()
    
    for pattern, script_content in implementations.items():
        try:
            match = re.match(f"^{pattern}$", step_text, re.IGNORECASE)
            
            if not match:
                match = re.match(f"^{pattern}$", full_step_text, re.IGNORECASE)

            if match:
                variables = {}
                for i, group in enumerate(match.groups(), 1):
                    variables[f'MATCH_{i}'] = group if group is not None else ""
                
                result = execute_shell_script(script_content, variables, context, debug)
                
                return {
                    'status': 'passed' if result.returncode == 0 else 'failed',
                    'output': result.stderr if result.returncode != 0 and result.stderr.strip() else None,
                    'stdout': result.stdout if result.stdout else None,
                    'stderr': result.stderr if result.stderr else None,
                    'exit_code': result.returncode
                }
                
        except re.error as e:
            if debug:
                print(f"Invalid regex pattern '{pattern}': {e}")
            continue
    
    return {'status': 'undefined', 'output': f'No implementation found for: {full_step_text}'}


def extract_from_markdown(markdown_file):
    """
    Parses a Markdown file to extract the Gherkin feature block and the Category metadata.
    """
    gherkin_content = None
    category = None
    md_parser = MarkdownIt()
    
    try:
        markdown_path = Path(markdown_file)
        if not markdown_path.is_file():
             raise FileNotFoundError
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tokens = md_parser.parse(content)
        
        for i, token in enumerate(tokens):
            # Extract Gherkin content from a fenced code block
            if token.type == 'fence' and token.info == 'gherkin':
                gherkin_content = token.content
            
            # Extract Category from the metadata bullet list
            if (token.type == 'inline' and 
                token.content.strip().lower().startswith('**category**:')):
                
                match = re.search(r'^\*\*Category\*\*:\s*(\w+)', token.content.strip(), re.IGNORECASE)
                if match:
                    category = match.group(1).lower()

        return gherkin_content, category
    except FileNotFoundError:
        print_colored(f"Error: Markdown file not found at {markdown_file}", Colors.RED, file=sys.stderr)
        return None, None
    except Exception as e:
        print_colored(f"Error parsing markdown file {markdown_file}: {e}", Colors.RED, file=sys.stderr)
        return None, None


def run_markdown_file(markdown_file, implementations, output_dir, debug=False, json_output=False):
    """
    Extracts Gherkin from a markdown file and runs it using the provided implementations.
    Returns the results and the extracted category.
    """
    feature_content, category = extract_from_markdown(markdown_file)

    if not feature_content:
        error_msg = f"No Gherkin content found in {markdown_file}"
        if not json_output:
            print_colored(f"Error: {error_msg}", Colors.RED, file=sys.stderr)
        return {'error': error_msg, 'summary': {}}, category

    try:
        feature_content = normalize_line_endings(feature_content)
        # **MODIFICATION**: Normalize keywords before parsing
        feature_content = normalize_gherkin_keywords(feature_content)
        
        parser = Parser()
        gherkin_document = parser.parse(feature_content)
        
        if not gherkin_document.get('feature'):
            raise Exception("No feature found in the Gherkin block")
        
        feature = gherkin_document['feature']
        
        results = {
            'feature': {'name': feature['name'], 'file': markdown_file},
            'scenarios': [],
            'summary': {
                'scenarios': {'total': 0, 'passed': 0, 'failed': 0},
                'steps': {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'undefined': 0}
            }
        }
        
        if not json_output:
            print_colored(f"Feature: {feature['name']}", Colors.BOLD)
        
        for child in feature.get('children', []):
            if 'scenario' in child:
                scenario = child['scenario']
                scenario_result = {'name': scenario['name'], 'status': 'passed', 'steps': []}
                results['summary']['scenarios']['total'] += 1
                
                if not json_output:
                    print_colored(f"\n  Scenario: {scenario['name']}")
                
                scenario_failed = False
                scenario_context = {}

                # Calculate and inject the category output directory into the context
                if category:
                    output_category_dir = Path(output_dir) / 'categories' / category
                    # Ensure the directory exists *before* steps run
                    output_category_dir.mkdir(parents=True, exist_ok=True)
                    # Pass the absolute, resolved path to the script
                    scenario_context['CATEGORY_DIR'] = str(output_category_dir.resolve())
                else:
                    # Fallback to the base output dir if no category is found
                    base_dir = Path(output_dir).resolve()
                    base_dir.mkdir(parents=True, exist_ok=True)
                    scenario_context['CATEGORY_DIR'] = str(base_dir)
                
                is_first_step = True 

                for step in scenario.get('steps', []):
                    results['summary']['steps']['total'] += 1
                    step_keyword = step['keyword'].strip()
                    step_text = step['text']
                    
                    if scenario_failed:
                        step_result = {'keyword': step_keyword, 'text': step_text, 'status': 'skipped'}
                        results['summary']['steps']['skipped'] += 1
                        if not json_output:
                            print_colored(f"    - {step_keyword} {step_text}", Colors.YELLOW)
                    else:
                        step_result = run_step(step_text, step_keyword, implementations, scenario_context, debug)
                        step_result['keyword'] = step_keyword
                        step_result['text'] = step_text
                        
                        if step_result['status'] == 'passed':
                            results['summary']['steps']['passed'] += 1
                            if step_result.get('stdout') is not None:
                                # This is the key change to preserve the initial context
                                if is_first_step: 
                                    scenario_context['GIVEN_STDOUT'] = step_result['stdout'].strip()
                                    is_first_step = False 
                                
                                # Always update the previous step's output for simple chaining
                                scenario_context['PREVIOUS_STEP_STDOUT'] = step_result['stdout'].strip()

                            if not json_output:
                                print_colored(f"    V {step_keyword} {step_text}", Colors.GREEN)
                        else:
                            scenario_failed = True
                            scenario_result['status'] = 'failed'
                            if step_result['status'] == 'failed':
                                results['summary']['steps']['failed'] += 1
                                if not json_output:
                                    print_colored(f"    ? {step_keyword} {step_text}", Colors.RED)
                                    if step_result.get('stderr'):
                                        print_colored(f"      Error: {step_result['stderr']}", Colors.RED, file=sys.stderr)
                            elif step_result['status'] == 'undefined':
                                results['summary']['steps']['undefined'] += 1
                                if not json_output:
                                    print_colored(f"    ? {step_keyword} {step_text}", Colors.MAGENTA)
                                    if step_result.get('output'):
                                        print_colored(f"      {step_result['output']}", Colors.MAGENTA, file=sys.stderr)
                    
                    scenario_result['steps'].append(step_result)
                
                if scenario_result['status'] == 'passed':
                    results['summary']['scenarios']['passed'] += 1
                else:
                    results['summary']['scenarios']['failed'] += 1
                
                results['scenarios'].append(scenario_result)
        
        return results, category
        
    except Exception as e:
        error_msg = f"Error processing Gherkin from {markdown_file}: {e}"
        if not json_output:
            print_colored(error_msg, Colors.RED, file=sys.stderr)
        return {'error': error_msg, 'summary': {}}, category


def print_summary(results):
    """Print a summary of test results."""
    if 'summary' not in results:
        return
    summary = results['summary']
    
    print_colored("\n" + "-" * 50)
    print_colored("Run Summary:", Colors.BOLD)
    
    scenarios = summary.get('scenarios', {})
    print_colored(f"  Scenarios: {scenarios.get('total', 0)} total, " +
                 f"{Colors.GREEN}{scenarios.get('passed', 0)} passed{Colors.RESET}, {Colors.RED}{scenarios.get('failed', 0)} failed{Colors.RESET}")
    
    steps = summary.get('steps', {})
    print_colored(f"  Steps:     {steps.get('total', 0)} total, " +
                 f"{Colors.GREEN}{steps.get('passed', 0)} passed{Colors.RESET}, {Colors.RED}{steps.get('failed', 0)} failed{Colors.RESET}, " +
                 f"{Colors.YELLOW}{steps.get('skipped', 0)} skipped{Colors.RESET}, {Colors.MAGENTA}{steps.get('undefined', 0)} undefined{Colors.RESET}")
    
    print_colored("-" * 50)


def main():
    """Main entry point."""
    
    # --- THIS IS THE INTEGRATED HELP TEXT ---
    epilog_text = """
Implementation scripts (in the --impl-dir) have access to several
environment variables during execution:

  $GIVEN_STDOUT
    The complete stdout from the first 'Given' step in the scenario.
    This is stable and persists across all steps.

  $PREVIOUS_STEP_STDOUT
    The stdout from the *immediately* preceding step.

  $CATEGORY_DIR
    The calculated, absolute path to the output directory for the
    current feature's category (e.g., ../dashboard/categories/operations).
    This is derived from the --output-dir and the **Category** metadata.

  $MATCH_1, $MATCH_2, ...
    Capture groups from the step's 'IMPLEMENTS' regex pattern.
    (e.g., IMPLEMENTS an inventory for (.*) would put the matched
    text into $MATCH_1)
"""

    parser = argparse.ArgumentParser(
        description='Gherkin Test Runner for Markdown Files',
        epilog=epilog_text,
        formatter_class=argparse.RawTextHelpFormatter
    )
    # --- END OF INTEGRATED HELP TEXT ---

    parser.add_argument('markdown_file', help='Path to the .md file containing Gherkin features')
    parser.add_argument('--impl-dir', default='../gherkin-implements', 
                       help='Directory containing implementation files (default: ../gherkin-implements)')
    
    parser.add_argument('--output-dir', default='../dashboard',
                        help='Base directory for output. A category-specific subdir (e.g., "categories/<category_name>") will be created and passed to scripts as $CATEGORY_DIR. (default: ../dashboard)')

    parser.add_argument('--json', action='store_true', help='Output results as JSON to stdout')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--display', action='store_true', help='Display extracted Gherkin and category, then exit')
    parser.add_argument('implementation_files', nargs='*', help='Specific implementation files to use (overrides --impl-dir)')
    
    args = parser.parse_args()
    
    # Handle the new --display flag
    if args.display:
        gherkin_content, category = extract_from_markdown(args.markdown_file)
        print_colored("--- Gherkin Display Mode ---", Colors.CYAN + Colors.BOLD)
        print(f"\nFile: {Path(args.markdown_file).name}")
        
        print_colored("\n== Output Category ==", Colors.YELLOW)
        print(category if category else "Not Found")
        
        print_colored("\n== Gherkin to be Executed ==", Colors.YELLOW)
        print(gherkin_content.strip() if gherkin_content else "Not Found")
        
        sys.exit(0)

    if not args.json:
        print_colored("--- Gherkin Markdown Test Runner ---", Colors.CYAN + Colors.BOLD)
    
    if args.implementation_files:
        impl_files = args.implementation_files
    else:
        impl_files = find_implementation_files(args.impl_dir, args.debug)
    
    if not impl_files:
        print_colored(f"No implementation files found in {args.impl_dir}", Colors.RED, file=sys.stderr)
        sys.exit(1)
    
    implementations = load_all_implementations(impl_files, args.debug)
    
    if not implementations:
        print_colored("No step implementations found", Colors.RED, file=sys.stderr)
        sys.exit(1)
    
    results, category = run_markdown_file(args.markdown_file, implementations, args.output_dir, args.debug, args.json)
    
    # Write log file to the specified directory structure
    if category:
        try:
            output_base_dir = Path(args.output_dir)
            output_category_dir = output_base_dir / 'categories' / category
            
            markdown_path = Path(args.markdown_file)
            log_filename = markdown_path.with_suffix('.stdout').name
            output_log_path = output_category_dir / log_filename
            
            with open(output_log_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            if not args.json:
                 print_colored(f"INFO: Results log written to {output_log_path}", Colors.BLUE)

        except Exception as e:
            print_colored(f"Error writing log file: {e}", Colors.RED, file=sys.stderr)
    elif 'error' not in results:
        print_colored("Warning: 'Category' not found in metadata. Cannot write log file.", Colors.YELLOW, file=sys.stderr)

    # Print to standard output as requested
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_summary(results)
    
    if 'error' in results or results.get('summary', {}).get('scenarios', {}).get('failed', 0) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
