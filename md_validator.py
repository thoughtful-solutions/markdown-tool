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
                
            # Set defaults for each block
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
                return False
                
            with open(links_path, 'r', encoding='utf-8') as f:
                self.links_spec = yaml.safe_load(f)
                
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
            # Skip hidden directories
            if any(part.startswith('.') for part in path.parts):
                continue
            md_files.append(path)
            
        return sorted(md_files)
    
    def validate_sequence_step(self, tokens: List[Token], token_index: int, 
                              step: Dict[str, Any]) -> Tuple[bool, int, str]:
        """
        Validate a single sequence step against tokens.
        Returns: (success, tokens_consumed, error_message)
        """
        if token_index >= len(tokens):
            return False, 0, "No more tokens available"
            
        token = tokens[token_index]
        
        # Check token type
        if token.type != step['type']:
            return False, 0, f"Expected {step['type']}, found {token.type}"
        
        # Check level for headings
        if 'level' in step and token.type == 'heading_open':
            expected_tag = f"h{step['level']}"
            if token.tag != expected_tag:
                return False, 0, f"Expected {expected_tag}, found {token.tag}"
        
        # Check info for fenced code blocks
        if 'info' in step and token.type == 'fence':
            if token.info != step['info']:
                return False, 0, f"Expected fence info '{step['info']}', found '{token.info}'"
        
        # Check content regex
        if 'content_regex' in step:
            content_to_check = ""
            
            # For heading_open or paragraph_open, check the inline token
            if token.type in ['heading_open', 'paragraph_open']:
                # Look for the corresponding inline token
                if token_index + 1 < len(tokens) and tokens[token_index + 1].type == 'inline':
                    content_to_check = tokens[token_index + 1].content
            else:
                content_to_check = token.content
            
            pattern = re.compile(step['content_regex'])
            if not pattern.search(content_to_check):
                return False, 0, f"Content doesn't match regex: {step['content_regex']}"
        
        return True, 1, ""
    
    def validate_block(self, tokens: List[Token], token_index: int, 
                      block: Dict[str, Any]) -> Tuple[int, Optional[str]]:
        """
        Validate a block against tokens.
        Returns: (tokens_consumed, error_message)
        """
        sequence = block['sequence']
        current_index = token_index
        
        # --- NEW VERBOSE DEBUGGING START ---
        if self.verbose:
            block_num = self.spec['structure'].index(block) + 1
            self.log(ErrorLevel.INFO, f"--- DEBUG: Starting Block {block_num} ---")
            self.log(ErrorLevel.INFO, f"Initial Token Index: {token_index}, Total Tokens: {len(tokens)}")
        # --- NEW VERBOSE DEBUGGING END ---
        
        for step_idx, step in enumerate(sequence):
            # --- NEW VERBOSE DEBUGGING START ---
            if self.verbose:
                token_type = tokens[current_index].type if current_index < len(tokens) else 'EOF'
                self.log(ErrorLevel.INFO, f"  Step {step_idx + 1}: Expected Type: {step.get('type', 'N/A')}, Found Index {current_index} Token Type: {token_type}")
                if 'content_regex' in step:
                     self.log(ErrorLevel.INFO, f"  Step {step_idx + 1}: Expected Content Regex: {step['content_regex']}")
            # --- NEW VERBOSE DEBUGGING END ---

            success, consumed, error = self.validate_sequence_step(tokens, current_index, step)
            
            if not success:
                # --- NEW VERBOSE DEBUGGING START ---
                if self.verbose:
                    token_info = tokens[current_index].as_dict() if current_index < len(tokens) else 'EOF'
                    self.log(ErrorLevel.INFO, f"  Step {step_idx + 1} FAILED. Error: {error}. Token details: {token_info}")
                # --- NEW VERBOSE DEBUGGING END ---
                return 0, f"step {step_idx + 1}: {error}"
            
            current_index += consumed
            
            # --- NEW VERBOSE DEBUGGING START ---
            if self.verbose:
                self.log(ErrorLevel.INFO, f"  Step {step_idx + 1} MATCHED (Consumed: {consumed}). New Index: {current_index}")
            # --- NEW VERBOSE DEBUGGING END ---

            # Skip related tokens (e.g., inline, close tags)
            if tokens[current_index - 1].type in ['heading_open', 'paragraph_open', 'list_item_open']: # ADDED 'list_item_open'
                # The logic must be smarter to skip the full list item content
                # when Block 5 matches the list_item_open
                
                # Check if the current block started with a list_item_open
                started_with_list_item = any(s['type'] == 'list_item_open' for s in sequence)
                
                if started_with_list_item:
                    # Look for the closing list_item_close token, which signifies the end
                    # of the element we just started consuming.
                    # We are intentionally leaving the parent bullet_list_close for the next block to handle
                    list_item_depth = 1
                    initial_index_for_skip = current_index
                    while current_index < len(tokens):
                        token = tokens[current_index]
                        
                        if token.type == 'list_item_open':
                            list_item_depth += 1
                        elif token.type == 'list_item_close':
                            list_item_depth -= 1
                            if list_item_depth == 0:
                                # Consume the closing token and break
                                current_index += 1
                                # --- NEW VERBOSE DEBUGGING START ---
                                if self.verbose:
                                    self.log(ErrorLevel.INFO, f"  Skipped {current_index - initial_index_for_skip} tokens until list_item_close.")
                                # --- NEW VERBOSE DEBUGGING END ---
                                break
                        
                        current_index += 1
                
                # Default skipping logic for headings/paragraphs
                else:
                    initial_index_for_skip = current_index
                    while current_index < len(tokens):
                        if tokens[current_index].type in ['inline', 'heading_close', 'paragraph_close']:
                            current_index += 1
                        else:
                            # --- NEW VERBOSE DEBUGGING START ---
                            if self.verbose:
                                self.log(ErrorLevel.INFO, f"  Skipped {current_index - initial_index_for_skip} tokens (Inline/Close). Next: {tokens[current_index].type}")
                            # --- NEW VERBOSE DEBUGGING END ---
                            break
                    
        return current_index - token_index, None
    
    def validate_structure(self, filepath: Path, content: str, result: ValidationResult) -> bool:
        """Validate document structure against spec.yaml."""
        if not self.spec:
            return True
            
        tokens = self.md_parser.parse(content)
        token_index = 0
        
        for block_idx, block in enumerate(self.spec['structure']):
            min_occur = block['min_occurrences']
            max_occur = block['max_occurrences']
            error_level = block['error_level']
            
            matches = 0
            
            while token_index < len(tokens):
                consumed, error = self.validate_block(tokens, token_index, block)
                
                if consumed > 0:
                    matches += 1
                    token_index += consumed
                    
                    if max_occur is not None and matches >= max_occur:
                        break
                else:
                    break
            
            # Check occurrence constraints
            if matches < min_occur:
                message = f"{filepath.name} [block {block_idx + 1}]: Expected at least {min_occur} occurrences, found {matches}"
                
                if error_level == 'FATAL':
                    result.errors.append(message)
                    self.log(ErrorLevel.FATAL, message)
                    return False  # Stop processing this file
                else:
                    result.warnings.append(message)
                    self.log(ErrorLevel.WARN, message)
        
        return True
    
    def extract_links(self, content: str) -> List[str]:
        """Extract all relative links from Markdown content."""
        # Match Markdown links: [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(link_pattern, content)
        
        # Filter for relative links
        relative_links = []
        for _, url in matches:
            if not url.startswith(('http://', 'https://', 'mailto:', '#')):
                relative_links.append(url)
        
        return relative_links
    
    def validate_links(self, filepath: Path, content: str, result: ValidationResult) -> bool:
        """Validate hyperlinks against links.yaml."""
        if not self.links_spec:
            return True
            
        links = self.extract_links(content)
        
        # Check allowed_targets
        if 'allowed_targets' in self.links_spec:
            for link in links:
                link_path = filepath.parent / link
                link_valid = False
                
                for target in self.links_spec['allowed_targets']:
                    target_dir = filepath.parent / target['directory']
                    filename_pattern = re.compile(target['filename_regex'])
                    
                    try:
                        if link_path.resolve().parent == target_dir.resolve():
                            if filename_pattern.match(link_path.name):
                                link_valid = True
                                break
                    except:
                        pass  # Invalid path
                
                if not link_valid:
                    message = f"{filepath.name}: Invalid link target '{link}'"
                    result.warnings.append(message)
                    self.log(ErrorLevel.WARN, message)
        
        # Check required_links
        if 'required_links' in self.links_spec:
            if str(filepath) in self.links_spec['required_links']:
                required = self.links_spec['required_links'][str(filepath)]
                for req_link in required:
                    if req_link not in links:
                        message = f"{filepath.name}: Missing required link to '{req_link}'"
                        result.warnings.append(message)
                        self.log(ErrorLevel.WARN, message)
        
        return True
    
    def validate_file(self, filepath: Path) -> ValidationResult:
        """Validate a single Markdown file."""
        result = ValidationResult(filename=str(filepath))
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Validate structure
            if not self.validate_structure(filepath, content, result):
                return result  # Fatal error, stop processing
            
            # Validate links
            self.validate_links(filepath, content, result)
            
        except Exception as e:
            result.errors.append(f"Failed to process file: {e}")
            self.log(ErrorLevel.FATAL, f"{filepath.name}: {e}")
        
        return result
    
    def verify_project(self, directory: Path, dry_run: bool = False) -> int:
        """
        Verify all Markdown files in the project.
        Returns exit code: 0=success, 1=warnings, 2=errors
        """
        # Load specifications
        self.load_spec(directory / 'spec.yaml')
        self.load_links_spec(directory / 'links.yaml')
        
        # Find all Markdown files
        md_files = self.find_markdown_files(directory)
        
        if not md_files:
            self.log(ErrorLevel.INFO, "No Markdown files found")
            return 0
        
        # Validate each file
        total_errors = 0
        total_warnings = 0
        files_with_errors = 0
        files_with_warnings = 0
        
        for filepath in md_files:
            if self.verbose:
                self.log(ErrorLevel.INFO, f"Validating {filepath}...")
            
            result = self.validate_file(filepath)
            
            # Print file summary
            if result.has_errors or result.has_warnings:
                status = "❌" if result.has_errors else "⚠️"
            else:
                status = "✅"
            
            self.log(ErrorLevel.INFO, 
                    f"{status} {filepath.name}: {len(result.errors)} errors, {len(result.warnings)} warnings")
            
            # Update totals
            if result.has_errors:
                files_with_errors += 1
                total_errors += len(result.errors)
            if result.has_warnings:
                files_with_warnings += 1
                total_warnings += len(result.warnings)
        
        # Print summary
        self.log(ErrorLevel.INFO, 
                f"\nSummary: {len(md_files)} files validated, "
                f"{files_with_errors} with fatal errors, "
                f"{files_with_warnings} with warnings")
        
        # Determine exit code
        if total_errors > 0:
            return 2
        elif total_warnings > 0:
            return 1
        return 0


def create_file(args):
    """Create a new Markdown file."""
    filepath = Path(args.filename)
    
    if filepath.exists():
        logger.error(f"[FATAL] File already exists: {filepath}")
        return 2
    
    try:
        # Create with a basic template
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
    
    # Placeholder: In a full implementation, this would parse the file,
    # find the section, and update it
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
    validator = MarkdownValidator(verbose=args.verbose, quiet=args.quiet)
    return validator.verify_project(Path.cwd(), dry_run=args.dry_run)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='md_validator',
        description='Markdown Validator CLI - A tool for Markdown document validation and management'
    )
    
    # Global optional flags
    parser.add_argument('--verbose', action='store_true', 
                       help='Enable detailed output for debugging')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress non-error messages')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform validation without making any file changes')
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new Markdown file')
    create_parser.add_argument('filename', help='Name of the file to create')
    create_parser.set_defaults(func=create_file)
    
    # Read command
    read_parser = subparsers.add_parser('read', help='Print the content of a file')
    read_parser.add_argument('filename', help='Name of the file to read')
    read_parser.set_defaults(func=read_file)
    
    # Update command
    update_parser = subparsers.add_parser('update', 
                                         help='Update a section in a file (placeholder)')
    update_parser.add_argument('filename', help='Name of the file to update')
    update_parser.add_argument('section_name', help='Name of the section to update')
    update_parser.add_argument('content', help='New content for the section')
    update_parser.set_defaults(func=update_file)
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a file')
    delete_parser.add_argument('filename', help='Name of the file to delete')
    delete_parser.set_defaults(func=delete_file)
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', 
                                         help='Validate all Markdown files in the project')
    verify_parser.set_defaults(func=verify_project)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if hasattr(args, 'func'):
        exit_code = args.func(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()