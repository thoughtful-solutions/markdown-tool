# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Markdown Validator CLI Tool
A Python CLI tool for Markdown document validation and management.
Supports hyperlink validation via links.yaml.
"""

import argparse
import sys
import re
import yaml
import os
import textwrap
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from markdown_it import MarkdownIt
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

    def find_markdown_files(self, directory: Path, recursive: bool = True) -> List[Path]:
        """Find all Markdown files in a directory."""
        pattern = '*.md'
        search = directory.rglob(pattern) if recursive else directory.glob(pattern)
        
        md_files = []
        for path in search:
            if any(part.startswith('.') for part in path.parts):
                continue
            md_files.append(path)

        return sorted(md_files)

    def extract_links(self, content: str) -> List[str]:
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(link_pattern, content)
        relative_links = []
        for _, url in matches:
            if not url.startswith(('http://', 'https://', 'mailto:', '#')):
                relative_links.append(url)
        return relative_links

    def validate_links(self, filepath: Path, content: str, result: ValidationResult) -> bool:
        physical_links = self.extract_links(content)
        established_links = []
        if self.links_spec and 'established_links' in self.links_spec:
            established_links = self.links_spec.get('established_links', {}).get(filepath.name, [])
        
        all_links = list(set(physical_links + established_links))
        if not all_links and not (self.links_spec and 'required_links' in self.links_spec):
            return True

        for link in all_links:
            normalized_link = os.path.normpath(link)
            link_path = filepath.parent / normalized_link
            if not link_path.exists():
                message = f"Broken link to '{link}' (target does not exist)"
                if message not in result.warnings:
                    result.warnings.append(message)
                    self.log(ErrorLevel.WARN, f"{filepath.name}: {message}")
        
        if self.links_spec and 'allowed_targets' in self.links_spec:
            for link in all_links:
                normalized_link = os.path.normpath(link)
                link_path = filepath.parent / normalized_link
                link_valid = False
                for target in self.links_spec['allowed_targets']:
                    try:
                        target_dir = (filepath.parent / target['directory']).resolve()
                        filename_pattern = re.compile(target['filename_regex'])
                        if link_path.resolve().parent == target_dir and filename_pattern.match(link_path.name):
                            link_valid = True
                            break
                    except Exception:
                        continue
                if not link_valid:
                    message = f"Link to '{link}' is not permitted by allowed_targets rule"
                    if message not in result.warnings:
                        result.warnings.append(message)
                        self.log(ErrorLevel.WARN, f"{filepath.name}: {message}")

        if self.links_spec and 'required_links' in self.links_spec:
            required_spec = self.links_spec['required_links']
            required_for_this_file = required_spec.get(str(filepath), required_spec.get(filepath.name))
            if required_for_this_file:
                for req_link in required_for_this_file:
                    if req_link not in all_links:
                        message = f"Missing required link to '{req_link}'"
                        if message not in result.warnings:
                            result.warnings.append(message)
                            self.log(ErrorLevel.WARN, f"{filepath.name}: {message}")
        return True

    def validate_file(self, filepath: Path) -> ValidationResult:
        result = ValidationResult(filename=str(filepath))
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # --- MODIFIED: Warning for missing links.yaml is now handled in verify_project ---
            self.load_links_spec(filepath.parent / 'links.yaml')
            self.validate_links(filepath, content, result)
        except Exception as e:
            result.errors.append(f"Failed to process file: {e}")
            self.log(ErrorLevel.FATAL, f"{filepath.name}: {e}")
        return result

    def verify_bidirectional_links(self, directory: Path) -> List[str]:
        """Checks for reverse links for all outgoing links in the given directory's links.yaml."""
        warnings = []
        local_spec_path = directory / 'links.yaml'

        if not self.load_links_spec(local_spec_path) or 'established_links' not in self.links_spec:
            return []

        for source_name, targets in self.links_spec['established_links'].items():
            try:
                source_abs = (directory / source_name).resolve(strict=True)
                for target_link in targets:
                    try:
                        target_abs = (directory / os.path.normpath(target_link)).resolve(strict=True)
                        target_spec_path = target_abs.parent / 'links.yaml'
                        
                        target_validator = MarkdownValidator()
                        if not target_validator.load_links_spec(target_spec_path):
                            warnings.append(f"Link {source_name} -> {target_link}: Cannot verify reverse link, {target_spec_path.relative_to(directory.parent)} is missing.")
                            continue

                        reverse_link_path = os.path.relpath(source_abs, start=target_abs.parent).replace(os.path.sep, '/')
                        
                        target_links = target_validator.links_spec.get('established_links', {}).get(target_abs.name, [])
                        
                        is_reversed = any(os.path.normpath(link).replace(os.path.sep, '/') == reverse_link_path for link in target_links)
                        
                        if not is_reversed:
                            warnings.append(f"Unidirectional link found: {source_name} -> {target_link}")

                    except FileNotFoundError:
                        pass
            except FileNotFoundError:
                pass
        return warnings

    def verify_project(self, directory: Path, args: argparse.Namespace) -> int:
        resolved_directory = directory.resolve()
        
        md_files = self.find_markdown_files(resolved_directory, recursive=False)
        
        total_errors, total_warnings = 0, 0
        files_with_errors, files_with_warnings = 0, 0

        # --- MODIFIED: Check for links.yaml once per directory ---
        if md_files and not (resolved_directory / 'links.yaml').exists():
            self.log(ErrorLevel.WARN, f"Directory '{resolved_directory.name}' contains Markdown files but is missing links.yaml.")
            total_warnings += 1

        if md_files:
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
                
                if self.quiet and status == "[PASS]" and not result.has_warnings:
                    continue
                
                self.log(ErrorLevel.INFO, f"{status} {filepath.relative_to(resolved_directory.parent)}: {len(result.errors)} errors, {len(result.warnings)} warnings")
        else:
            self.log(ErrorLevel.INFO, f"No Markdown files found in {resolved_directory}")

        if self.verbose:
            self.log(ErrorLevel.INFO, "\nChecking for bidirectional link integrity in current directory...")
        
        bidir_warnings = self.verify_bidirectional_links(resolved_directory)
        if bidir_warnings:
            self.log(ErrorLevel.WARN, "\nBidirectional Link Warnings:")
            for warning in sorted(bidir_warnings):
                self.log(ErrorLevel.WARN, f" - {warning}")
            total_warnings += len(bidir_warnings)

        summary_msg = f"\nSummary: {len(md_files)} files validated in this directory. {files_with_errors} with fatal errors, {total_warnings} total warnings."
        self.log(ErrorLevel.INFO, summary_msg)

        if total_errors > 0: return 2
        elif total_warnings > 0: return 1
        return 0


def create_file(args):
    filepath = Path(args.filename)
    if filepath.exists():
        logger.error(f"[FATAL] File already exists: {filepath}")
        return 2
    try:
        template = f"""# {filepath.stem.replace('_', ' ').title()}\n\n## Description\n\nThis is a new Markdown document.\n"""
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
        relative_path = os.path.relpath(target_path, start=source_path.parent).replace(os.path.sep, '/')

        data.setdefault('established_links', {}).setdefault(source_path.name, [])
        
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

def unlink_files(args):
    """Removes an established link from the source directory's links.yaml."""
    source_path_arg = Path(args.source)
    if not source_path_arg.is_file():
        logger.error(f"[FATAL] Source file not found: {source_path_arg}")
        return 2
    
    source_path_abs = source_path_arg.resolve()
    target_path_abs = (Path.cwd() / args.target).resolve(strict=False)
    
    links_spec_path = source_path_abs.parent / 'links.yaml'
    if not links_spec_path.exists():
        logger.error(f"[FATAL] Cannot remove link: {links_spec_path} does not exist.")
        return 2

    try:
        with open(links_spec_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        source_filename = source_path_abs.name
        if 'established_links' not in data or source_filename not in data['established_links']:
            logger.info(f"[INFO] No established links found for '{source_filename}' to remove.")
            return 0
        
        path_to_find = os.path.normpath(os.path.relpath(target_path_abs, start=source_path_abs.parent)).replace(os.path.sep, '/')
        
        link_to_remove = None
        for link in data['established_links'][source_filename]:
            normalized_existing_link = os.path.normpath(link).replace(os.path.sep, '/')
            if normalized_existing_link == path_to_find:
                link_to_remove = link
                break
        
        if link_to_remove:
            data['established_links'][source_filename].remove(link_to_remove)
            
            if not data['established_links'][source_filename]:
                del data['established_links'][source_filename]
            
            if not data['established_links']:
                del data['established_links']
            
            with open(links_spec_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, sort_keys=False, default_flow_style=False, indent=2)
            
            logger.info(f"[INFO] Link from '{source_filename}' to '{Path(args.target).name}' removed.")
        else:
            logger.info(f"[INFO] Link from '{source_filename}' to '{Path(args.target).name}' not found.")
            
        return 0

    except Exception as e:
        logger.error(f"[FATAL] Failed to remove link: {e}")
        return 2

def update_bidirectional_links(args):
    """Scans all links.yaml files and adds missing reverse links and rules."""
    logger.info("Scanning project to create bidirectional links...")
    validator = MarkdownValidator(quiet=args.quiet)
    project_root = Path(sys.argv[0]).parent.resolve()
    all_specs = {}
    updated_files = set()

    for spec_path in project_root.rglob('links.yaml'):
        with open(spec_path, 'r', encoding='utf-8') as f:
            all_specs[spec_path.resolve()] = yaml.safe_load(f) or {}

    for source_spec_path, source_data in all_specs.items():
        if 'established_links' not in source_data:
            continue
        
        source_dir = source_spec_path.parent
        for source_name, targets in source_data['established_links'].items():
            try:
                source_abs = (source_dir / source_name).resolve(strict=True)
                for target_link in targets:
                    try:
                        target_abs = (source_dir / os.path.normpath(target_link)).resolve(strict=True)
                        target_spec_path = (target_abs.parent / 'links.yaml').resolve()
                        
                        if target_spec_path not in all_specs:
                            validator.log(ErrorLevel.WARN, f"Cannot create reverse link for '{target_abs.relative_to(project_root)}': links.yaml missing.")
                            continue

                        reverse_link_path = os.path.relpath(source_abs, start=target_abs.parent).replace(os.path.sep, '/')
                        
                        target_spec_data = all_specs[target_spec_path]
                        
                        is_allowed = False
                        allowed_targets = target_spec_data.setdefault('allowed_targets', [])
                        
                        for rule in allowed_targets:
                            try:
                                rule_dir = (target_abs.parent / rule['directory']).resolve()
                                if source_abs.parent == rule_dir:
                                    is_allowed = True
                                    break
                            except: continue
                        
                        if not is_allowed:
                            reverse_dir_path = os.path.relpath(source_abs.parent, start=target_abs.parent).replace(os.path.sep, '/')
                            new_rule = {'directory': reverse_dir_path, 'filename_regex': '.*\\.md$'}
                            allowed_targets.append(new_rule)
                            validator.log(ErrorLevel.INFO, f"Added new rule to {target_spec_path.relative_to(project_root)} for directory '{reverse_dir_path}'")
                            updated_files.add(target_spec_path)

                        target_links = target_spec_data.setdefault('established_links', {}).setdefault(target_abs.name, [])
                        
                        if not any(os.path.normpath(link).replace(os.path.sep, '/') == reverse_link_path for link in target_links):
                            target_links.append(reverse_link_path)
                            validator.log(ErrorLevel.INFO, f"Added reverse link to {target_abs.relative_to(project_root)}")
                            updated_files.add(target_spec_path)

                    except FileNotFoundError:
                        validator.log(ErrorLevel.WARN, f"Could not resolve link target '{target_link}' from '{source_name}'. Skipping.")
                        continue
            except FileNotFoundError:
                continue
    
    if updated_files:
        for spec_path in updated_files:
            with open(spec_path, 'w', encoding='utf-8') as f:
                yaml.dump(all_specs[spec_path], f, sort_keys=False, default_flow_style=False, indent=2)
        logger.info(f"\nSuccessfully updated {len(updated_files)} links.yaml file(s).")
    else:
        logger.info("\nAll links are already bidirectional. No files were changed.")
        
    return 0

def display_links(args):
    validator = MarkdownValidator()
    project_root = Path(sys.argv[0]).parent.resolve()
    
    logger.info("Scanning project for links...")
    link_map = {}

    for spec_file in project_root.rglob('links.yaml'):
        if validator.load_links_spec(spec_file) and 'established_links' in validator.links_spec:
            for source_name, targets in validator.links_spec['established_links'].items():
                source_file = spec_file.parent / source_name
                if source_file not in link_map:
                    link_map[source_file] = []
                for target_link in targets:
                    target_file = (source_file.parent / os.path.normpath(target_link)).resolve()
                    link_map[source_file].append({'target': target_file, 'type': 'Established'})

    md_files = validator.find_markdown_files(project_root, recursive=True)
    for source_file in md_files:
        try:
            content = source_file.read_text(encoding='utf-8')
            relative_links = validator.extract_links(content)
            if relative_links:
                if source_file not in link_map:
                    link_map[source_file] = []
                for link in relative_links:
                    target_file = (source_file.parent / os.path.normpath(link)).resolve()
                    link_map[source_file].append({'target': target_file, 'type': 'Physical'})
        except Exception as e:
            logger.error(f"Could not process {source_file}: {e}")

    links_found = sum(len(links) for links in link_map.values())
    
    if links_found == 0:
        logger.info("\nNo relative links found in any files.")
        return 0

    for source_file, links in sorted(link_map.items()):
        print(f"\nFILE: {source_file.relative_to(project_root)}")
        for link_info in links:
            target_file = link_info['target']
            link_type = link_info['type']
            status_indicator = "[OK]" if target_file.exists() else "[BROKEN]"
            
            try:
                display_path = target_file.relative_to(project_root)
            except ValueError:
                display_path = target_file

            print(f"  --> {status_indicator} {display_path}  ({link_type})")
            
    return 0

def verify_project(args):
    """Wrapper function to set up and run the project verification."""
    validator = MarkdownValidator(verbose=args.verbose, quiet=args.quiet)
    return validator.verify_project(Path.cwd(), args)


def main():
    parser = argparse.ArgumentParser(
        prog='md_validator', 
        description='A CLI tool for validating and managing Markdown documentation.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--verbose', action='store_true', help='Enable detailed output for debugging')
    parser.add_argument('--quiet', action='store_true', help='Suppress non-error messages')

    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    create_parser = subparsers.add_parser('create', help='Create a new Markdown file.')
    create_parser.add_argument('filename', help='Path for the file to create.')
    create_parser.set_defaults(func=create_file)

    read_parser = subparsers.add_parser('read', help='Print the content of a file.')
    read_parser.add_argument('filename', help='Name of the file to read.')
    read_parser.set_defaults(func=read_file)

    delete_parser = subparsers.add_parser('delete', help='Delete a specified file.')
    delete_parser.add_argument('filename', help='Name of the file to delete.')
    delete_parser.set_defaults(func=delete_file)
    
    link_parser = subparsers.add_parser(
        'link', 
        help="Record a logical link in a links.yaml file.",
        description="Records a logical link between two files in the source directory's links.yaml.",
        epilog=textwrap.dedent('''
            example:
              python md_validator.py link domains/business-arch.md principles/agility.md
        '''),
        formatter_class=argparse.RawTextHelpFormatter
    )
    link_parser.add_argument('source', help='The source Markdown file')
    link_parser.add_argument('target', help='The target file or directory')
    link_parser.set_defaults(func=link_files)

    unlink_parser = subparsers.add_parser(
        'unlink',
        help="Remove an established link from a links.yaml file.",
        description="Removes an established link from the source directory's links.yaml.",
        epilog=textwrap.dedent('''
            example:
              python md_validator.py unlink domains/business-arch.md principles/agility.md
        '''),
        formatter_class=argparse.RawTextHelpFormatter
    )
    unlink_parser.add_argument('source', help='The source file of the link')
    unlink_parser.add_argument('target', help='The target file of the link to remove')
    unlink_parser.set_defaults(func=unlink_files)

    verify_parser = subparsers.add_parser(
        'verify', 
        help='Validate all Markdown files in the local directory.',
        description='Validates files in the current directory against local and remote link rules.',
        epilog=textwrap.dedent('''
            Checks for:
             - Missing links.yaml in the current directory
             - Broken links originating from this directory
             - Unidirectional links originating from this directory
        '''),
        formatter_class=argparse.RawTextHelpFormatter
    )
    verify_parser.set_defaults(func=verify_project)
    
    display_parser = subparsers.add_parser('display-links', help='Display a map of all links across the project.')
    display_parser.set_defaults(func=display_links)

    update_links_parser = subparsers.add_parser(
        'update-links',
        help='Scans the whole project and creates missing reverse links.',
        description='Scans all established links and creates the corresponding reverse links\nto ensure bidirectionality, automatically adding link rules where needed.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    update_links_parser.set_defaults(func=update_bidirectional_links)


    args = parser.parse_args()
    if hasattr(args, 'func'):
        sys.exit(args.func(args))
    else:
        parser.print_help()
        sys.exit(0)

if __name__ == '__main__':
    main()
