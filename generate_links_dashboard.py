#!/usr/bin/env python3
"""
Enhanced Architecture Links Dashboard Generator

Generates an interactive HTML dashboard visualising the link relationships
between architecture documents AND integrates live verification results
from dashboard/categories directories.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict
import yaml
from datetime import datetime
import re

class EnhancedDashboardGenerator:
    """Generates HTML dashboard from architecture document links and verification results."""
    
    HIERARCHY = ['domains', 'principles', 'rules', 'verification']
    
    LAYER_COLORS = {
        'domains': {'bg': '#cce5ff', 'fg': '#004085', 'accent': '#007bff'},
        'principles': {'bg': '#d4edda', 'fg': '#155724', 'accent': '#28a745'},
        'rules': {'bg': '#fff3cd', 'fg': '#856404', 'accent': '#ffc107'},
        'verification': {'bg': '#f8d7da', 'fg': '#721c24', 'accent': '#dc3545'}
    }
    
    CATEGORY_COLORS = {
        'operations': '#17a2b8',
        'security': '#dc3545',
        'development': '#28a745',
        'regulatory': '#ffc107',
        'risk': '#fd7e14'
    }
    
    def __init__(self, project_dir: Path, output_file: Path = None):
        self.project_dir = project_dir.resolve()
        self.output_file = output_file or (self.project_dir / 'dashboard' / 'links-dashboard.html')
        self.link_graph = defaultdict(set)
        self.all_documents = defaultdict(set)
        self.document_metadata = {}
        self.verification_results = {}
        self.verification_charts = {}
        
    def load_verification_results(self) -> None:
        """Load verification results from dashboard/categories directories."""
        dashboard_dir = self.project_dir / 'dashboard' / 'categories'
        
        if not dashboard_dir.exists():
            print(f"Warning: No dashboard/categories directory found at {dashboard_dir}")
            return
            
        for category_dir in dashboard_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category_name = category_dir.name.lower()
            
            # Look for JSON result files (*.json)
            for json_file in category_dir.glob('*.json'):
                verification_name = json_file.stem
                
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Store the verification result
                    self.verification_results[verification_name] = {
                        'category': category_name,
                        'data': data,
                        'json_file': str(json_file.relative_to(self.project_dir))
                    }
                    
                    # Check for corresponding HTML chart
                    html_file = json_file.with_suffix('.html')
                    if html_file.exists():
                        self.verification_charts[verification_name] = {
                            'html_file': str(html_file.relative_to(self.project_dir)),
                            'category': category_name
                        }
                        
                except Exception as e:
                    print(f"Error loading verification result {json_file}: {e}")
        
        # Also look for .stdout files which contain the full test results
        for category_dir in dashboard_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            for stdout_file in category_dir.glob('*.stdout'):
                verification_name = stdout_file.stem
                
                try:
                    with open(stdout_file, 'r', encoding='utf-8') as f:
                        test_results = json.load(f)
                        
                    if verification_name in self.verification_results:
                        self.verification_results[verification_name]['test_results'] = test_results
                    else:
                        self.verification_results[verification_name] = {
                            'category': category_dir.name.lower(),
                            'test_results': test_results,
                            'stdout_file': str(stdout_file.relative_to(self.project_dir))
                        }
                        
                except Exception as e:
                    print(f"Error loading test results {stdout_file}: {e}")
    
    def parse_verification_metadata(self) -> None:
        """Parse verification markdown files to extract metadata."""
        verification_dir = self.project_dir / 'verification'
        
        if not verification_dir.exists():
            return
            
        for md_file in verification_dir.glob('*.md'):
            verification_name = md_file.stem
            
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract category
                category_match = re.search(r'^\s*-\s*\*\*Category\*\*:\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
                category = category_match.group(1).strip().lower() if category_match else None
                
                # Extract display control
                control_match = re.search(r'^\s*-\s*\*\*Display Control\*\*:\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
                display_control = control_match.group(1).strip().lower() if control_match else None
                
                # Extract thresholds
                thresholds = {}
                threshold_section = re.search(r'\*\*Thresholds\*\*:(.*?)(?=^\s*-\s*\*\*|\Z)', content, re.MULTILINE | re.DOTALL)
                if threshold_section:
                    threshold_text = threshold_section.group(1)
                    green_match = re.search(r'\*\*Green\*\*:\s*([^*\n]+)', threshold_text)
                    amber_match = re.search(r'\*\*Amber\*\*:\s*([^*\n]+)', threshold_text)
                    red_match = re.search(r'\*\*Red\*\*:\s*([^*\n]+)', threshold_text)
                    
                    if green_match: thresholds['green'] = green_match.group(1).strip()
                    if amber_match: thresholds['amber'] = amber_match.group(1).strip()
                    if red_match: thresholds['red'] = red_match.group(1).strip()
                
                # Store metadata
                if verification_name not in self.document_metadata:
                    self.document_metadata[verification_name] = {'layer': 'verification'}
                    
                self.document_metadata[verification_name].update({
                    'category': category,
                    'display_control': display_control,
                    'thresholds': thresholds
                })
                
            except Exception as e:
                print(f"Error parsing verification file {md_file}: {e}")
    
    def load_all_links(self) -> None:
        """Load all links from links.yaml files across the project."""
        # First, scan for all markdown files in the hierarchy
        for layer in self.HIERARCHY:
            layer_dir = self.project_dir / layer
            if layer_dir.exists():
                for md_file in layer_dir.glob('*.md'):
                    doc_name = md_file.stem
                    self.all_documents[layer].add(doc_name)
                    self.document_metadata[doc_name] = {'layer': layer}
        
        # Parse verification metadata
        self.parse_verification_metadata()
        
        # Then load the links
        for layer in self.HIERARCHY:
            layer_dir = self.project_dir / layer
            if not layer_dir.exists():
                continue
                
            links_yaml_path = layer_dir / 'links.yaml'
            if not links_yaml_path.exists():
                continue
                
            try:
                with open(links_yaml_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    
                established = data.get('established_links', {})
                for source_file, targets in established.items():
                    if not targets:
                        continue
                        
                    source_name = Path(source_file).stem
                    self.all_documents[layer].add(source_name)
                    if source_name not in self.document_metadata:
                        self.document_metadata[source_name] = {'layer': layer}
                    
                    for target in targets:
                        # Normalize Windows paths to forward slashes
                        normalized_target = target.replace('\\', '/')
                        target_path = Path(normalized_target)
                        target_name = target_path.stem
                        
                        # Determine target layer from path components
                        target_layer = None
                        path_str = normalized_target.lower()
                        
                        for l in self.HIERARCHY:
                            if f'../{l}/' in path_str or f'/{l}/' in path_str or path_str.startswith(f'{l}/'):
                                target_layer = l
                                break
                        
                        if target_layer:
                            self.link_graph[source_name].add(target_name)
                            self.all_documents[target_layer].add(target_name)
                            if target_name not in self.document_metadata:
                                self.document_metadata[target_name] = {'layer': target_layer}
                            
            except Exception as e:
                print(f"Error loading links from {links_yaml_path}: {e}", file=sys.stderr)
    
    def calculate_stats(self) -> Dict:
        """Calculate dashboard statistics including verification results."""
        # Count incoming links
        incoming_counts = defaultdict(int)
        for source, targets in self.link_graph.items():
            for target in targets:
                incoming_counts[target] += 1
        
        # Calculate bidirectional links
        bidirectional_count = 0
        unidirectional_links = []
        
        for source, targets in self.link_graph.items():
            for target in targets:
                if source in self.link_graph.get(target, set()):
                    bidirectional_count += 1
                else:
                    unidirectional_links.append((source, target))
        
        # Actual bidirectional pairs (divide by 2 as we count each direction)
        bidirectional_count //= 2
        
        total_docs = sum(len(docs) for docs in self.all_documents.values())
        total_links = sum(len(targets) for targets in self.link_graph.values())
        
        docs_with_links = len(self.link_graph) + len(incoming_counts)
        coverage = (docs_with_links / total_docs * 100) if total_docs > 0 else 0
        
        # Calculate verification statistics
        total_verifications = len(self.verification_results)
        passed_verifications = 0
        failed_verifications = 0
        
        for ver_name, ver_data in self.verification_results.items():
            if 'test_results' in ver_data:
                test_results = ver_data['test_results']
                if 'summary' in test_results:
                    scenarios = test_results['summary'].get('scenarios', {})
                    if scenarios.get('failed', 0) == 0 and scenarios.get('total', 0) > 0:
                        passed_verifications += 1
                    else:
                        failed_verifications += 1
        
        return {
            'total_documents': total_docs,
            'total_links': total_links,
            'bidirectional_links': bidirectional_count,
            'unidirectional_links': len(unidirectional_links),
            'link_coverage': round(coverage, 1),
            'incoming_counts': dict(incoming_counts),
            'total_verifications': total_verifications,
            'passed_verifications': passed_verifications,
            'failed_verifications': failed_verifications,
            'verification_coverage': round((total_verifications / len(self.all_documents.get('verification', [])) * 100), 1) if self.all_documents.get('verification') else 0
        }
    
    def generate_verification_status_badge(self, doc_name: str) -> str:
        """Generate a status badge for verification documents."""
        if doc_name not in self.verification_results:
            return '<span class="verification-badge pending">⏳ Not Run</span>'
        
        ver_data = self.verification_results[doc_name]
        
        # Check test results
        if 'test_results' in ver_data:
            test_results = ver_data['test_results']
            if 'summary' in test_results:
                scenarios = test_results['summary'].get('scenarios', {})
                if scenarios.get('failed', 0) > 0:
                    return '<span class="verification-badge failed">❌ Failed</span>'
                elif scenarios.get('total', 0) > 0:
                    return '<span class="verification-badge passed">✅ Passed</span>'
        
        # Check for chart availability
        if doc_name in self.verification_charts:
            return '<span class="verification-badge chart">📊 Chart</span>'
        
        return '<span class="verification-badge unknown">❓ Unknown</span>'
    
    def generate_verification_card(self, doc_name: str, stats: Dict) -> str:
        """Generate an enhanced card for verification documents."""
        metadata = self.document_metadata.get(doc_name, {})
        category = metadata.get('category', 'unknown')
        display_control = metadata.get('display_control', 'unknown')
        
        # Get link information
        outgoing = self.link_graph.get(doc_name, set())
        incoming = stats['incoming_counts'].get(doc_name, 0)
        
        # Get verification status
        status_badge = self.generate_verification_status_badge(doc_name)
        
        # Generate link status badges
        status_badges = f'<span class="link-badge incoming">↓ {incoming}</span>\n'
        status_badges += f'<span class="link-badge outgoing">↑ {len(outgoing)}</span>\n'
        
        # Add verification-specific information
        verification_info = f'''
        <div class="verification-info">
            <div class="verification-meta">
                <span class="category-tag" style="background-color: {self.CATEGORY_COLORS.get(category, '#6c757d')}20; color: {self.CATEGORY_COLORS.get(category, '#6c757d')};">
                    {category.capitalize()}
                </span>
                <span class="display-type">{display_control.replace('_', ' ').title()}</span>
            </div>
            {status_badge}
        </div>'''
        
        # Add links to results if available
        result_links = []
        if doc_name in self.verification_results:
            ver_data = self.verification_results[doc_name]
            if 'json_file' in ver_data:
                result_links.append(f'<a href="{ver_data["json_file"]}" class="result-link">📄 Data</a>')
        
        if doc_name in self.verification_charts:
            chart_data = self.verification_charts[doc_name]
            result_links.append(f'<a href="{chart_data["html_file"]}" class="result-link">📊 Chart</a>')
        
        result_links_html = ' '.join(result_links) if result_links else ''
        
        # Generate link list
        link_items = []
        for target in sorted(outgoing):
            target_layer = self.document_metadata.get(target, {}).get('layer', 'unknown')
            if doc_name in self.link_graph.get(target, set()):
                arrow = '↔'
            else:
                arrow = '→'
            link_items.append(f'''
                <div class="link-item">
                    <span class="link-arrow">{arrow}</span>
                    <span class="link-target">{target}</span>
                    <span class="link-type-badge">{target_layer}</span>
                </div>''')
        
        # Add incoming-only links
        for source, targets in self.link_graph.items():
            if doc_name in targets and source not in outgoing:
                source_layer = self.document_metadata.get(source, {}).get('layer', 'unknown')
                link_items.append(f'''
                <div class="link-item">
                    <span class="link-arrow">←</span>
                    <span class="link-target">{source}</span>
                    <span class="link-type-badge">{source_layer}</span>
                </div>''')
        
        link_list = ''.join(link_items) if link_items else '<p style="color: #6c757d; font-style: italic;">No established links</p>'
        
        return f'''
        <div class="document-card verification-card">
            <div class="document-header">
                <h3 class="document-name">{doc_name}</h3>
                <div class="link-status">
                    {status_badges}
                </div>
            </div>
            {verification_info}
            {f'<div class="result-links">{result_links_html}</div>' if result_links_html else ''}
            <div class="link-details">
                <div class="link-list">
                    {link_list}
                </div>
            </div>
        </div>'''
    
    def generate_document_card(self, doc_name: str, layer: str, stats: Dict) -> str:
        """Generate HTML for a single document card."""
        # Use special card for verification documents
        if layer == 'verification':
            return self.generate_verification_card(doc_name, stats)
        
        # Standard card for other layers
        outgoing = self.link_graph.get(doc_name, set())
        incoming = stats['incoming_counts'].get(doc_name, 0)
        
        # Determine link status
        has_bidirectional = False
        for target in outgoing:
            if doc_name in self.link_graph.get(target, set()):
                has_bidirectional = True
                break
        
        status_badges = f'<span class="link-badge incoming">↓ {incoming}</span>\n'
        status_badges += f'<span class="link-badge outgoing">↑ {len(outgoing)}</span>\n'
        
        if has_bidirectional:
            status_badges += '<span class="link-badge bidirectional">✓</span>'
        elif len(outgoing) == 0 and incoming == 0:
            status_badges += '<span class="link-badge unidirectional">⚠️</span>'
        
        # Generate link list
        link_items = []
        for target in sorted(outgoing):
            target_layer = self.document_metadata.get(target, {}).get('layer', 'unknown')
            if doc_name in self.link_graph.get(target, set()):
                arrow = '↔'
            else:
                arrow = '→'
            link_items.append(f'''
                <div class="link-item">
                    <span class="link-arrow">{arrow}</span>
                    <span class="link-target">{target}</span>
                    <span class="link-type-badge">{target_layer}</span>
                </div>''')
        
        # Add incoming-only links
        for source, targets in self.link_graph.items():
            if doc_name in targets and source not in outgoing:
                source_layer = self.document_metadata.get(source, {}).get('layer', 'unknown')
                link_items.append(f'''
                <div class="link-item">
                    <span class="link-arrow">←</span>
                    <span class="link-target">{source}</span>
                    <span class="link-type-badge">{source_layer}</span>
                </div>''')
        
        link_list = ''.join(link_items) if link_items else '<p style="color: #6c757d; font-style: italic;">No established links</p>'
        
        return f'''
        <div class="document-card">
            <div class="document-header">
                <h3 class="document-name">{doc_name}</h3>
                <div class="link-status">
                    {status_badges}
                </div>
            </div>
            <div class="link-details">
                <div class="link-list">
                    {link_list}
                </div>
            </div>
        </div>'''
    
    def generate_verification_summary(self, stats: Dict) -> str:
        """Generate a summary section for verification results."""
        if not self.verification_results:
            return ''
        
        # Group verifications by category
        by_category = defaultdict(list)
        for ver_name, ver_data in self.verification_results.items():
            category = ver_data.get('category', 'unknown')
            by_category[category].append((ver_name, ver_data))
        
        category_cards = []
        for category in sorted(by_category.keys()):
            verifications = by_category[category]
            
            passed = failed = pending = 0
            for ver_name, ver_data in verifications:
                if 'test_results' in ver_data:
                    test_results = ver_data['test_results']
                    if 'summary' in test_results:
                        scenarios = test_results['summary'].get('scenarios', {})
                        if scenarios.get('failed', 0) > 0:
                            failed += 1
                        else:
                            passed += 1
                else:
                    pending += 1
            
            color = self.CATEGORY_COLORS.get(category, '#6c757d')
            
            category_cards.append(f'''
            <div class="category-summary-card">
                <div class="category-header" style="border-left: 4px solid {color};">
                    <h4>{category.capitalize()}</h4>
                    <span class="category-count">{len(verifications)} tests</span>
                </div>
                <div class="category-stats">
                    <span class="stat-item passed">✅ {passed}</span>
                    <span class="stat-item failed">❌ {failed}</span>
                    <span class="stat-item pending">⏳ {pending}</span>
                </div>
            </div>''')
        
        return f'''
        <section id="verification-summary" class="layer-section">
            <div class="layer-header">
                <h2 class="layer-title">Verification Results</h2>
                <span class="layer-badge badge-verification">Live Status</span>
            </div>
            <div class="category-grid">
                {''.join(category_cards)}
            </div>
        </section>'''
    
    def generate_dashboard(self) -> str:
        """Generate the complete HTML dashboard with verification results."""
        stats = self.calculate_stats()
        
        # Generate layer sections
        layer_sections = []
        for layer in self.HIERARCHY:
            if layer not in self.all_documents or not self.all_documents[layer]:
                continue
                
            colors = self.LAYER_COLORS[layer]
            layer_title = layer.capitalize()
            
            # Generate document cards for this layer
            cards = []
            for doc_name in sorted(self.all_documents[layer]):
                cards.append(self.generate_document_card(doc_name, layer, stats))
            
            section = f'''
            <section id="{layer}" class="layer-section">
                <div class="layer-header">
                    <h2 class="layer-title">{layer_title}</h2>
                    <span class="layer-badge badge-{layer}">{len(self.all_documents[layer])} Documents</span>
                </div>
                <div class="documents-grid">
                    {''.join(cards)}
                </div>
            </section>'''
            
            layer_sections.append(section)
        
        # Add verification summary if we have results
        verification_summary = self.generate_verification_summary(stats)
        if verification_summary:
            layer_sections.insert(0, verification_summary)
        
        # Generate navigation items
        nav_items = []
        
        if self.verification_results:
            nav_items.append(f'''
            <a href="#verification-summary" class="nav-item">
                <span class="nav-icon">📈</span>
                <span class="nav-text">Test Results</span>
                <span class="nav-count">{stats['total_verifications']}</span>
            </a>''')
        
        for layer in self.HIERARCHY:
            count = len(self.all_documents[layer])
            if count > 0:
                icon = {'domains': '🏛️', 'principles': '📐', 'rules': '📋', 'verification': '✓'}.get(layer, '📄')
                nav_items.append(f'''
                <a href="#{layer}" class="nav-item {layer}">
                    <span class="nav-icon">{icon}</span>
                    <span class="nav-text">{layer.capitalize()}</span>
                    <span class="nav-count">{count}</span>
                </a>''')
        
        # Enhanced CSS with verification-specific styles
        enhanced_css = '''
        .verification-card { border-top: 3px solid #dc3545; }
        .verification-info { padding: 1rem 0; border-bottom: 1px solid #e9ecef; }
        .verification-meta { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
        .category-tag { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
        .display-type { color: #6c757d; font-size: 0.85rem; }
        .verification-badge { padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
        .verification-badge.passed { background-color: #d4edda; color: #155724; }
        .verification-badge.failed { background-color: #f8d7da; color: #721c24; }
        .verification-badge.pending { background-color: #fff3cd; color: #856404; }
        .verification-badge.chart { background-color: #d1ecf1; color: #0c5460; }
        .verification-badge.unknown { background-color: #e9ecef; color: #6c757d; }
        .result-links { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
        .result-link { padding: 0.2rem 0.5rem; background: #f8f9fa; border-radius: 4px; text-decoration: none; color: #495057; font-size: 0.85rem; }
        .result-link:hover { background: #e9ecef; }
        .category-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .category-summary-card { background: white; border-radius: 8px; padding: 1.5rem; border: 1px solid #e9ecef; }
        .category-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; padding-left: 1rem; }
        .category-header h4 { margin: 0; font-size: 1.1rem; }
        .category-count { background: #f8f9fa; padding: 0.2rem 0.5rem; border-radius: 12px; font-size: 0.75rem; }
        .category-stats { display: flex; gap: 1rem; }
        .stat-item { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.85rem; }
        .stat-item.passed { background: #d4edda; color: #155724; }
        .stat-item.failed { background: #f8d7da; color: #721c24; }
        .stat-item.pending { background: #fff3cd; color: #856404; }
        '''
        
        html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Architecture Documentation Dashboard - Enhanced</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8f9fa; color: #333; line-height: 1.6; }}
        .container {{ display: flex; min-height: 100vh; }}
        .header {{ background: linear-gradient(135deg, #5a6fd8 0%, #4a5cc5 100%); color: white; padding: 1rem 2rem; position: fixed; top: 0; left: 280px; right: 0; z-index: 100; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header h1 {{ font-size: 1.5rem; font-weight: 600; }}
        .header .subtitle {{ font-size: 0.9rem; opacity: 0.9; margin-top: 0.25rem; }}
        .sidebar {{ width: 280px; background: white; border-right: 1px solid #e9ecef; position: fixed; top: 0; left: 0; height: 100vh; overflow-y: auto; z-index: 200; }}
        .sidebar-header {{ padding: 1.5rem; border-bottom: 1px solid #e9ecef; background-color: #f8f9fa; }}
        .sidebar-header h3 {{ color: #495057; font-size: 1.1rem; font-weight: 600; }}
        .sidebar-nav {{ padding: 1rem 0; }}
        .nav-item {{ display: flex; align-items: center; padding: 0.75rem 1.5rem; color: #495057; text-decoration: none; transition: all 0.2s ease; border-left: 3px solid transparent; cursor: pointer; }}
        .nav-item:hover {{ background-color: #f8f9fa; color: #5a6fd8; }}
        .nav-item.active {{ background-color: #e3f2fd; color: #5a6fd8; border-left-color: #5a6fd8; }}
        .nav-icon {{ font-size: 1.2rem; margin-right: 0.75rem; width: 24px; text-align: center; }}
        .nav-text {{ font-weight: 500; font-size: 0.9rem; }}
        .nav-count {{ margin-left: auto; background-color: #e9ecef; color: #495057; padding: 0.2rem 0.5rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
        .main-content {{ flex: 1; margin-left: 280px; margin-top: 80px; padding: 2rem; }}
        .layer-section {{ background: white; border-radius: 8px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .layer-header {{ display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; }}
        .layer-title {{ font-size: 1.75rem; font-weight: 600; color: #2c3e50; }}
        .layer-badge {{ padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
        .badge-domains {{ background-color: #cce5ff; color: #004085; }}
        .badge-principles {{ background-color: #d4edda; color: #155724; }}
        .badge-rules {{ background-color: #fff3cd; color: #856404; }}
        .badge-verification {{ background-color: #f8d7da; color: #721c24; }}
        .documents-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; }}
        .document-card {{ background: #fff; border: 1px solid #e9ecef; border-radius: 8px; padding: 1.5rem; transition: all 0.2s ease; }}
        .document-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); }}
        .document-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }}
        .document-name {{ font-size: 1.1rem; font-weight: 600; color: #2c3e50; margin: 0; }}
        .link-status {{ display: flex; gap: 0.5rem; }}
        .link-badge {{ display: flex; align-items: center; gap: 0.25rem; padding: 0.2rem 0.5rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
        .link-badge.incoming {{ background-color: #e3f2fd; color: #1976d2; }}
        .link-badge.outgoing {{ background-color: #f3e5f5; color: #7b1fa2; }}
        .link-badge.bidirectional {{ background-color: #e8f5e9; color: #388e3c; }}
        .link-badge.unidirectional {{ background-color: #fff3e0; color: #f57c00; }}
        .link-details {{ margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e9ecef; }}
        .link-list {{ font-size: 0.85rem; color: #6c757d; }}
        .link-item {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; padding: 0.25rem 0; }}
        .link-arrow {{ font-size: 0.75rem; color: #adb5bd; }}
        .link-target {{ color: #5a6fd8; text-decoration: none; flex: 1; }}
        .link-type-badge {{ font-size: 0.65rem; padding: 0.1rem 0.3rem; border-radius: 4px; background-color: #f8f9fa; color: #6c757d; }}
        .stats-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; }}
        .stat-label {{ font-size: 0.9rem; opacity: 0.9; }}
        .footer {{ margin-top: 3rem; padding: 1.5rem; text-align: center; color: #6c757d; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        {enhanced_css}
    </style>
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <div class="sidebar-header">
                <h3>Architecture Layers</h3>
            </div>
            <nav class="sidebar-nav">
                <a href="#overview" class="nav-item active">
                    <span class="nav-icon">📊</span>
                    <span class="nav-text">Overview</span>
                </a>
                {nav_items}
            </nav>
        </aside>

        <main class="main-content">
            <header class="header">
                <h1>Architecture Documentation Dashboard</h1>
                <div class="subtitle">Links & Verification Results from {project_dir_name}</div>
            </header>

            <section id="overview" class="layer-section">
                <div class="stats-container">
                    <div class="stat-card">
                        <div class="stat-value">{total_documents}</div>
                        <div class="stat-label">Total Documents</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                        <div class="stat-value">{total_links}</div>
                        <div class="stat-label">Total Links</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                        <div class="stat-value">{total_verifications}</div>
                        <div class="stat-label">Verifications Run</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                        <div class="stat-value">{passed_verifications}/{total_verifications}</div>
                        <div class="stat-label">Tests Passing</div>
                    </div>
                </div>
            </section>

            {layer_sections}

            <div class="footer">
                <p>Enhanced Architecture Dashboard with Verification Results</p>
                <p>Generated: {timestamp}</p>
                <p>Source: {project_dir}</p>
            </div>
        </main>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const navItems = document.querySelectorAll('.nav-item');
            const sections = document.querySelectorAll('section[id]');

            navItems.forEach(item => {{
                item.addEventListener('click', function(e) {{
                    e.preventDefault();
                    navItems.forEach(nav => nav.classList.remove('active'));
                    this.classList.add('active');
                    
                    const targetId = this.getAttribute('href')?.substring(1);
                    if (targetId) {{
                        const targetSection = document.getElementById(targetId);
                        if (targetSection) {{
                            targetSection.scrollIntoView({{ behavior: 'smooth' }});
                        }}
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>'''
        
        return html_template.format(
            nav_items=''.join(nav_items),
            layer_sections=''.join(layer_sections),
            total_documents=stats['total_documents'],
            total_links=stats['total_links'],
            total_verifications=stats['total_verifications'],
            passed_verifications=stats['passed_verifications'],
            project_dir_name=self.project_dir.name,
            project_dir=self.project_dir,
            timestamp=datetime.now().isoformat(),
            enhanced_css=enhanced_css
        )
    
    def save_dashboard(self) -> None:
        """Save the generated dashboard to file."""
        html_content = self.generate_dashboard()
        
        # Ensure output directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Enhanced dashboard generated successfully: {self.output_file}")
    
    def run(self) -> int:
        """Main execution method."""
        try:
            print(f"Loading links from: {self.project_dir}")
            self.load_all_links()
            
            print(f"Loading verification results from: {self.project_dir / 'dashboard' / 'categories'}")
            self.load_verification_results()
            
            if not any(self.all_documents.values()):
                print("No documents found in any layer directories.")
                return 1
            
            print(f"Found {len(self.verification_results)} verification results")
            print(f"Found {len(self.verification_charts)} verification charts")
            
            self.save_dashboard()
            return 0
            
        except Exception as e:
            print(f"Error generating dashboard: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Generate an enhanced HTML dashboard with verification results'
    )
    parser.add_argument(
        'project_dir',
        nargs='?',
        default='.',
        help='Path to the project root directory (default: current directory)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output HTML file path (default: <project>/dashboard/enhanced-dashboard.html)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Also output complete data as JSON'
    )
    
    args = parser.parse_args()
    
    project_dir = Path(args.project_dir)
    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}", file=sys.stderr)
        return 1
    
    output_file = Path(args.output) if args.output else project_dir / 'dashboard' / 'enhanced-dashboard.html'
    
    generator = EnhancedDashboardGenerator(project_dir, output_file)
    exit_code = generator.run()
    
    if args.json and exit_code == 0:
        # Export all data as JSON
        stats = generator.calculate_stats()
        json_output = {
            'stats': stats,
            'documents': {layer: list(docs) for layer, docs in generator.all_documents.items()},
            'links': {source: list(targets) for source, targets in generator.link_graph.items()},
            'verification_results': generator.verification_results,
            'verification_charts': generator.verification_charts,
            'document_metadata': generator.document_metadata
        }
        
        json_file = output_file.with_suffix('.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, default=str)
        print(f"JSON data saved to: {json_file}")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
