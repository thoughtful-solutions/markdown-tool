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
            
            self.load_links_spec(filepath.parent / 'links.yaml')
            self.validate_links(filepath, content, result)
        except Exception as e:
            result.errors.append(f"Failed to process file: {e}")
            self.log(ErrorLevel.FATAL, f"{filepath.name}: {e}")
        return result

    def verify_bidirectional_links(self, local_directory: Path, project_root: Path) -> List[str]:
        """Performs a targeted scan for unidirectional links related to the given directory."""
        warnings: Set[str] = set()
        
        local_spec_path = local_directory / 'links.yaml'
        local_validator = MarkdownValidator()
        if not local_validator.load_links_spec(local_spec_path):
            return []

        local_links = local_validator.links_spec.get('established_links', {})
        
        for source_name, targets in local_links.items():
            for target_link in targets:
                try:
                    source_abs = (local_directory / source_name).resolve(strict=True)
                    target_abs = (local_directory / os.path.normpath(target_link)).resolve(strict=True)
                    
                    remote_validator = MarkdownValidator()
                    if not remote_validator.load_links_spec(target_abs.parent / 'links.yaml'):
                        continue
                    
                    reverse_path = os.path.relpath(source_abs, start=target_abs.parent).replace(os.path.sep, '/')
                    remote_target_links = remote_validator.links_spec.get('established_links', {}).get(target_abs.name, [])
                    
                    if not any(os.path.normpath(link).replace(os.path.sep, '/') == reverse_path for link in remote_target_links):
                        warnings.add(f"Unidirectional link: {source_abs.relative_to(project_root)} -> {target_abs.relative_to(project_root)}")

                except FileNotFoundError: continue

        remote_dirs_to_check: Set[Path] = set()
        if 'allowed_targets' in local_validator.links_spec:
            for rule in local_validator.links_spec['allowed_targets']:
                try:
                    remote_dir = (local_directory / rule['directory']).resolve(strict=True)
                    remote_dirs_to_check.add(remote_dir)
                except FileNotFoundError: continue
        
        for remote_dir in remote_dirs_to_check:
            remote_validator = MarkdownValidator()
            if not remote_validator.load_links_spec(remote_dir / 'links.yaml'):
                continue
                
            for remote_source_name, remote_targets in remote_validator.links_spec.get('established_links', {}).items():
                for remote_target_link in remote_targets:
                    try:
                        remote_target_abs = (remote_dir / os.path.normpath(remote_target_link)).resolve(strict=True)
                        
                        if remote_target_abs.parent == local_directory:
                            remote_source_abs = (remote_dir / remote_source_name).resolve(strict=True)
                            reverse_path = os.path.relpath(remote_source_abs, start=remote_target_abs.parent).replace(os.path.sep, '/')
                            local_target_links = local_links.get(remote_target_abs.name, [])
                            
                            if not any(os.path.normpath(link).replace(os.path.sep, '/') == reverse_path for link in local_target_links):
                                warnings.add(f"Unidirectional link: {remote_target_abs.relative_to(project_root)} <- {remote_source_abs.relative_to(project_root)}")
                    except FileNotFoundError: continue

        return sorted(list(warnings))

    def verify_project(self, directory: Path, project_root: Path, args: argparse.Namespace) -> int:
        resolved_local_dir = directory.resolve()
        
        md_files = self.find_markdown_files(resolved_local_dir, recursive=False)
        
        total_errors, total_warnings = 0, 0
        files_with_errors, files_with_warnings = 0, 0

        if md_files and not (resolved_local_dir / 'links.yaml').exists():
            self.log(ErrorLevel.WARN, f"Directory '{resolved_local_dir.name}' contains Markdown files but is missing links.yaml.")
            total_warnings += 1

        if md_files:
            for filepath in md_files:
                if self.verbose: self.log(ErrorLevel.INFO, f"Validating {filepath}...")
                result = self.validate_file(filepath)
                status = "[PASS]"
                if result.has_errors:
                    status = "[FAIL]"; files_with_errors += 1; total_errors += len(result.errors)
                if result.has_warnings:
                    status = "[WARN]" if not result.has_errors else status; files_with_warnings += 1; total_warnings += len(result.warnings)
                
                if self.quiet and status == "[PASS]" and not result.has_warnings: continue
                
                self.log(ErrorLevel.INFO, f"{status} {filepath.relative_to(project_root)}: {len(result.errors)} errors, {len(result.warnings)} warnings")
        else:
            self.log(ErrorLevel.INFO, f"No Markdown files found in {resolved_local_dir}")

        if self.verbose: self.log(ErrorLevel.INFO, "\nChecking for bidirectional link integrity...")
        
        bidir_warnings = self.verify_bidirectional_links(resolved_local_dir, project_root)
        if bidir_warnings:
            self.log(ErrorLevel.WARN, "\nBidirectional Link Warnings:")
            for warning in sorted(list(set(bidir_warnings))):
                self.log(ErrorLevel.WARN, f" - {warning}")
            total_warnings += len(bidir_warnings)

        summary_msg = f"\nSummary: {len(md_files)} files validated in this directory. {files_with_errors} with fatal errors, {total_warnings} total warnings."
        self.log(ErrorLevel.INFO, summary_msg)

        if total_errors > 0: return 2
        elif total_warnings > 0: return 1
        return 0


def create_file(args):
    filepath = Path(args.filename)
    if filepath.exists(): logger.error(f"[FATAL] File already exists: {filepath}"); return 2
    try:
        template = f"""# {filepath.stem.replace('_', ' ').title()}\n\n## Description\n\nThis is a new Markdown document.\n"""
        filepath.write_text(template, encoding='utf-8')
        logger.info(f"[INFO] Created file: {filepath}")
        return 0
    except Exception as e: logger.error(f"[FATAL] Failed to create file: {e}"); return 2

def read_file(args):
    filepath = Path(args.filename)
    if not filepath.exists(): logger.error(f"[FATAL] File not found: {filepath}"); return 2
    try:
        print(filepath.read_text(encoding='utf-8'))
        return 0
    except Exception as e: logger.error(f"[FATAL] Failed to read file: {e}"); return 2

def delete_file(args):
    filepath = Path(args.filename)
    if not filepath.exists(): logger.error(f"[FATAL] File not found: {filepath}"); return 2
    try:
        filepath.unlink()
        logger.info(f"[INFO] Deleted file: {filepath}")
        return 0
    except Exception as e: logger.error(f"[FATAL] Failed to delete file: {e}"); return 2

def link_files(args):
    source_path = Path(args.source)
    target_path = Path(args.target)

    if not source_path.is_file(): logger.error(f"[FATAL] Source file not found: {source_path}"); return 2
    if not target_path.exists(): logger.error(f"[FATAL] Target path does not exist: {target_path}"); return 2

    source_spec_path = source_path.resolve().parent / 'links.yaml'
    target_spec_path = target_path.resolve().parent / 'links.yaml'
    
    source_data = {}
    if source_spec_path.exists():
        with open(source_spec_path, 'r', encoding='utf-8') as f:
            source_data = yaml.safe_load(f) or {}
            
    target_data = {}
    if target_spec_path.exists():
        with open(target_spec_path, 'r', encoding='utf-8') as f:
            target_data = yaml.safe_load(f) or {}

    forward_rel_path = os.path.relpath(target_path.resolve(), start=source_path.resolve().parent).replace(os.path.sep, '/')
    
    is_allowed = False
    for rule in source_data.get('allowed_targets', []):
        try:
            if target_path.resolve().parent == (source_path.resolve().parent / rule['directory']).resolve():
                is_allowed = True; break
        except: continue
        
    if not is_allowed:
        if args.force:
            rule_dir = os.path.relpath(target_path.resolve().parent, start=source_path.resolve().parent).replace(os.path.sep, '/')
            new_rule = {'directory': rule_dir, 'filename_regex': '.*\\.md$'}
            source_data.setdefault('allowed_targets', []).append(new_rule)
            logger.info(f"[INFO] Force: Added new rule to {source_spec_path.name} for directory '{rule_dir}'")
        else:
            logger.error(f"[FATAL] Link from '{source_path.name}' to '{target_path.name}' is not allowed by rules in {source_spec_path.name}. Use --force to update rules."); return 2
            
    source_links = source_data.setdefault('established_links', {}).setdefault(source_path.name, [])
    if forward_rel_path not in source_links:
        source_links.append(forward_rel_path)
        
    if args.force:
        reverse_rel_path = os.path.relpath(source_path.resolve(), start=target_path.resolve().parent).replace(os.path.sep, '/')
        
        is_allowed_reverse = False
        for rule in target_data.get('allowed_targets', []):
            try:
                if source_path.resolve().parent == (target_path.resolve().parent / rule['directory']).resolve():
                    is_allowed_reverse = True; break
            except: continue
        
        if not is_allowed_reverse:
            rule_dir = os.path.relpath(source_path.resolve().parent, start=target_path.resolve().parent).replace(os.path.sep, '/')
            new_rule = {'directory': rule_dir, 'filename_regex': '.*\\.md$'}
            target_data.setdefault('allowed_targets', []).append(new_rule)
            logger.info(f"[INFO] Force: Added new rule to {target_spec_path.name} for directory '{rule_dir}'")
            
        target_links = target_data.setdefault('established_links', {}).setdefault(target_path.name, [])
        if reverse_rel_path not in target_links:
            target_links.append(reverse_rel_path)
            
    try:
        with open(source_spec_path, 'w', encoding='utf-8') as f:
            yaml.dump(source_data, f, sort_keys=False, default_flow_style=False, indent=2)
        logger.info(f"[INFO] Updated {source_spec_path.name}")
        
        if args.force:
            with open(target_spec_path, 'w', encoding='utf-8') as f:
                yaml.dump(target_data, f, sort_keys=False, default_flow_style=False, indent=2)
            logger.info(f"[INFO] Updated {target_spec_path.name}")
        
        return 0
    except Exception as e: logger.error(f"[FATAL] Failed to write link file(s): {e}"); return 2

def _remove_link_entry(spec_path: Path, source_name: str, target_rel_path: str) -> bool:
    """Helper to remove a single link entry from a given spec file."""
    if not spec_path.exists():
        return False
        
    with open(spec_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    if 'established_links' not in data or source_name not in data['established_links']:
        return False

    link_to_remove = None
    for link in data['established_links'][source_name]:
        if os.path.normpath(link).replace(os.path.sep, '/') == target_rel_path:
            link_to_remove = link
            break
            
    if link_to_remove:
        data['established_links'][source_name].remove(link_to_remove)
        if not data['established_links'][source_name]: del data['established_links'][source_name]
        if not data['established_links']: del data['established_links']
        
        with open(spec_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False, indent=2)
        return True
        
    return False

def unlink_files(args):
    """Removes an established link, and optionally the reverse link if --force is used."""
    source_path = Path(args.source)
    target_path = Path(args.target)

    if not source_path.is_file():
        logger.error(f"[FATAL] Source file not found: {source_path}")
        return 2

    source_abs = source_path.resolve()
    target_abs = (Path.cwd() / target_path).resolve(strict=False)
    forward_rel_path = os.path.normpath(os.path.relpath(target_abs, start=source_abs.parent)).replace(os.path.sep, '/')
    
    was_removed = _remove_link_entry(source_abs.parent / 'links.yaml', source_abs.name, forward_rel_path)
    if was_removed:
        logger.info(f"[INFO] Link from '{source_path.name}' to '{target_path.name}' removed.")
    else:
        logger.info(f"[INFO] Link from '{source_path.name}' to '{target_path.name}' not found.")

    if args.force:
        if not target_path.exists():
            logger.warning(f"[WARN] Target file {target_path} does not exist. Cannot remove reverse link.")
            return 0
            
        reverse_rel_path = os.path.normpath(os.path.relpath(source_abs, start=target_abs.parent)).replace(os.path.sep, '/')
        was_reverse_removed = _remove_link_entry(target_abs.parent / 'links.yaml', target_abs.name, reverse_rel_path)
        
        if was_reverse_removed:
            logger.info(f"[INFO] Force: Reverse link from '{target_path.name}' to '{source_path.name}' removed.")
    
    return 0

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
        if 'established_links' not in source_data: continue
        source_dir = source_spec_path.parent
        for source_name, targets in source_data['established_links'].items():
            try:
                source_abs = (source_dir / source_name).resolve(strict=True)
                for target_link in targets:
                    try:
                        target_abs = (source_dir / os.path.normpath(target_link)).resolve(strict=True)
                        target_spec_path = (target_abs.parent / 'links.yaml').resolve()
                        if target_spec_path not in all_specs:
                            validator.log(ErrorLevel.WARN, f"Cannot create reverse link for '{target_abs.relative_to(project_root)}': links.yaml missing."); continue
                        
                        reverse_link_path = os.path.relpath(source_abs, start=target_abs.parent).replace(os.path.sep, '/')
                        target_spec_data = all_specs[target_spec_path]
                        is_allowed = False
                        allowed_targets = target_spec_data.setdefault('allowed_targets', [])
                        for rule in allowed_targets:
                            try:
                                if source_abs.parent == (target_abs.parent / rule['directory']).resolve():
                                    is_allowed = True; break
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
                        validator.log(ErrorLevel.WARN, f"Could not resolve link target '{target_link}' from '{source_name}'. Skipping."); continue
            except FileNotFoundError: continue
    
    if updated_files:
        for spec_path in updated_files:
            with open(spec_path, 'w', encoding='utf-8') as f:
                yaml.dump(all_specs[spec_path], f, sort_keys=False, default_flow_style=False, indent=2)
        logger.info(f"\nSuccessfully updated {len(updated_files)} links.yaml file(s).")
    else:
        logger.info("\nAll links are already bidirectional. No files were changed.")
    return 0

def display_links(args):
    # --- MODIFIED: display-links now shows paths relative to CWD ---
    validator = MarkdownValidator()
    local_directory = Path.cwd().resolve()
    
    logger.info(f"Displaying links related to directory: {os.path.relpath(local_directory)}")
    link_map = {}
    
    local_spec_path = local_directory / 'links.yaml'
    local_validator = MarkdownValidator()
    if local_validator.load_links_spec(local_spec_path) and 'established_links' in local_validator.links_spec:
        for source, targets in local_validator.links_spec['established_links'].items():
            source_abs = (local_directory / source).resolve(strict=False)
            if source_abs not in link_map: link_map[source_abs] = []
            for target_link in targets:
                target_abs = (local_directory / os.path.normpath(target_link)).resolve(strict=False)
                link_map[source_abs].append({'target': target_abs, 'type': 'Established'})
    
    for md_file in local_directory.glob('*.md'):
        content = md_file.read_text(encoding='utf-8')
        physical_links = validator.extract_links(content)
        if physical_links:
            source_abs = md_file.resolve()
            if source_abs not in link_map: link_map[source_abs] = []
            for link in physical_links:
                target_abs = (source_abs.parent / os.path.normpath(link)).resolve(strict=False)
                link_map[source_abs].append({'target': target_abs, 'type': 'Physical'})

    remote_dirs_to_check = set()
    if local_validator.links_spec and 'allowed_targets' in local_validator.links_spec:
        for rule in local_validator.links_spec['allowed_targets']:
            try:
                remote_dir = (local_directory / rule['directory']).resolve(strict=True)
                remote_dirs_to_check.add(remote_dir)
            except FileNotFoundError: continue

    for remote_dir in remote_dirs_to_check:
        remote_validator = MarkdownValidator()
        if remote_validator.load_links_spec(remote_dir / 'links.yaml') and 'established_links' in remote_validator.links_spec:
            for source, targets in remote_validator.links_spec['established_links'].items():
                for target_link in targets:
                    try:
                        target_abs = (remote_dir / os.path.normpath(target_link)).resolve(strict=True)
                        if target_abs.parent == local_directory:
                            source_abs = (remote_dir / source).resolve(strict=True)
                            if source_abs not in link_map: link_map[source_abs] = []
                            link_map[source_abs].append({'target': target_abs, 'type': 'Established'})
                    except FileNotFoundError: continue
    
    # Filter and display
    if args.filename:
        query_path = (local_directory / args.filename).resolve()
        
        # Display outgoing
        if query_path in link_map:
            print(f"\n--- Outgoing Links from {Path(args.filename).name} ---")
            for link_info in link_map[query_path]:
                status = "[OK]" if link_info['target'].exists() else "[BROKEN]"
                display_path = os.path.relpath(link_info['target'], start=local_directory)
                print(f"  --> {status} {display_path} ({link_info['type']})")
        
        # Display incoming
        incoming = []
        for source, targets in link_map.items():
            if source == query_path: continue
            for link_info in targets:
                if link_info['target'] == query_path:
                    incoming.append(source)
                    break
        if incoming:
            print(f"\n--- Incoming Links to {Path(args.filename).name} ---")
            for source in sorted(incoming):
                display_path = os.path.relpath(source, start=local_directory)
                print(f"  <-- [OK] {display_path}")

    else: # Display all found links
        for source_file, links in sorted(link_map.items()):
            display_path = os.path.relpath(source_file, start=local_directory)
            print(f"\nFILE: {display_path}")
            for link_info in links:
                status = "[OK]" if link_info['target'].exists() else "[BROKEN]"
                target_display_path = os.path.relpath(link_info['target'], start=local_directory)
                print(f"  --> {status} {target_display_path}  ({link_info['type']})")

    return 0

def verify_project(args):
    """Wrapper function to set up and run the project verification."""
    validator = MarkdownValidator(verbose=args.verbose, quiet=args.quiet)
    project_root = Path(sys.argv[0]).parent.resolve()
    return validator.verify_project(Path.cwd(), project_root, args)


def main():
    parser = argparse.ArgumentParser(prog='md_validator', description='A CLI tool for validating and managing Markdown documentation.', formatter_class=argparse.RawTextHelpFormatter)
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
    
    link_parser = subparsers.add_parser('link', help="Record a logical link in a links.yaml file.", epilog=textwrap.dedent('''
            example:
              python md_validator.py link domains/business-arch.md principles/agility.md
        '''), formatter_class=argparse.RawTextHelpFormatter)
    link_parser.add_argument('source', help='The source Markdown file')
    link_parser.add_argument('target', help='The target file or directory')
    link_parser.add_argument('-f', '--force', action='store_true', help='Force link creation by adding rules and creating back-links.')
    link_parser.set_defaults(func=link_files)

    unlink_parser = subparsers.add_parser('unlink', help="Remove an established link from a links.yaml file.", epilog=textwrap.dedent('''
            example:
              python md_validator.py unlink domains/business-arch.md principles/agility.md
        '''), formatter_class=argparse.RawTextHelpFormatter)
    unlink_parser.add_argument('source', help='The source file of the link')
    unlink_parser.add_argument('target', help='The target file of the link to remove')
    unlink_parser.add_argument('-f', '--force', action='store_true', help='Force unlink by removing the reverse link from the target file.')
    unlink_parser.set_defaults(func=unlink_files)

    verify_parser = subparsers.add_parser('verify', help='Validate all Markdown files in the local directory.', epilog=textwrap.dedent('''
            Checks for:
             - Missing links.yaml in the current directory
             - Broken links originating from this directory
             - Unidirectional links involving this directory
        '''), formatter_class=argparse.RawTextHelpFormatter)
    verify_parser.set_defaults(func=verify_project)
    
    display_parser = subparsers.add_parser('display-links', help='Display a map of links related to the current directory.', epilog=textwrap.dedent('''
        Shows outgoing and incoming links for the current directory.
        If a filename is provided, it filters the results for that specific file.
        '''), formatter_class=argparse.RawTextHelpFormatter)
    display_parser.add_argument('filename', nargs='?', default=None, help='Optional: A specific filename to display links for.')
    display_parser.set_defaults(func=display_links)

    update_links_parser = subparsers.add_parser('update-links', help='Scans the whole project and creates missing reverse links.', epilog=textwrap.dedent('''
        Scans all established links and creates the corresponding reverse links
        to ensure bidirectionality, automatically adding link rules where needed.
        '''), formatter_class=argparse.RawTextHelpFormatter)
    update_links_parser.set_defaults(func=update_bidirectional_links)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        sys.exit(args.func(args))
    else:
        parser.print_help()
        sys.exit(0)

if __name__ == '__main__':
    main()
