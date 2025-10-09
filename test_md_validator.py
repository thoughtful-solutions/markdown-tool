#!/usr/bin/env python3
"""
Test suite for Markdown Validator CLI Tool
Run with: pytest test_suite.py -v
or: python test_suite.py
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
import sys
import os

# Add parent directory to path and try different module names
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to import with different possible names
try:
    from md_validator import (
        MarkdownValidator, ValidationResult, ErrorLevel,
        create_file, read_file, delete_file, verify_project
    )
except ImportError:
    try:
        # Try with hyphen version if saved as md-validator.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("md_validator", "md-validator.py")
        if spec and spec.loader:
            md_validator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(md_validator)
            
            MarkdownValidator = md_validator.MarkdownValidator
            ValidationResult = md_validator.ValidationResult
            ErrorLevel = md_validator.ErrorLevel
            create_file = md_validator.create_file
            read_file = md_validator.read_file
            delete_file = md_validator.delete_file
            verify_project = md_validator.verify_project
        else:
            raise ImportError("Could not load md-validator.py")
    except:
        print("ERROR: Could not find md_validator.py or md-validator.py")
        print("Please ensure the main validator script is in the same directory")
        print("and named either 'md_validator.py' or 'md-validator.py'")
        sys.exit(1)


class TestValidationResult:
    """Test the ValidationResult dataclass."""
    
    def test_initialisation(self):
        """Test ValidationResult initialisation."""
        result = ValidationResult(filename="test.md")
        assert result.filename == "test.md"
        assert result.errors == []
        assert result.warnings == []
        assert not result.has_errors
        assert not result.has_warnings
    
    def test_error_tracking(self):
        """Test error and warning tracking."""
        result = ValidationResult(filename="test.md")
        result.errors.append("Error 1")
        result.warnings.append("Warning 1")
        
        assert result.has_errors
        assert result.has_warnings
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestMarkdownValidator:
    """Test the MarkdownValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir)
        self.validator = MarkdownValidator()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_load_valid_spec(self):
        """Test loading a valid spec.yaml file."""
        spec_content = """
structure:
  - min_occurrences: 1
    max_occurrences: 1
    error_level: FATAL
    sequence:
      - type: heading_open
        level: 1
"""
        spec_path = self.test_path / "spec.yaml"
        spec_path.write_text(spec_content)
        
        assert self.validator.load_spec(spec_path)
        assert self.validator.spec is not None
        assert len(self.validator.spec['structure']) == 1
    
    def test_load_invalid_spec(self):
        """Test handling of invalid spec.yaml."""
        spec_path = self.test_path / "spec.yaml"
        spec_path.write_text("invalid: yaml: content:")
        
        assert not self.validator.load_spec(spec_path)
    
    def test_find_markdown_files(self):
        """Test finding Markdown files recursively."""
        # Create test files
        (self.test_path / "test1.md").touch()
        (self.test_path / "test2.md").touch()
        (self.test_path / "docs").mkdir()
        (self.test_path / "docs" / "test3.md").touch()
        (self.test_path / ".hidden").mkdir()
        (self.test_path / ".hidden" / "test4.md").touch()  # Should be skipped
        
        files = self.validator.find_markdown_files(self.test_path)
        
        assert len(files) == 3  # Hidden directory should be excluded
        assert any("test1.md" in str(f) for f in files)
        assert any("test2.md" in str(f) for f in files)
        assert any("test3.md" in str(f) for f in files)
        assert not any("test4.md" in str(f) for f in files)
    
    def test_validate_simple_structure(self):
        """Test validation of a simple Markdown structure."""
        # Set up spec
        self.validator.spec = {
            'structure': [
                {
                    'min_occurrences': 1,
                    'max_occurrences': 1,
                    'error_level': 'FATAL',
                    'sequence': [
                        {'type': 'heading_open', 'level': 1}
                    ]
                }
            ]
        }
        
        # Valid content
        valid_content = "# Test Heading\n\nSome content"
        test_file = self.test_path / "valid.md"
        test_file.write_text(valid_content)
        
        result = ValidationResult(filename="valid.md")
        success = self.validator.validate_structure(test_file, valid_content, result)
        
        assert success
        assert not result.has_errors
        
        # Invalid content
        invalid_content = "## Wrong Level Heading\n\nSome content"
        test_file2 = self.test_path / "invalid.md"
        test_file2.write_text(invalid_content)
        
        result2 = ValidationResult(filename="invalid.md")
        success2 = self.validator.validate_structure(test_file2, invalid_content, result2)
        
        assert not success2
        assert result2.has_errors
    
    def test_extract_links(self):
        """Test extraction of links from Markdown content."""
        content = """
# Document

[External link](https://example.com)
[Relative link](docs/guide.md)
[Another relative](../common/shared.md)
[Anchor link](#section)
[Email](mailto:test@example.com)
"""
        links = self.validator.extract_links(content)
        
        assert len(links) == 2  # Only relative links
        assert "docs/guide.md" in links
        assert "../common/shared.md" in links
        assert "https://example.com" not in links
        assert "#section" not in links
        assert "mailto:test@example.com" not in links
    
    def test_content_regex_validation(self):
        """Test content regex matching in validation."""
        self.validator.spec = {
            'structure': [
                {
                    'min_occurrences': 1,
                    'max_occurrences': 1,
                    'error_level': 'FATAL',
                    'sequence': [
                        {
                            'type': 'heading_open',
                            'level': 1,
                            'content_regex': r'Project.*'
                        }
                    ]
                }
            ]
        }
        
        # Valid content matching regex
        valid_content = "# Project Documentation\n\nContent here"
        test_file = self.test_path / "regex_valid.md"
        test_file.write_text(valid_content)
        
        result = ValidationResult(filename="regex_valid.md")
        success = self.validator.validate_structure(test_file, valid_content, result)
        
        assert success
        assert not result.has_errors
        
        # Invalid content not matching regex
        invalid_content = "# Other Title\n\nContent here"
        test_file2 = self.test_path / "regex_invalid.md"
        test_file2.write_text(invalid_content)
        
        result2 = ValidationResult(filename="regex_invalid.md")
        success2 = self.validator.validate_structure(test_file2, invalid_content, result2)
        
        assert not success2
        assert result2.has_errors


class TestCLIFunctions:
    """Test CLI command functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_create_file(self):
        """Test file creation."""
        # Mock args object
        class Args:
            filename = "test_new.md"
        
        args = Args()
        exit_code = create_file(args)
        
        assert exit_code == 0
        assert Path("test_new.md").exists()
        
        # Try to create existing file
        exit_code2 = create_file(args)
        assert exit_code2 == 2  # Should fail
    
    def test_read_file(self):
        """Test file reading."""
        # Create test file
        test_content = "# Test\n\nContent"
        Path("test_read.md").write_text(test_content)
        
        class Args:
            filename = "test_read.md"
        
        args = Args()
        exit_code = read_file(args)
        
        assert exit_code == 0
        
        # Try to read non-existent file
        args.filename = "nonexistent.md"
        exit_code2 = read_file(args)
        assert exit_code2 == 2
    
    def test_delete_file(self):
        """Test file deletion."""
        # Create test file
        Path("test_delete.md").touch()
        
        class Args:
            filename = "test_delete.md"
        
        args = Args()
        exit_code = delete_file(args)
        
        assert exit_code == 0
        assert not Path("test_delete.md").exists()
        
        # Try to delete non-existent file
        exit_code2 = delete_file(args)
        assert exit_code2 == 2


class TestEndToEnd:
    """End-to-end integration tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        # Create spec.yaml
        spec_content = """
structure:
  - min_occurrences: 1
    max_occurrences: 1
    error_level: FATAL
    sequence:
      - type: heading_open
        level: 1
  - min_occurrences: 1
    error_level: WARN
    sequence:
      - type: heading_open
        level: 2
        content_regex: "Description"
"""
        Path("spec.yaml").write_text(spec_content)
        
        # Create links.yaml
        links_content = """
allowed_targets:
  - directory: "."
    filename_regex: ".*\\.md$"
required_links:
  "README.md":
    - "docs/guide.md"
"""
        Path("links.yaml").write_text(links_content)
        
        # Create valid Markdown file
        Path("README.md").write_text("""# Project Title

## Description

This is a test project.

[Link to guide](docs/guide.md)
""")
        
        # Create docs directory and guide
        Path("docs").mkdir()
        Path("docs/guide.md").write_text("# Guide\n\n## Description\n\nGuide content")
        
        # Create invalid file
        Path("invalid.md").write_text("## Missing H1\n\nContent")
        
        # Run validation
        class Args:
            verbose = False
            quiet = False
            dry_run = False
        
        validator = MarkdownValidator()
        exit_code = validator.verify_project(Path.cwd(), dry_run=False)
        
        # Should have errors due to invalid.md
        assert exit_code == 2


# Allow running without pytest
if __name__ == "__main__":
    # Check if pytest is available
    try:
        import pytest
        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not installed. Running basic tests...")
        
        # Run basic tests without pytest
        print("\nRunning basic tests without pytest...")
        
        # Test ValidationResult
        print("Testing ValidationResult...")
        result = ValidationResult(filename="test.md")
        assert result.filename == "test.md"
        assert not result.has_errors
        print("✅ ValidationResult tests passed")
        
        # Test MarkdownValidator initialisation
        print("Testing MarkdownValidator...")
        validator = MarkdownValidator()
        assert validator.md_parser is not None
        print("✅ MarkdownValidator tests passed")
        
        print("\nBasic tests completed successfully!")
        print("For full test coverage, install pytest: pip install pytest")
