#!/usr/bin/env python3
"""
Markdown Validator CLI Tool
A Python CLI tool for Markdown document validation and management.
Supports structure validation via spec.yaml and hyperlink validation via links.yaml.
"""

import argparse
from collections import defaultdict
import sys
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum, Flag
import logging
import os

try:
    from markdown_it import MarkdownIt
    from markdown_it.token import Token
except ImportError:
    print("ERROR: markdown-it-py not installed. Run: pip install markdown-it-py")
    sys.exit(2)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Defined regex as a constant for reusability and clarity
RELATIVE_LINK_PATTERN = re.compile(r'\[(?:[^\]]+)\]\(([^)]+)\)')


class ErrorLevel(Enum):
    """Error severity levels for validation."""
    FATAL = "FATAL"
    WARN = "WARN"
    INFO = "INFO"


@dataclass
class ValidationResult:
    """Stores validation results for a single file."""
    filename: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class MarkdownValidator:
    """Main validator class for Markdown documents."""

    def __init__(self, verbose: bool = False, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet
        self.md_parser = MarkdownIt()
        self.spec = None
        self.links_spec = None

    def log(self, level: ErrorLevel, message: str):
        """Centralised logging with level prefixes."""
        if self.quiet and level != ErrorLevel.FATAL:
            return

        prefix = f"[{level.value}]"
        if level == ErrorLevel.FATAL:
            logger.error(f"{prefix} {message}")
        elif level == ErrorLevel.WARN:
            logger.warning(f"{prefix} {message}")
        else:
            logger.info(f"{prefix} {message}")

    def _load_yaml_file(self, file_path: Path, spec_name: str) -> Optional[Dict]:
        """Generic YAML file loader."""
        if not file_path.exists():
            if self.verbose:
                self.log(ErrorLevel.INFO, f"No {spec_name} found at {file_path}")
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.log(ErrorLevel.FATAL, f"Failed to parse {spec_name}: {e}")
            return None
        except Exception as e:
            self.log(ErrorLevel.FATAL, f"Error loading {spec_name}: {e}")
            return None

    def load_spec(self, spec_path: Path) -> bool:
        """Load and validate spec.yaml file."""
        self.spec = self._load_yaml_file(spec_path, "spec.yaml")
        if not self.spec:
            return False

        if 'structure' not in self.spec:
            self.log(ErrorLevel.WARN, "spec.yaml missing 'structure' key")
            return False

        # Set defaults for each block
        for block in self.spec['structure']:
            block.setdefault('min_occurrences', 1)
            block.setdefault('max_occurrences', None)
            block.setdefault('error_level', 'FATAL')

            if 'sequence' not in block:
                self.log(ErrorLevel.WARN, "Block missing 'sequence' key in spec.yaml")
                return False
        return True

    def load_links_spec(self, links_path: Path) -> bool:
        """Load and validate links.yaml file."""
        self.links_spec = self._load_yaml_file(links_path, "links.yaml")
        return self.links_spec is not None

    def find_markdown_files(self, directory: Path) -> List[Path]:
        """Recursively find all Markdown files, excluding hidden directories."""
        md_files = []
        for path in directory.rglob('*.md'):
            if any(part.startswith('.') for part in path.parts):
                continue
            md_files.append(path)
        return sorted(md_files)

    def _describe_step(self, step: Dict[str, Any]) -> str:
        """Creates a human-readable description of a validation step."""
        description = step['type']
        if step['type'] == 'heading_open' and 'level' in step:
            description = f"heading (H{step['level']})"
        elif step['type'] == 'paragraph_open':
            description = 'paragraph'
        elif step['type'] == 'fence' and 'info' in step:
            description = f"code block (`{step['info']}`)"
        if 'content_regex' in step:
            description += f" with content matching regex '{step['content_regex']}'"
        return description

    def validate_sequence_step(self, tokens: List[Token], token_index: int,
                              step: Dict[str, Any]) -> Tuple[bool, int, str]:
        """
        Validate a single sequence step against tokens.
        Returns: (success, tokens_consumed, error_message)
        """
        if token_index >= len(tokens):
            return False, 0, f"Expected {self._describe_step(step)}, but reached the end of the file."

        token = tokens[token_index]
        line_num = token.map[0] + 1 if token.map else 'N/A'

        if token.type != step['type']:
            return False, 0, f"line {line_num}: Expected {self._describe_step(step)}, but found a '{token.type}' instead."

        if 'level' in step and token.type == 'heading_open':
            expected_tag = f"h{step['level']}"
            if token.tag != expected_tag:
                return False, 0, f"line {line_num}: Expected heading level {step['level']} ({expected_tag}), but found level {token.tag[1:]} ({token.tag})."

        if 'info' in step and token.type == 'fence':
            if token.info != step['info']:
                return False, 0, f"line {line_num}: Expected code block language '{step['info']}', but found '{token.info}'."

        if 'content_regex' in step:
            content_to_check = ""
            if token.type in ['heading_open', 'paragraph_open']:
                if token_index + 1 < len(tokens) and tokens[token_index + 1].type == 'inline':
                    content_to_check = tokens[token_index + 1].content.strip()
            else:
                content_to_check = token.content

            pattern = re.compile(step['content_regex'])
            if not pattern.fullmatch(content_to_check):
                return False, 0, f"line {line_num}: Content does not fully match the expected pattern: {step['content_regex']}"

        return True, 1, ""

    def validate_block(self, tokens: List[Token], token_index: int,
                      block: Dict[str, Any]) -> Tuple[int, Optional[str]]:
        """
        Validate a block against tokens.
        Returns: (tokens_consumed, error_message)
        """
        sequence = block['sequence']
        current_index = token_index
        for step_idx, step in enumerate(sequence):
            success, consumed, error = self.validate_sequence_step(tokens, current_index, step)
            if not success:
                block_description = self._describe_step(sequence[0])
                return 0, f"In block starting with '{block_description}', step {step_idx + 1} failed: {error}"
            current_index += consumed
            if tokens[current_index - 1].type in ['heading_open', 'paragraph_open', 'list_item_open']:
                started_with_list_item = any(s['type'] == 'list_item_open' for s in sequence)
                if started_with_list_item and step_idx + 1 == len(sequence):
                    list_item_depth = 1
                    while current_index < len(tokens):
                        token = tokens[current_index]
                        if token.type == 'list_item_open':
                            list_item_depth += 1
                        elif token.type == 'list_item_close':
                            list_item_depth -= 1
                            if list_item_depth == 0:
                                current_index += 1
                                break
                        current_index += 1
                elif not started_with_list_item or step_idx + 1 == len(sequence):
                    while current_index < len(tokens):
                        if tokens[current_index].type in ['inline', 'heading_close', 'paragraph_close']:
                            current_index += 1
                        else:
                            break
        return current_index - token_index, None

    def validate_structure(self, filepath: Path, tokens: List[Token], result: ValidationResult) -> bool:
        """Validate document structure against spec.yaml, now accepting tokens."""
        if not self.spec:
            return True

        token_index = 0
        for block in self.spec['structure']:
            min_occur = block['min_occurrences']
            max_occur = block['max_occurrences']
            error_level = ErrorLevel(block.get('error_level', 'FATAL').upper())

            matches = 0
            while token_index < len(tokens):
                consumed, error = self.validate_block(tokens, token_index, block)
                if consumed > 0:
                    matches += 1
                    token_index += consumed
                    if max_occur is not None and matches >= max_occur:
                        break
                else:
                    if matches < min_occur:
                        message = f"{filepath.name}: {error}"
                        if error_level == ErrorLevel.FATAL:
                            result.errors.append(message)
                            self.log(ErrorLevel.FATAL, message)
                        else:
                            result.warnings.append(message)
                            self.log(ErrorLevel.WARN, message)
                        return False if error_level == ErrorLevel.FATAL else True
                    break

            if matches < min_occur:
                # Add line number to occurrence errors, reporting at the end of the file.
                last_line = tokens[-1].map[1] if tokens and tokens[-1].map else 'EOF'
                block_description = self._describe_step(block['sequence'][0])
                message = (f"{filepath.name}: line {last_line}: Expected the block starting with "
                           f"'{block_description}' to appear at least {min_occur} time(s), but it appeared {matches} time(s).")
                if error_level == ErrorLevel.FATAL and message not in result.errors:
                    result.errors.append(message)
                    self.log(ErrorLevel.FATAL, message)
                    return False
                elif error_level == ErrorLevel.WARN and message not in result.warnings:
                    result.warnings.append(message)
                    self.log(ErrorLevel.WARN, message)
        return True

    def extract_links_with_location(self, tokens: List[Token]) -> List[Tuple[str, int]]:
        """Extract all relative links and their line numbers from tokens."""
        relative_links = []
        for token in tokens:
            if token.type == 'link_open':
                url = token.attrs.get('href', '')
                line_num = token.map[0] + 1 if token.map else 0
                if not url.startswith(('http://', 'https://', 'mailto:', '#')):
                    relative_links.append((url, line_num))
        return relative_links

    def validate_links(self, filepath: Path, tokens: List[Token], result: ValidationResult) -> bool:
        """Validate hyperlinks against links.yaml, now accepting tokens."""
        if not self.links_spec:
            return True

        links_with_locations = self.extract_links_with_location(tokens)
        all_links = [link for link, _ in links_with_locations]

        if 'allowed_targets' in self.links_spec:
            for link, line_num in links_with_locations:
                link_path = filepath.parent / link
                link_valid = False
                for target in self.links_spec['allowed_targets']:
                    target_dir = filepath.parent / target['directory']
                    filename_pattern = re.compile(target['filename_regex'])
                    try:
                        if link_path.resolve().parent == target_dir.resolve() and filename_pattern.match(link_path.name):
                            link_valid = True
                            break
                    except FileNotFoundError:
                        continue
                if not link_valid:
                    message = f"{filepath.name}: line {line_num}: Invalid link target '{link}'"
                    result.warnings.append(message)
                    self.log(ErrorLevel.WARN, message)

        if 'required_links' in self.links_spec:
            required_links_map = self.links_spec.get('required_links', {})
            if str(filepath) in required_links_map:
                required = required_links_map[str(filepath)]
                for req_link in required:
                    if req_link not in all_links:
                        last_line = tokens[-1].map[1] if tokens and tokens[-1].map else 'EOF'
                        message = f"{filepath.name}: line {last_line}: Missing required link to '{req_link}'"
                        result.warnings.append(message)
                        self.log(ErrorLevel.WARN, message)
        return True

    def validate_file(self, filepath: Path) -> ValidationResult:
        """Validate a single Markdown file."""
        result = ValidationResult(filename=str(filepath))
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tokens = self.md_parser.parse(content)

            if not self.validate_structure(filepath, tokens, result):
                return result
            
            self.validate_links(filepath, tokens, result)

        except Exception as e:
            result.errors.append(f"Failed to process file: {e}")
            self.log(ErrorLevel.FATAL, f"{filepath.name}: {e}")
        return result

    def verify_project(self, directory: Path) -> int:
        """
        Verify all Markdown files in the project.
        Returns exit code: 0=success, 1=warnings, 2=errors
        """
        self.load_spec(directory / 'spec.yaml')
        self.load_links_spec(directory / 'links.yaml')

        md_files = self.find_markdown_files(directory)
        if not md_files:
            self.log(ErrorLevel.INFO, "No Markdown files found")
            return 0

        files_with_errors = 0
        files_with_warnings = 0

        for filepath in md_files:
            result = self.validate_file(filepath)
            status = "PASS"
            if result.has_errors:
                status = "FAIL"
            elif result.has_warnings:
                status = "WARN"

            self.log(ErrorLevel.INFO,
                    f"{status:<5} {filepath.name}: {len(result.errors)} errors, {len(result.warnings)} warnings")

            if result.has_errors:
                files_with_errors += 1
            if result.has_warnings:
                files_with_warnings += 1

        self.log(ErrorLevel.INFO,
                f"\nSummary: {len(md_files)} files validated, "
                f"{files_with_errors} with fatal errors, "
                f"{files_with_warnings} with warnings")

        if files_with_errors > 0:
            return 2
        elif files_with_warnings > 0:
            return 1
        return 0

# --- LinkValidator for the verify-link command ---

class LinkExitCode(Flag):
    OK = 0
    ERRORS = 1
    SYSTEM_ERROR = 16

@dataclass
class LinkValidationDetail:
    source_file: str
    target_link: str
    results: Dict[str, Tuple[str, str]] = field(default_factory=dict)

class LinkValidator:
    """Validator for the verify-link command based on links.yaml content."""

    def __init__(self, args):
        self.directory = Path(args.directory).resolve()
        self.verbose = args.verbose
        self.quiet = args.quiet
        self.exit_code = LinkExitCode.OK
        self.results: List[LinkValidationDetail] = []
        self.summary = {"total": 0, "broken": 0, "unidirectional": 0, "disallowed": 0}

    def _log(self, message: str, level: str = "INFO"):
        if self.quiet and level != "ERROR":
            return
        if level == "ERROR":
            logger.error(message)
        else:
            logger.info(message)

    def _add_exit_flag(self, flag: LinkExitCode):
        self.exit_code |= flag

    def _load_links_yaml(self, directory: Path) -> Optional[Dict]:
        path = directory / "links.yaml"
        if not path.exists():
            return None
        try:
            with path.open('r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"[ERROR] YAML parse error in {path}: {e}")
            self._add_exit_flag(LinkExitCode.SYSTEM_ERROR)
            return None
    
    def _build_link_graph(self, root_links_yaml: Dict) -> Dict[Path, Set[Path]]:
        """Builds a complete graph of all links from all relevant links.yaml files."""
        graph = defaultdict(set)
        dirs_to_scan = {self.directory}
        
        if 'allowed_targets' in root_links_yaml:
            for rule in root_links_yaml.get('allowed_targets', []):
                rule_dir = (self.directory / rule['directory']).resolve()
                if rule_dir.is_dir():
                    dirs_to_scan.add(rule_dir)

        for current_dir in dirs_to_scan:
            links_yaml = self._load_links_yaml(current_dir)
            if not links_yaml or 'established_links' not in links_yaml:
                continue

            for source_file, target_links in links_yaml.get('established_links', {}).items():
                if not target_links: continue
                source_abs = (current_dir / source_file).resolve()
                for target_link in target_links:
                    try:
                        target_abs = (current_dir / target_link.replace('\\', '/')).resolve()
                        graph[source_abs].add(target_abs)
                    except Exception:
                        continue
        return graph

    def _perform_all_checks(self, links_yaml: Dict):
        """Performs all validation checks and stores results."""
        allowed_targets = links_yaml.get('allowed_targets', [])
        established_links = links_yaml.get('established_links', {})

        if not established_links:
            return

        for source_file, target_links in established_links.items():
            if not target_links: continue
            for target_link in target_links:
                detail = LinkValidationDetail(source_file, target_link)
                self.summary["total"] += 1

                # 1. Allowed Target Check
                if not self._check_allowed_target(target_link, self.directory, allowed_targets):
                    self.summary["disallowed"] += 1
                    self._add_exit_flag(LinkExitCode.ERRORS)
                    detail.results['allowed'] = ('FAIL', 'Link does not match any rule.')
                else:
                    detail.results['allowed'] = ('PASS', '')

                # 2. File Existence Check
                target_path = self.directory / target_link.replace('\\', '/')
                if not target_path.exists():
                    self.summary["broken"] += 1
                    self._add_exit_flag(LinkExitCode.ERRORS)
                    detail.results['exists'] = ('FAIL', f"File not found at '{target_path.resolve()}'")
                    detail.results['bidi'] = ('SKIPPED', 'Target file does not exist.')
                else:
                    detail.results['exists'] = ('PASS', '')
                    # 3. Bidirectional Check (only if file exists)
                    status, msg = self._check_bidirectional(target_link, source_file, self.directory)
                    detail.results['bidi'] = (status, msg)
                    if status == "FAIL": self._add_exit_flag(LinkExitCode.ERRORS)
                
                self.results.append(detail)
    
    def _print_summary_report(self, links_yaml: Dict):
        """Prints the new default summary view with unidirectional counts."""
        self._log("Link Summary (Uni-TO | Total-TO <-> Total-FROM | Uni-FROM):")
        
        graph = self._build_link_graph(links_yaml)
        local_md_files = sorted([p for p in self.directory.glob('*.md')])

        for file_path in local_md_files:
            abs_path = file_path.resolve()
            
            from_links = graph.get(abs_path, set())
            f_total = len(from_links)

            t_total = sum(1 for targets in graph.values() if abs_path in targets)
            
            uf_count = sum(1 for target_path in from_links if abs_path not in graph.get(target_path, set()))
            
            ut_count = sum(1 for source_path, targets in graph.items() if abs_path in targets and source_path not in from_links)

            self._log(f"  [{ut_count:^3}] [{t_total:^3}] {file_path.name} [{f_total:^3}] [{uf_count:^3}]")

    def _print_verbose_report(self):
        """Prints the detailed, multi-check validation report."""
        for detail in self.results:
            self._log(f"\nVerifying link for: {detail.source_file}")
            self._log(f"  -> {detail.target_link}")

            allowed_status, allowed_msg = detail.results['allowed']
            icon = 'V' if allowed_status == 'PASS' else '?'
            self._log(f"     [{icon}] Allowed Target: {allowed_status}{' - ' + allowed_msg if allowed_msg else ''}")

            exists_status, exists_msg = detail.results['exists']
            icon = 'V' if exists_status == 'PASS' else '?'
            self._log(f"     [{icon}] File Exists: {exists_status}{' - ' + exists_msg if exists_msg else ''}")
            
            bidi_status, bidi_msg = detail.results['bidi']
            icon = "V" if bidi_status == "PASS" else "?" if bidi_status == "FAIL" else "?"
            self._log(f"     [{icon}] Bidirectional Link: {bidi_status} - {bidi_msg}")
        
        self._log("\n---")
        self._log("Verification Summary:")
        self._log(f"  - Total Links Checked: {self.summary['total']}")
        self._log(f"  - Broken Links (Not Found): {self.summary['broken']}")
        self._log(f"  - Disallowed Targets: {self.summary['disallowed']}")
        self._log(f"  - Unidirectional Links: {self.summary['unidirectional']}")

    def _print_error_details(self):
        """Prints a concise list of errors found during validation."""
        if self.quiet or self.exit_code == LinkExitCode.OK:
            return
        
        self._log("\n---", "ERROR")
        self._log("Validation Errors:", "ERROR")
        
        check_name_map = {
            'allowed': 'Allowed Target',
            'exists': 'File Existence',
            'bidi': 'Bidirectional Link'
        }

        for detail in self.results:
            for check_key, (status, msg) in detail.results.items():
                if status == 'FAIL':
                    check_name = check_name_map.get(check_key, check_key)
                    self._log(f"  - In '{detail.source_file}': Link to '{detail.target_link}'", "ERROR")
                    self._log(f"    Reason: [{check_name}] {msg}", "ERROR")

    def run(self) -> int:
        """Main execution method."""
        links_yaml_path = self.directory / "links.yaml"
        if not links_yaml_path.exists():
            logger.error(f"[ERROR] No links.yaml found in {self.directory}")
            return LinkExitCode.SYSTEM_ERROR.value

        self._log(f"Using links.yaml from: {links_yaml_path}")
        links_yaml = self._load_links_yaml(self.directory)
        if not links_yaml:
            return LinkExitCode.SYSTEM_ERROR.value

        # Always perform validation checks
        self._perform_all_checks(links_yaml)

        # Choose output format
        if self.verbose:
            self._print_verbose_report()
        else:
            self._print_summary_report(links_yaml)
            self._print_error_details()  # Always show specific errors on failure
        
        return self.exit_code.value

    def _check_allowed_target(self, target_link: str, source_dir: Path, rules: List[Dict]) -> bool:
        """Check if a single link is allowed by the rules."""
        try:
            normalized_link = target_link.replace('\\', '/')
            target_abs = (source_dir / normalized_link).resolve()
        except Exception:
            return False

        for rule in rules:
            rule_dir = (source_dir / rule['directory']).resolve()
            if target_abs.parent == rule_dir:
                if re.fullmatch(rule['filename_regex'], target_abs.name):
                    return True
        return False

    def _check_bidirectional(self, target_link: str, source_file: str, source_dir: Path) -> Tuple[str, str]:
        """Check for a reverse link."""
        normalized_link = target_link.replace('\\', '/')
        target_path = (source_dir / normalized_link).resolve()
        
        target_links_yaml = self._load_links_yaml(target_path.parent)
        if not target_links_yaml or 'established_links' not in target_links_yaml:
            return "INFO", "Target directory has no links.yaml or established_links"

        source_path = (source_dir / source_file).resolve()
        relative_back_path = Path(os.path.relpath(source_path, target_path.parent)).as_posix()
        
        established_in_target = [Path(p.replace('\\', '/')).as_posix() for p in target_links_yaml['established_links'].get(target_path.name, [])]
        
        if relative_back_path in established_in_target:
            return "PASS", "Bidirectional link confirmed"
        else:
            self.summary["unidirectional"] += 1
            return "FAIL", f"No reverse link found in {target_path.parent / 'links.yaml'}"


# --- Command Handler Functions ---

def create_file(args):
    """Create a new Markdown file."""
    filepath = Path(args.filename)
    if filepath.exists():
        logger.error(f"[FATAL] File already exists: {filepath}")
        return 2
    try:
        template = f"""# {filepath.stem.replace('_', ' ').title()}

## Description

This is a new Markdown document.

## Content

Add your content here.
"""
        filepath.write_text(template, encoding='utf-8')
        logger.info(f"[INFO] Created file: {filepath}")
        return 0
    except Exception as e:
        logger.error(f"[FATAL] Failed to create file: {e}")
        return 2


def read_file(args):
    """Read and display file contents."""
    filepath = Path(args.filename)
    if not filepath.exists():
        logger.error(f"[FATAL] File not found: {filepath}")
        return 2
    try:
        content = filepath.read_text(encoding='utf-8')
        print(content)
        return 0
    except Exception as e:
        logger.error(f"[FATAL] Failed to read file: {e}")
        return 2


def update_file(args):
    """Update a section in a Markdown file (placeholder implementation)."""
    filepath = Path(args.filename)
    if not filepath.exists():
        logger.error(f"[FATAL] File not found: {filepath}")
        return 2
    logger.info(f"[INFO] Update command logged for {filepath}")
    logger.info(f"[INFO] Section: {args.section_name}")
    logger.info(f"[INFO] Content: {args.content[:50]}..." if len(args.content) > 50 else f"[INFO] Content: {args.content}")
    return 0


def delete_file(args):
    """Delete a Markdown file."""
    filepath = Path(args.filename)
    if not filepath.exists():
        logger.error(f"[FATAL] File not found: {filepath}")
        return 2
    try:
        filepath.unlink()
        logger.info(f"[INFO] Deleted file: {filepath}")
        return 0
    except Exception as e:
        logger.error(f"[FATAL] Failed to delete file: {e}")
        return 2


def verify_doc(args):
    """Handler for the verify-doc command."""
    target_directory = Path(args.directory)
    if not target_directory.is_dir():
        logger.error(f"[FATAL] Invalid directory: {target_directory}")
        return 2
    validator = MarkdownValidator(verbose=args.verbose, quiet=args.quiet)
    return validator.verify_project(target_directory)

def verify_link(args):
    """Handler for the verify-link command."""
    validator = LinkValidator(args)
    return validator.run()


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='md_validator',
        description='Markdown Validator CLI - A tool for Markdown document validation and management'
    )
    parser.add_argument('--verbose', action='store_true', help='Enable detailed output for debugging')
    parser.add_argument('--quiet', action='store_true', help='Suppress non-error messages')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    create_parser = subparsers.add_parser('create', help='Create a new Markdown file')
    create_parser.add_argument('filename', help='Name of the file to create')
    create_parser.set_defaults(func=create_file)

    read_parser = subparsers.add_parser('read', help='Print the content of a file')
    read_parser.add_argument('filename', help='Name of the file to read')
    read_parser.set_defaults(func=read_file)

    update_parser = subparsers.add_parser('update', help='Update a section in a file (placeholder)')
    update_parser.add_argument('filename', help='Name of the file to update')
    update_parser.add_argument('section_name', help='Name of the section to update')
    update_parser.add_argument('content', help='New content for the section')
    update_parser.set_defaults(func=update_file)

    delete_parser = subparsers.add_parser('delete', help='Delete a file')
    delete_parser.add_argument('filename', help='Name of the file to delete')
    delete_parser.set_defaults(func=delete_file)

    verify_doc_parser = subparsers.add_parser('verify-doc', help='Validate all Markdown documents in the project for structure')
    verify_doc_parser.add_argument('directory', nargs='?', default='.', help='The directory to validate (defaults to current directory)')
    verify_doc_parser.set_defaults(func=verify_doc)

    verify_link_parser = subparsers.add_parser('verify-link', help='Validate established links in the links.yaml file')
    verify_link_parser.add_argument('directory', nargs='?', default='.', help='The directory containing the links.yaml to validate')
    verify_link_parser.set_defaults(func=verify_link)

    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        args.verbose = getattr(args, 'verbose', False)
        args.quiet = getattr(args, 'quiet', False)
        
        exit_code = args.func(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()
