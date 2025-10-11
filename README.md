# Markdown Validator CLI

A Python CLI tool for Markdown document validation and management. Validates document structure against specifications and ensures link integrity across your markdown project.

## Why Use This Tool?

When managing large documentation projects or knowledge bases with multiple interconnected markdown files, maintaining consistency and link integrity becomes challenging:

- **Structural consistency**: Ensures all documents follow the same format (e.g., all API docs have the same sections in the same order)
- **Link rot prevention**: Detects broken links before they reach production
- **Bidirectional relationships**: Identifies one-way links that should be bidirectional (e.g., related documents that reference each other)
- **Automated validation**: Integrates into CI/CD pipelines to catch issues during development
- **Documentation quality**: Enforces documentation standards across teams and contributors

This tool provides automated enforcement of documentation standards, preventing common issues like missing sections, broken links, and inconsistent document structure.

## Configuration Files

### spec.yaml - Document Structure Specification

The `spec.yaml` file defines the expected structure of your markdown documents. It specifies sequences of markdown elements that documents must contain.

#### Structure

```yaml
structure:
  - sequence:
      - type: heading_open
        level: 1
        content_regex: ".*"
      - type: paragraph_open
    min_occurrences: 1
    max_occurrences: 1
    error_level: FATAL
    
  - sequence:
      - type: heading_open
        level: 2
      - type: fence
        info: python
    min_occurrences: 0
    max_occurrences: null
    error_level: WARN
```

#### Fields Explained

**Block-level fields:**
- `sequence`: Array of element steps that must appear in order
- `min_occurrences`: Minimum times this block must appear (default: 1)
- `max_occurrences`: Maximum times this block can appear (null = unlimited)
- `error_level`: Severity level - `FATAL`, `WARN`, or `INFO`

**Sequence step fields:**
- `type`: Token type from markdown-it parser:
  - `heading_open`: Heading element
  - `paragraph_open`: Paragraph element
  - `fence`: Code block
  - `list_item_open`: List item
  - `inline`: Inline content (used internally)
- `level`: (Optional) For headings, specifies H1-H6 (1-6)
- `info`: (Optional) For code blocks, specifies language (e.g., `python`, `javascript`)
- `content_regex`: (Optional) Regex pattern that content must fully match

#### Example Use Cases

**Enforce standard document template:**
```yaml
structure:
  # Every document must start with H1 title
  - sequence:
      - type: heading_open
        level: 1
    min_occurrences: 1
    max_occurrences: 1
    error_level: FATAL
  
  # Must have a "Description" section
  - sequence:
      - type: heading_open
        level: 2
        content_regex: "Description"
      - type: paragraph_open
    min_occurrences: 1
    max_occurrences: 1
    error_level: FATAL
  
  # Can have multiple example code blocks
  - sequence:
      - type: heading_open
        level: 2
        content_regex: "Example.*"
      - type: fence
        info: python
    min_occurrences: 0
    max_occurrences: null
    error_level: WARN
```

### links.yaml - Link Integrity Specification

The `links.yaml` file manages link relationships between markdown files. It defines which links are allowed and tracks established connections between documents.

#### Structure

```yaml
allowed_targets:
  - directory: "../docs"
    filename_regex: ".*\\.md"
  - directory: "."
    filename_regex: "README\\.md"

established_links:
  document1.md:
    - document2.md
    - ../docs/api.md
  document2.md:
    - document1.md

required_links:
  document1.md:
    - document2.md
```

#### Fields Explained

**`allowed_targets`**: Defines which directories and files are valid link targets
- `directory`: Relative path to allowed directory
- `filename_regex`: Regex pattern matching allowed filenames

**`established_links`**: Maps source files to their target links
- Key: Source markdown filename
- Value: Array of relative paths to target files
- Used to verify bidirectional relationships and file existence

**`required_links`**: (Optional) Specifies links that must exist in certain files
- Key: Markdown filename
- Value: Array of links that must be present in that file

#### Example Use Cases

**Restrict cross-references to specific directories:**
```yaml
allowed_targets:
  # Can only link to markdown files in current directory
  - directory: "."
    filename_regex: ".*\\.md"
  # Can link to API docs
  - directory: "../api"
    filename_regex: ".*\\.md"
  # Can link to specific guide files
  - directory: "../guides"
    filename_regex: "(getting-started|advanced)\\.md"
```

**Track bidirectional relationships:**
```yaml
established_links:
  overview.md:
    - details.md
  details.md:
    - overview.md  # Reverse link creates bidirectional relationship
```

If `details.md` doesn't link back to `overview.md`, the validator will report a unidirectional link error.

**Enforce required links:**
```yaml
required_links:
  README.md:
    - LICENSE.md
    - CONTRIBUTING.md
```

Ensures your README always includes links to license and contribution guidelines.

#### Multiple links.yaml Files

You can have `links.yaml` files in multiple directories. The validator will:
1. Start with the root `links.yaml`
2. Scan all directories listed in `allowed_targets`
3. Build a complete link graph from all `links.yaml` files found
4. Validate relationships across the entire project

## What is Validated

### Document Structure (`verify-doc`)

The tool validates markdown document structure against a `spec.yaml` specification file:

- **Element sequences**: Ensures documents follow a specific order of markdown elements (headings, paragraphs, code blocks, list items, etc.)
- **Heading levels**: Validates heading hierarchy (H1, H2, H3, etc.)
- **Code block languages**: Checks that code fences use expected language identifiers
- **Content patterns**: Validates content against regex patterns (e.g., ensuring a heading contains specific text)
- **Occurrence constraints**: Enforces minimum and maximum occurrences of document blocks
- **Error levels**: Supports FATAL, WARN, and INFO severity levels for different validation rules

### Hyperlink Integrity (`verify-link`)

The tool validates links defined in `links.yaml` files:

- **Allowed targets**: Ensures links only point to permitted directories/files based on regex rules
- **File existence**: Verifies that all linked files actually exist on disk
- **Bidirectional links**: Checks whether target files link back to source files (detecting one-way links)
- **Link graph analysis**: Builds a complete graph of all links across the project for relationship analysis

## How Validation Works

### Structure Validation Process

1. **Parse markdown**: Uses `markdown-it-py` to convert markdown into a token stream
2. **Load spec**: Reads `spec.yaml` from the target directory defining expected structure
3. **Sequential matching**: Steps through tokens matching against the sequence of elements defined in each block
4. **Occurrence tracking**: Counts how many times each block appears and validates against min/max constraints
5. **Error reporting**: Reports specific line numbers and describes what was expected vs. what was found

### Link Validation Process

1. **Load links.yaml**: Reads link specifications from the project directory
2. **Build link graph**: Scans all `links.yaml` files in allowed directories to build a complete relationship map
3. **Run checks**: For each link defined in `established_links`:
   - Validates against `allowed_targets` rules
   - Verifies file existence
   - Checks for reverse link in target's `links.yaml`
4. **Report results**: Provides summary view with unidirectional link counts or verbose multi-check details

## CLI Options

### Global Flags

```bash
--verbose    Enable detailed output for debugging
--quiet      Suppress non-error messages (only show errors)
```

### Commands

#### File Management

**`create <filename>`**
```bash
md_validator.py create my_document.md
```
Creates a new markdown file with a basic template.

**`read <filename>`**
```bash
md_validator.py read my_document.md
```
Displays the contents of a markdown file.

**`update <filename> <section_name> <content>`**
```bash
md_validator.py update my_document.md "Introduction" "New content here"
```
Updates a section in a markdown file (placeholder implementation).

**`delete <filename>`**
```bash
md_validator.py delete my_document.md
```
Deletes a markdown file.

#### Validation Commands

**`verify-doc [directory]`**
```bash
md_validator.py verify-doc .
md_validator.py --verbose verify-doc ./docs
```
Validates all markdown files in the specified directory (defaults to current directory) against `spec.yaml`.

**Exit codes:**
- `0`: All files valid
- `1`: Warnings found
- `2`: Fatal errors found

**`verify-link [directory]`**
```bash
md_validator.py verify-link .
md_validator.py --verbose verify-link ./docs
```
Validates established links in the `links.yaml` file from the specified directory (defaults to current directory).

**Exit codes:**
- `0`: All links valid
- `1`: Link errors found (broken, disallowed, or unidirectional)
- `16`: System error (missing links.yaml, parse errors)

**Default output** shows a summary table:
```
Link Summary (Uni-TO | Total-TO <-> Total-FROM | Uni-FROM):
  [2] [5] document1.md [3] [1]
```

**Verbose output** (`--verbose`) shows detailed validation results for each link including all three checks (allowed target, file existence, bidirectional link).

## Requirements

- Python 3.7+
- `markdown-it-py`: `pip install markdown-it-py`
- `PyYAML`: `pip install pyyaml`
