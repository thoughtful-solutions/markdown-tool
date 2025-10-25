#!/usr/bin/env python3
"""
Verification Markdown Chart Generator

This CLI tool parses a single verification markdown file, extracts metadata,
and generates a corresponding HTML chart page for the dashboard.
"""

import argparse
import re
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

def parse_verification_file(filepath: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parses a verification markdown file to find the Feature Title, Category, and Display Control.

    Args:
        filepath: The path to the markdown file.

    Returns:
        A tuple of (title, category, display_control). Values are None if not found.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # --- MODIFIED SECTION ---
        # 1. Find Title (from Gherkin FEATURE tag)
        # This now looks for "FEATURE: ..." instead of "# V: ..."
        title_match = re.search(
            r'^\s*FEATURE:\s*(.*)$',
            content,
            re.IGNORECASE | re.MULTILINE
        )
        title = title_match.group(1).strip() if title_match else None
        # --- END OF MODIFIED SECTION ---

        # 2. Find Category
        category_match = re.search(
            r'^\s*-\s*\*\*(?i:Category)\*\*:\s*(.*)$',
            content,
            re.MULTILINE
        )
        category = category_match.group(1).strip() if category_match else None

        # 3. Find Display Control
        control_match = re.search(
            r'^\s*-\s*\*\*(?i:Display Control)\*\*:\s*(.*)$',
            content,
            re.MULTILINE
        )
        display_control = control_match.group(1).strip().lower() if control_match else None

        return title, category, display_control

    except FileNotFoundError:
        print(f"    **ERROR**: File not found at {filepath}", file=sys.stderr)
        return None, None, None
    except Exception as e:
        print(f"    **ERROR**: Could not parse {filepath}: {e}", file=sys.stderr)
        return None, None, None

# --- HTML Template Generators ---

def generate_pie_chart_html(title: str, json_filename: str) -> str:
    """
    Generates the HTML content for a Pie Chart page.
    Assumes JSON format: [{"model": "Name 1", "count": 10}, {"model": "Name 2", "count": 20}]
    """
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; max-width: 900px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #333; }}
        #chartContainer {{ position: relative; height: 500px; margin-top: 20px; }}
        .error-message {{ color: #D8000C; background-color: #FFD2D2; border: 1px solid #D8000C; padding: 15px; border-radius: 5px; text-align: left; }}
        .error-message h2 {{ margin-top: 0; }}
        .error-message code {{ background-color: #FFF; padding: 2px 5px; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div id="chartContainer">
        <canvas id="myChart"></canvas>
    </div>
    
    <script>
        fetch('{json_filename}')
            .then(response => {{
                // Check if the response is ok (status 200-299)
                if (!response.ok) {{
                    throw new Error(`Network response was not ok: ${{response.status}} ${{response.statusText}}`);
                }}
                return response.json();
            }})
            .then(data => {{
                // Assumes data is like: [{{ "model": "SaaS", "count": 4 }}, ...]
                const labels = data.map(item => item.model);
                const values = data.map(item => item.count);
                
                // Dynamic color generation
                const backgroundColors = values.map((_, i) => `hsl(${{i * 360 / values.length}}, 70%, 60%)`);
                
                const ctx = document.getElementById('myChart');
                new Chart(ctx, {{
                    type: 'pie',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: 'Count',
                            data: values,
                            backgroundColor: backgroundColors,
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'bottom' }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        return context.label + ': ' + context.parsed;
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }})
            .catch(error => {{
                console.error('Error loading data:', error);
                let errorMessage = `
                    <div class="error-message">
                        <h2>Error Loading Chart Data</h2>
                        <p>Could not fetch or parse data from <code>{json_filename}</code>.</p>
                        <p><strong>Possible Reason:</strong></p>`;
                
                if (error instanceof SyntaxError && error.message.includes("Unexpected token")) {{
                    errorMessage += `<p>The file was found, but it is not valid JSON. This often happens if the file is missing and a 404 HTML page was returned instead.</p>`;
                }} else if (error.message.includes("Network response was not ok")) {{
                    errorMessage += `<p>The data file <code>{json_filename}</code> could not be found (e.g., 404 Not Found).</p>`;
                }} else {{
                    errorMessage += `<p>An unexpected error occurred: ${{error.message}}</p>`;
                }}
                
                errorMessage += `<p>Please ensure the JSON file exists in the same directory as this HTML file and contains valid data.</p></div>`;
                document.getElementById('chartContainer').innerHTML = errorMessage;
            }});
    </script>
</body>
</html>
"""

def generate_traffic_light_html(title: str, json_filename: str) -> str:
    """
    Generates the HTML content for a Traffic Light page.
    Assumes JSON format: {{ "status": "Green" | "Amber" | "Red", "value": "99.5%" }}
    """
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; text-align: center; }}
        h1 {{ color: #333; }}
        .traffic-light {{
            background: #222;
            display: inline-block;
            padding: 15px;
            border-radius: 20px;
            margin-top: 20px;
        }}
        .light {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: #444;
            margin: 10px;
            opacity: 0.3;
        }}
        .light.red {{ background-color: #F00; }}
        .light.amber {{ background-color: #FF0; }}
        .light.green {{ background-color: #0F0; }}
        .light.on {{ opacity: 1; }}
        h2 {{ margin-top: 20px; }}
        .error-message {{ color: #D8000C; background-color: #FFD2D2; border: 1px solid #D8000C; padding: 15px; border-radius: 5px; text-align: left; max-width: 600px; margin: 20px auto; }}
        .error-message code {{ background-color: #FFF; padding: 2px 5px; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="traffic-light">
        <div id="light-red" class="light red"></div>
        <div id="light-amber" class="light amber"></div>
        <div id="light-green" class="light green"></div>
    </div>
    <h2 id="status-value">Loading...</h2>
    
    <script>
        fetch('{json_filename}')
            .then(response => {{
                if (!response.ok) {{
                    throw new Error(`Network response was not ok: ${{response.status}} ${{response.statusText}}`);
                }}
                return response.json();
            }})
            .then(data => {{
                // Assumes data is like: {{ "status": "Green", "value": "99.5%" }}
                const status = data.status ? data.status.toLowerCase() : '';
                const value = data.value || 'N/A';
                
                document.getElementById('status-value').innerText = `Status: ${{data.status || 'Unknown'}} (${{value}})`;
                
                if (status === 'green') {{
                    document.getElementById('light-green').classList.add('on');
                }} else if (status === 'amber') {{
                    document.getElementById('light-amber').classList.add('on');
                }} else if (status === 'red') {{
                    document.getElementById('light-red').classList.add('on');
                }}
            }})
            .catch(error => {{
                console.error('Error loading data:', error);
                let errorMessage = `
                    <div class="error-message">
                        <strong>Error Loading Status:</strong><br>`;
                
                if (error instanceof SyntaxError && error.message.includes("Unexpected token")) {{
                    errorMessage += `Could not parse data from <code>{json_filename}</code>. It may be an HTML 404 page.`;
                }} else if (error.message.includes("Network response was not ok")) {{
                    errorMessage += `Data file <code>{json_filename}</code> could not be found.`;
                }} else {{
                    errorMessage += `An unexpected error occurred: ${{error.message}}`;
                }}
                errorMessage += `</div>`;
                document.getElementById('status-value').innerHTML = errorMessage;
            }});
    </script>
</body>
</html>
"""

def generate_temperature_bar_html(title: str, json_filename: str) -> str:
    """
    Generates the HTML content for a Temperature Bar page.
    Assumes JSON format: {{ "value": 95, "threshold_red": 90, "threshold_amber": 98 }}
    """
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; text-align: center; }}
        h1 {{ color: #333; }}
        .bar-container {{
            width: 80%;
            max-width: 600px;
            height: 50px;
            background: #eee;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin: 20px auto;
            position: relative;
            overflow: hidden;
        }}
        .bar-fill {{
            height: 100%;
            width: 0%; /* Set by JS */
            background-color: #ccc; /* Default/loading color */
            transition: width 0.5s ease, background-color 0.5s ease;
            position: absolute;
            left: 0;
            top: 0;
        }}
        .bar-label {{
            position: absolute;
            width: 100%;
            text-align: center;
            line-height: 50px;
            font-size: 1.2em;
            font-weight: bold;
            color: #000;
            text-shadow: 0 0 2px #fff;
        }}
        .bar-label.error {{
            color: #D8000C;
            text-shadow: none;
            font-size: 1em;
            line-height: 1.2em;
            padding: 10px;
            box-sizing: border-box;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="bar-container">
        <div id="bar-fill" class="bar-fill"></div>
        <div id="bar-label" class="bar-label">Loading...</div>
    </div>
    
    <script>
        fetch('{json_filename}')
            .then(response => {{
                if (!response.ok) {{
                    throw new Error(`Network response was not ok: ${{response.status}} ${{response.statusText}}`);
                }}
                return response.json();
            }})
            .then(data => {{
                // Assumes data is like: {{ "value": 95, "threshold_red": 90, "threshold_amber": 98 }}
                const value = data.value || 0;
                const red = data.threshold_red || 90;
                const amber = data.threshold_amber || 98;
                
                let color = '#d9534f'; // Red
                if (value >= amber) {{
                    color = '#5cb85c'; // Green
                }} else if (value >= red) {{
                    color = '#f0ad4e'; // Amber
                }}
                
                const fillElement = document.getElementById('bar-fill');
                fillElement.style.width = value + '%';
                fillElement.style.backgroundColor = color;
                
                document.getElementById('bar-label').innerText = value + '%';
            }})
            .catch(error => {{
                console.error('Error loading data:', error);
                const labelElement = document.getElementById('bar-label');
                labelElement.classList.add('error');
                
                if (error instanceof SyntaxError && error.message.includes("Unexpected token")) {{
                    labelElement.innerText = `Error: Could not parse '{json_filename}'. File may be missing.`;
                }} else if (error.message.includes("Network response was not ok")) {{
                    labelElement.innerText = `Error: Could not find file '{json_filename}'.`;
                }} else {{
                    labelElement.innerText = `Error: ${{error.message}}`;
                }}
                
                document.getElementById('bar-fill').style.backgroundColor = '#FADBD8';
            }});
    </script>
</body>
</html>
"""

def main():
    """
    Main entry point for the CLI tool.
    """
    parser = argparse.ArgumentParser(
        description="A CLI tool to generate an HTML chart from a single verification markdown file."
    )
    parser.add_argument(
        'filepath',
        help="Path to the single .md file to process. (e.g., verification/service-tag.md)"
    )
    
    args = parser.parse_args()
    
    md_file_path = Path(args.filepath)
    
    print(f"--> Processing: {md_file_path}")
    
    title, category, control = parse_verification_file(args.filepath)
    
    if not title:
        print(f"    **ERROR**: Could not find 'FEATURE:' name in {md_file_path.name}.")
        print("    Generation failed.")
        sys.exit(1)
    if not category:
        print(f"    **ERROR**: Could not find 'Category:' in {md_file_path.name}.")
        print("    Generation failed.")
        sys.exit(1)
    if not control:
        print(f"    **ERROR**: Could not find 'Display Control:' in {md_file_path.name}.")
        print("    Generation failed.")
        sys.exit(1)
        
    print(f"    - Title:   '{title}'")
    print(f"    - Category: '{category}'")
    print(f"    - Control:  '{control}'")
    
    # Determine paths
    base_name = md_file_path.stem
    json_filename = f"{base_name}.json"
    html_filename = f"{base_name}.html"
    
    try:
        md_dir = md_file_path.parent.resolve()
        project_root = md_dir.parent 
        category_dir = project_root / 'dashboard' / 'categories' / category.lower()
        
        category_dir.mkdir(parents=True, exist_ok=True)
        
        output_html_path = category_dir / html_filename
        
        html_content = ""
        if 'pie chart' in control:
            html_content = generate_pie_chart_html(title, json_filename)
        elif 'traffic light' in control:
            html_content = generate_traffic_light_html(title, json_filename)
        elif 'temperature bar' in control:
            html_content = generate_temperature_bar_html(title, json_filename)
        else:
            print(f"    **WARNING**: No HTML template found for display control '{control}'. Skipping.")
            sys.exit(1)
            
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"    V OK: Generated HTML chart at: {output_html_path.relative_to(project_root)}")
        
    except Exception as e:
        print(f"    **ERROR**: Failed to write HTML file for {md_file_path.name}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone. Processed {md_file_path.name} successfully.")

if __name__ == "__main__":
    main()
