# Gherkin 

## Preface: Gherkin Syntax in this Project

In this project, **Gherkin** is used to embed executable verification tests directly inside your Markdown documentation. Unlike standard Gherkin (which usually lives in standalone `.feature` files), this tool parses `gherkin` code blocks found within your `.md` files.

### The Hierarchy

*  **FEATURE:** Represents the high-level capability being tested (e.g., "FEATURE: User Authentication"). This is usually the file level.
*   **SCENARIO:** A specific test case describing a situation (e.g., "SCENARIO: Login with valid credentials").
*  **STEPS:** The individual instructions that are executed sequentially.

### Step Keywords (UPPERCASE)

This project enforces the use of **UPPERCASE** keywords to map English sentences to executable Bash scripts.

  * **`GIVEN` (Setup):** Establishes the initial state. Use this to create resources, generate IDs, or prepare the environment. The output of the *first* `GIVEN` step is captured globally in `$GIVEN_STDOUT`.
  * **`WHEN` (Action):** Performs the action being tested (e.g., sending an API request, running a CLI command).
  * **`THEN` (Assertion):** Verifies the result. If the script executes successfully (exit code 0), the step passes. If it fails (exit code \!= 0), the test fails.
  * **`AND`:** Used to chain multiple steps of the same type (e.g., `GIVEN X, AND Y`).

### The `IMPLEMENTS` Command

The runner bridges the gap between English Gherkin steps and technical implementation using the `IMPLEMENTS` keyword found in `.gherkin` files. The text immediately following the keyword is treated as a **Regular Expression (Regex)**.

#### Syntax

```bash
IMPLEMENTS <Regex Pattern>
<Bash Script Body>
```

  * **Regex Mapping:** The runner matches the Gherkin step text against these regex patterns.
  * **Case Insensitivity:** The matching ignores case, so `IMPLEMENTS the user matches` handles "GIVEN THE USER MATCHES".
  * **Capture Groups:** Use regex groups `(.*)` to capture dynamic values from the step text, which are injected as variables `$MATCH_1`, `$MATCH_2`, etc.

#### Example

```bash
# Gherkin: "GIVEN the service 'nginx' is active"
IMPLEMENTS the service '(.*)' is active
  SERVICE_NAME="$MATCH_1"
  systemctl is-active --quiet "$SERVICE_NAME"
```

### Environment Variables

The runner injects specific context variables into the shell environment before executing your script. You can access these like any other Bash variable.

| Variable | Description |
| :--- | :--- |
| **`$MATCH_1`, `$MATCH_2`...** | The text captured by your regex groups. `$MATCH_1` is the first group, `$MATCH_2` the second, etc. |
| **`$GIVEN_STDOUT`** | The standard output (stdout) of the **first `GIVEN` step** in the scenario. This persists across all steps, making it ideal for referencing an ID created during setup. |
| **`$PREVIOUS_STEP_STDOUT`** | The stdout of the **immediately preceding** step. Use this to chain steps together (e.g., Step B parses the output of Step A). |
| **`$CATEGORY_DIR`** | The absolute path to the output directory for the current feature's category (e.g., `../dashboard/categories/operations`). Use this path to save logs or artifacts. |
| **`$VFILENAME`** | The filename (without extension) of the verification Markdown file currently being run. Useful for generating unique log filenames. |

### Using External Tools (jq & Miller)

Because these implementations are standard Bash scripts, you are encouraged to use powerful CLI tools for robust data processing and assertions.

  * **[jq](https://jqlang.github.io/jq/):** Essential for parsing JSON output from API calls or logs.

    ```bash
    # Example: Check if a JSON response contains a specific status
    echo "$PREVIOUS_STEP_STDOUT" | jq -e '.status == "active"'
    ```

  * **[Miller (mlr)](https://miller.readthedocs.io):** Recommended for processing CSV, TSV, and tabular data. It works like `awk`, `sed`, and `cut` combined but is aware of headers and data types.

    ```bash
    # Example: Filter a CSV file for a specific user ID
    mlr --csv filter '$id == 101' input.csv
    ```

### Cross-Platform Execution (Windows Support)

The runner is designed to work consistently on both Linux and Windows environments.

  * **Windows:** The runner automatically detects and uses **Git Bash** (part of Git for Windows). It does *not* use WSL, ensuring your scripts run in the native Windows context.
  * **Shebangs:** You do not need to include `#!/bin/bash` at the top of your scripts; the runner handles execution explicitly.
  * **Line Endings:** Windows CRLF line endings are automatically normalized to Unix LF to prevent syntax errors.