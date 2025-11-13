
# Gherkin Verification Syntax

## Value Proposition: Why Executable Markdown?

This project decouples verification from standalone test suites, embedding it directly into documentation. This approach addresses three critical engineering challenges:

 **Prevention of Documentation Drift:** By treating documentation as an executable test specification, the markdown document cannot diverge from the actual codebase without triggering a test failure.

 **Contextual Verification:** Snippets run within the directory context of the documentation, ensuring that file paths and environment configs described to the user are accurate.

 **Simplified Toolchain:** Replaces complex Cucumber/Ruby/Java stacks with standard Bash scripts, lowering the barrier to entry for writing verification logic.

-----

## Architecture & Workflow

The verification process relies on three distinct components: the specification (Markdown), the logic (Implementation Directory), and the executor (Runner).

  **Define Specification (`.md`):**
    Inside your Markdown documentation, define your validation logic within a fenced code block using the `gherkin` language identifier.

    ````markdown
    # My Documentation
    ...
    ```gherkin
    FEATURE: System Health
      SCENARIO: Check active services
        GIVEN the service 'nginx' is active

    ```
    ```

  **Define Logic (`gherkin-implements/`):**
    Create `.gherkin` files inside the `gherkin-implements` directory. These files map natural language steps to executable Bash scripts using the `IMPLEMENTS` keyword and Regex patterns.

  **Execute (`gherkin-runner.py`):**
    Run the `gherkin-runner.py` script. 
    It performs the following actions:

    * Parses the `gherkin` blocks from the target `.md` file.
    * Scans the `gherkin-implements` directory to match steps against defined Regex patterns.
    * Generates and executes temporary Bash scripts for every step.

-----

## Gherkin Hierarchy

The runner enforces a strict hierarchy to organize tests.

  * **FEATURE:** The high-level capability being tested (e.g., "User Authentication"). Represents the file level.
  * **SCENARIO:** A specific test case describing a situation. A single **FEATURE** may contain **one or more SCENARIOS**.
  * **STEPS:** Sequential instructions (`GIVEN`, `WHEN`, `THEN`) executed within a scenario.

-----

## Step Keywords

Keywords must be **UPPERCASE** to map correctly to executable scripts.

### 1\. `GIVEN` (Setup)

Establishes the initial state. The output of the *first* `GIVEN` step is captured globally in `$GIVEN_STDOUT`.

**Usage:**

```gherkin
GIVEN a temporary directory is created
```

**Implementation (`gherkin-implements/xxxx.gherkin`):**

```bash
IMPLEMENTS a temporary directory is created
  mktemp -d
```

### 2\. `WHEN` (Action)

Performs the action being tested (e.g., API requests, CLI commands).

**Usage:**

```gherkin
WHEN I execute the build command
```

### 3\. `THEN` (Assertion)

Verifies the result. The step passes if the exit code is `0` and fails if the exit code is non-zero.

**Usage:**

```gherkin
THEN the output contains 'BUILD SUCCESSFUL'
```

### 4\. `AND` (Chaining)

Chains multiple steps of the same type (Setup, Action, or Assertion).

**Usage:**

```gherkin
THEN the exit code is 0
AND the log file is empty
```

-----

## Implementation Details

### The `IMPLEMENTS` Keyword

Found in files within the `gherkin-implements` directory, this command maps English steps to Bash.

  * **Regex Mapping:** Matches step text against provided patterns (Case Insensitive).
  * **Capture Groups:** Regex groups `(.*)` are injected as variables `$MATCH_1`, `$MATCH_2`, etc.

### Context Variables

The `gherkin-runner.py` injects these variables into the shell environment.

| Variable | Description |
| :--- | :--- |
| **`$MATCH_N`** | Text captured by regex groups (`$MATCH_1`, `$MATCH_2`...) |
| **`$GIVEN_STDOUT`** | Stdout of the first `GIVEN` step (persists for whole scenario). |
| **`$PREVIOUS_STEP_STDOUT`** | Stdout of the immediately preceding step. |
| **`$CATEGORY_DIR`** | Absolute path to the output directory for the current category. |
| **`$VFILENAME`** | Filename (no extension) of the verification Markdown file. |

-----

## Recommended Tooling

Since implementations are standard Bash scripts, use robust CLI tools for data parsing.

### [jq](https://jqlang.github.io/jq/) (JSON Processor)

Essential for parsing JSON output from API calls or logs.

```bash
# Example: Check if a JSON response contains a specific status
echo "$PREVIOUS_STEP_STDOUT" | jq -e '.status == "active"'
```

### [Miller (mlr)](https://miller.readthedocs.io) (Tabular Data)

Recommended for processing CSV, TSV, and tabular data. Aware of headers and data types.

```bash
# Example: Filter a CSV file for a specific user ID
mlr --csv filter '$id == 101' input.csv
```

-----

## Platform Support

  * **Windows:** The runner detects and uses **Git Bash**. Do not use WSL.
  * **Line Endings:** Windows CRLF is normalized to Unix LF automatically.

-----
