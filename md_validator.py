# -*- coding: utf-8 -*-
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
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
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


class ErrorLevel(Enum):
    """Error severity levels for validation."""
    FATAL = "FATAL"
    WARN = "WARN"
    INFO = "INFO"


@dataclass
class ValidationResult:
    """Stores validation results for a single file."""
    filename: str
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

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

    def load_spec(self, spec_path: Path) -> bool:
        """Load and validate spec.yaml file."""
        try:
            if not spec_path.exists():
                if self.verbose:
                    self.log(ErrorLevel.INFO, f"No spec.yaml found at {spec_path}")
                return False

            with open(spec_path, 'r', encoding='utf-8') as f:
                self.spec = yaml.safe_load(f)

            if not self.spec or 'structure' not in self.spec:
                self.log(ErrorLevel.WARN, "spec.yaml missing 'structure' key")
                return False

            for block in self.spec['structure']:
                block.setdefault('min_occurrences', 1)
                block.setdefault('max_occurrences', None)
                block.setdefault('error_level', 'FATAL')

                if 'sequence' not in block:
                    self.log(ErrorLevel.WARN, "Block missing 'sequence' key in spec.yaml")
                    return False

            return True

        except yaml.YAMLError as e:
            self.log(ErrorLevel.FATAL, f"Failed to parse spec.yaml: {e}")
            return False
        except Exception as e:
            self.log(ErrorLevel.FATAL, f"Error loading spec.yaml: {e}")
            return False

    def load_links_spec(self, links_path: Path) -> bool:
        """Load and validate links.yaml file."""
        try:
            if not links_path.exists():
                if self.verbose:
                    self.log(ErrorLevel.INFO, f"No links.yaml found at {links_path}")
                self.links_spec = None
                return False

            with open(links_path, 'r', encoding='utf-8') as f:
                self.links_spec = yaml.safe_load(f)

            if self.links_spec is None:
                self.links_spec = {}
            
            return True

        except yaml.YAMLError as e:
            self.log(ErrorLevel.FATAL, f"Failed to parse links.yaml: {e}")
            return False
        except Exception as e:
            self.log(ErrorLevel.FATAL, f"Error loading links.yaml: {e}")
            return False

    def find_markdown_files(self, directory: Path) -> List[Path]:
        """Recursively find all Markdown files, excluding hidden directories."""
        md_files = []

        for path in directory.rglob('*.md'):
            if any(part.startswith('.') for part in path.parts):
                continue
            md_files.append(path)

        return sorted(md_files)

    def _describe_step(self, step: Dict[str, Any]) -> str:
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
                content_to_check = token.content.strip()

            pattern = re.compile(step['content_regex'])
            if not pattern.search(content_to_check):
                return False, 0, f"line {line_num}: Content '{content_to_check}' does not match the expected pattern: {step['content_regex']}"

        return True, 1, ""

    def validate_block(self, tokens: List[Token], token_index: int,
                      block: Dict[str, Any]) -> Tuple[int, Optional[str]]:
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

    def validate_structure(self, filepath: Path, content: str, result: ValidationResult) -> bool:
        if not self.spec:
            return True

        tokens = self.md_parser.parse(content)
        token_index = 0

        for block_idx, block in enumerate(self.spec['structure']):
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
                            return False
                        else:
                            result.warnings.append(message)
                            self.log(ErrorLevel.WARN, message)
                    break

            if matches < min_occur:
                block_description = self._describe_step(block['sequence'][0])
                message = f"{filepath.name}: Expected the block starting with '{block_description}' to appear at least {min_occur} time(s), but it appeared {matches} time(s)."

                if error_level == ErrorLevel.FATAL and message not in result.errors:
                    result.errors.append(message)
                    self.log(ErrorLevel.FATAL, message)
                    return False
                elif error_level == ErrorLevel.WARN and message not in result.warnings:
                    result.warnings.append(message)
                    self.log(ErrorLevel.WARN, message)
        return True

    def extract_links(self, content: str) -> List[str]:
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(link_pattern, content)
        relative_links = []
        for _, url in matches:
            if not url.startswith(('http://', 'https://', 'mailto:', '#')):
                relative_links.append(url)
        return relative_links

    def validate_links(self, filepath: Path, content: str, result: ValidationResult) -> bool:
        if not self.links_spec:
            return True

        physical_links = self.extract_links(content)
        
        established_links = []
        if 'established_links' in self.links_spec:
            established_links = self.links_spec['established_links'].get(filepath.name, [])
        
        all_links = physical_links + established_links

        if 'allowed_targets' in self.links_spec:
            for link in all_links:
                link_path = filepath.parent / link
                link_valid = False
                for target in self.links_spec['allowed_targets']:
                    target_dir = filepath.parent / target['directory']
                    filename_pattern = re.compile(target['filename_regex'])
                    try:
                        if link_path.resolve().parent == target_dir.resolve() and filename_pattern.match(link_path.name):
                            link_valid = True
                            break
                    except:
                        pass
                if not link_valid:
                    message = f"{filepath.name}: Invalid link target '{link}'"
                    result.warnings.append(message)
                    self.log(ErrorLevel.WARN, message)

        if 'required_links' in self.links_spec:
            required_spec = self.links_spec['required_links']
            required_for_this_file = required_spec.get(str(filepath), required_spec.get(filepath.name))

            if required_for_this_file:
                for req_link in required_for_this_file:
                    if req_link not in all_links:
                        message = f"{filepath.name}: Missing required link to '{req_link}'"
                        result.warnings.append(message)
                        self.log(ErrorLevel.WARN, message)
        return True

    def validate_file(self, filepath: Path) -> ValidationResult:
        result = ValidationResult(filename=str(filepath))
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.load_links_spec(filepath.parent / 'links.yaml')
            if not self.validate_structure(filepath, content, result):
                return result
            self.validate_links(filepath, content, result)
        except Exception as e:
            result.errors.append(f"Failed to process file: {e}")
            self.log(ErrorLevel.FATAL, f"{filepath.name}: {e}")
        return result

    def verify_project(self, directory: Path, dry_run: bool = False) -> int:
        self.load_spec(directory / 'spec.yaml')
        
        md_files = self.find_markdown_files(directory)
        if not md_files:
            self.log(ErrorLevel.INFO, "No Markdown files found")
            return 0

        total_errors, total_warnings = 0, 0
        files_with_errors, files_with_warnings = 0, 0

        for filepath in md_files:
            if self.verbose:
                self.log(ErrorLevel.INFO, f"Validating {filepath}...")
            result = self.validate_file(filepath)
            status = "[PASS]"
            if result.has_errors:
                status = "[FAIL]"
                files_with_errors += 1
                total_errors += len(result.errors)
            if result.has_warnings:
                status = "[WARN]" if not result.has_errors else status
                files_with_warnings += 1
                total_warnings += len(result.warnings)
            self.log(ErrorLevel.INFO, f"{status} {filepath.name}: {len(result.errors)} errors, {len(result.warnings)} warnings")

        self.log(ErrorLevel.INFO,
                f"\nSummary: {len(md_files)} files validated, "
                f"{files_with_errors} with fatal errors, "
                f"{files_with_warnings} with warnings")

        if total_errors > 0: return 2
        elif total_warnings > 0: return 1
        return 0


def create_file(args):
    filepath = Path(args.filename)
    if filepath.exists():
        logger.error(f"[FATAL] File already exists: {filepath}")
        return 2
    try:
        template = f"""# {filepath.stem.replace('_', ' ').title()}\n\n## Description\n\nThis is a new Markdown document.\n\n## Content\n\nAdd your content here.\n"""
        filepath.write_text(template, encoding='utf-8')
        logger.info(f"[INFO] Created file: {filepath}")
        return 0
    except Exception as e:
        logger.error(f"[FATAL] Failed to create file: {e}")
        return 2

def read_file(args):
    filepath = Path(args.filename)
    if not filepath.exists():
        logger.error(f"[FATAL] File not found: {filepath}")
        return 2
    try:
        print(filepath.read_text(encoding='utf-8'))
        return 0
    except Exception as e:
        logger.error(f"[FATAL] Failed to read file: {e}")
        return 2

def update_file(args):
    filepath = Path(args.filename)
    if not filepath.exists():
        logger.error(f"[FATAL] File not found: {filepath}")
        return 2
    logger.info(f"[INFO] Update command logged for {filepath}, Section: {args.section_name}")
    return 0

def delete_file(args):
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

def link_files(args):
    source_path = Path(args.source)
    target_path = Path(args.target)
    if not source_path.is_file():
        logger.error(f"[FATAL] Source file not found: {source_path}")
        return 2
    if not target_path.exists():
        logger.error(f"[FATAL] Target path does not exist: {target_path}")
        return 2

    links_spec_path = source_path.parent / 'links.yaml'
    validator = MarkdownValidator()
    validator.load_links_spec(links_spec_path)

    if not validator.links_spec or 'allowed_targets' not in validator.links_spec:
        logger.error(f"[FATAL] {links_spec_path} is missing 'allowed_targets' section or does not exist.")
        return 2

    link_is_valid = False
    for rule in validator.links_spec['allowed_targets']:
        try:
            target_dir_rule = (source_path.parent / rule['directory']).resolve()
            filename_pattern = re.compile(rule['filename_regex'])
            if target_path.resolve().parent == target_dir_rule and filename_pattern.match(target_path.name):
                link_is_valid = True
                break
        except Exception:
            continue
    if not link_is_valid:
        logger.error(f"[FATAL] Link from '{source_path.name}' to '{target_path.name}' is not allowed by the rules in {links_spec_path}.")
        return 2

    try:
        data = validator.links_spec
        relative_path = os.path.relpath(target_path, start=source_path.parent)

        if 'established_links' not in data:
            data['established_links'] = {}
        
        if source_path.name not in data['established_links']:
            data['established_links'][source_path.name] = []
        
        if relative_path not in data['established_links'][source_path.name]:
            data['established_links'][source_path.name].append(relative_path)
            
            with open(links_spec_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, sort_keys=False, default_flow_style=False, indent=2)

            logger.info(f"[INFO] Link from '{source_path.name}' to '{target_path.name}' recorded in {links_spec_path.name}")
        else:
            logger.info(f"[INFO] Link already exists.")
        
        return 0

    except Exception as e:
        logger.error(f"[FATAL] Failed to record link: {e}")
        return 2

def display_links(args):
    validator = MarkdownValidator()
    cwd = Path.cwd()
    
    logger.info("Scanning project for links...")
    link_map = {}

    for spec_file in cwd.rglob('links.yaml'):
        if validator.load_links_spec(spec_file) and 'established_links' in validator.links_spec:
            for source_name, targets in validator.links_spec['established_links'].items():
                source_file = spec_file.parent / source_name
                if source_file not in link_map:
                    link_map[source_file] = []
                for target_link in targets:
                    target_file = (source_file.parent / target_link).resolve()
                    link_map[source_file].append({'target': target_file, 'type': 'Established'})

    md_files = validator.find_markdown_files(cwd)
    for source_file in md_files:
        try:
            content = source_file.read_text(encoding='utf-8')
            relative_links = validator.extract_links(content)
            if relative_links:
                if source_file not in link_map:
                    link_map[source_file] = []
                for link in relative_links:
                    target_file = (source_file.parent / link).resolve()
                    link_map[source_file].append({'target': target_file, 'type': 'Physical'})
        except Exception as e:
            logger.error(f"Could not process {source_file}: {e}")

    links_found = sum(len(links) for links in link_map.values())
    
    if links_found == 0:
        logger.info("\nNo relative links found in any files.")
        return 0

    for source_file, links in sorted(link_map.items()):
        print(f"\nFILE: {source_file.relative_to(cwd)}")
        for link_info in links:
            target_file = link_info['target']
            link_type = link_info['type']
            status_indicator = "[OK]" if target_file.exists() else "[BROKEN]"
            
            try:
                display_path = target_file.relative_to(cwd)
            except ValueError:
                display_path = target_file

            print(f"  --> {status_indicator} {display_path}  ({link_type})")
            
    return 0

def verify_project(args):
    validator = MarkdownValidator(verbose=args.verbose, quiet=args.quiet)
    return validator.verify_project(Path.cwd(), dry_run=args.dry_run)


def main():
    parser = argparse.ArgumentParser(prog='md_validator', description='Markdown Validator CLI - A tool for Markdown document validation and management')
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
    
    link_parser = subparsers.add_parser('link', help="Record a link in the source directory's links.yaml")
    link_parser.add_argument('source', help='The source Markdown file')
    link_parser.add_argument('target', help='The target file or directory to link to')
    link_parser.set_defaults(func=link_files)

    verify_parser = subparsers.add_parser('verify', help='Validate all Markdown files in the project')
    verify_parser.set_defaults(func=verify_project)
    
    display_parser = subparsers.add_parser('display-links', help='Display a map of all physical and established links')
    display_parser.set_defaults(func=display_links)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        sys.exit(args.func(args))
    else:
        parser.print_help()
        sys.exit(0)

if __name__ == '__main__':
    main()
