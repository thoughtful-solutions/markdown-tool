#!/usr/bin/env python3
"""
Markdown Validator CLI Tool
A Python CLI tool for Markdown document validation and management.
Supports structure validation via spec.yaml and hyperlink validation via links.yaml.
"""

import argparse
import sys
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

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
            
            # Parse content into tokens once to be reused by validators
            tokens = self.md_parser.parse(content)

            if not self.validate_structure(filepath, tokens, result):
                return result
            
            self.validate_links(filepath, tokens, result)

        except Exception as e:
            result.errors.append(f"Failed to process file: {e}")
            self.log(ErrorLevel.FATAL, f"{filepath.name}: {e}")
        return result

    def verify_project(self, directory: Path, dry_run: bool = False) -> int:
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


def verify_project(args):
    """Run validation on the project."""
    target_directory = Path(args.directory)
    if not target_directory.is_dir():
        logger.error(f"[FATAL] Invalid directory: {target_directory}")
        return 2
    validator = MarkdownValidator(verbose=args.verbose, quiet=args.quiet)
    return validator.verify_project(target_directory, dry_run=args.dry_run)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='md_validator',
        description='Markdown Validator CLI - A tool for Markdown document validation and management'
    )
    parser.add_argument('--verbose', action='store_true', help='Enable detailed output for debugging')
    parser.add_argument('--quiet', action='store_true', help='Suppress non-error messages')
    parser.add_argument('--dry-run', action='store_true', help='Perform validation without making any file changes')

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

    verify_parser = subparsers.add_parser('verify', help='Validate all Markdown files in the project')
    verify_parser.add_argument('directory', nargs='?', default='.', help='The directory to validate (defaults to current directory)')
    verify_parser.set_defaults(func=verify_project)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        exit_code = args.func(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()
