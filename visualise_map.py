#!/usr/bin/env python3
"""
Visualise Map Tool (Autocomplete Search)
Generates an interactive HTML Dashboard for Markdown dependencies.
Features:
- Clean labels
- Category Filtering
- Robust "Focus Path" button
- Dynamic header colouring
- Search with Autocomplete/Suggestions
"""

import argparse
import json
import sys
import yaml
from pathlib import Path
from collections import defaultdict

try:
    from markdown_it import MarkdownIt
except ImportError:
    print("ERROR: markdown-it-py not installed. Run: pip install markdown-it-py")
    sys.exit(1)

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Architecture Dependency Graph</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow: hidden; }
        #container { display: flex; height: 100vh; }
        
        #graph-container { flex: 2; background: #f0f2f5; border-right: 1px solid #ddd; position: relative; }
        #content-container { flex: 1; overflow-y: auto; background: white; display: flex; flex-direction: column; min-width: 400px; box-shadow: -2px 0 5px rgba(0,0,0,0.05); }
        
        /* UI Controls */
        #controls { position: absolute; top: 20px; right: 20px; z-index: 10; display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
        .control-row { display: flex; gap: 10px; }
        
        .btn { padding: 8px 15px; background: #34495e; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9rem; box-shadow: 0 2px 4px rgba(0,0,0,0.2); transition: background 0.2s; }
        .btn:hover { background: #2c3e50; }
        .btn.active { background: #3498db; }
        .btn:disabled { background: #bdc3c7; cursor: not-allowed; opacity: 0.8; }
        
        select { padding: 8px; border-radius: 4px; border: 1px solid #ccc; font-family: inherit; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        
        #status-msg { font-size: 0.85rem; color: #7f8c8d; background: rgba(255,255,255,0.9); padding: 4px 8px; border-radius: 4px; display: none; }

        /* Search */
        #search-box { position: absolute; top: 20px; left: 20px; z-index: 10; background: white; padding: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; gap: 5px; }
        #search-input { padding: 5px 10px; border: 1px solid #ddd; border-radius: 4px; outline: none; width: 200px; font-family: inherit; }
        #search-btn { padding: 5px 10px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }

        /* Content Panel */
        .panel-header { padding: 15px 20px; background: #2c3e50; color: white; transition: background-color 0.3s ease; }
        .panel-header h2 { margin: 0; font-size: 1.2rem; text-shadow: 0 1px 2px rgba(0,0,0,0.2); }
        .badge { background: rgba(0,0,0,0.2); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-right: 5px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        #md-content { padding: 30px; line-height: 1.6; color: #333; }
        #md-content h1 { border-bottom: 2px solid #eee; padding-bottom: 10px; color: #2c3e50; font-size: 1.8em; margin-top: 0; }
        #md-content h2 { color: #34495e; margin-top: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        #md-content a { color: #3498db; text-decoration: none; }
        #md-content pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; border: 1px solid #eee; }
        #md-content code { background: #f8f9fa; padding: 2px 5px; border-radius: 3px; font-family: Consolas, monospace; color: #c7254e; }
        
        /* Legend */
        #legend { position: absolute; bottom: 20px; left: 20px; background: rgba(255,255,255,0.95); padding: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); font-size: 0.85rem; pointer-events: none; }
        .legend-item { display: flex; align-items: center; margin-bottom: 5px; }
        .legend-color { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
    </style>
</head>
<body>

<div id="container">
    <div id="graph-container">
        <div id="search-box">
            <input type="text" id="search-input" list="search-suggestions" placeholder="Find document...">
            <datalist id="search-suggestions"></datalist>
            <button id="search-btn">Search</button>
        </div>
        <div id="controls">
            <div id="status-msg"></div>
            <div class="control-row">
                <select id="category-filter">
                    <option value="all">All Classifications</option>
                </select>
            </div>
            <div class="control-row">
                <button id="focus-btn" class="btn">Focus Path</button>
                <button id="cluster-btn" class="btn">Toggle Clusters</button>
                <button id="reset-btn" class="btn">Reset View</button>
            </div>
        </div>
        <div id="mynetwork" style="width: 100%; height: 100%;"></div>
        <div id="legend"></div>
    </div>
    
    <div id="content-container">
        <div class="panel-header">
            <h2 id="doc-title">Document Viewer</h2>
            <div id="badge-container">
                <span id="doc-category" class="badge">Select a node</span>
            </div>
        </div>
        <div id="md-content">
            <div style="text-align: center; color: #95a5a6; margin-top: 50px;">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
                <h3>Dependency Graph</h3>
                <p>1. <strong>Click</strong> a node to select it.<br>2. Click <strong>Focus Path</strong> to isolate its story.<br>3. Click <strong>Reset View</strong> to see all.</p>
            </div>
        </div>
    </div>
</div>

<script type="text/javascript">
    const nodesArray = __NODES_JSON__;
    const edgesArray = __EDGES_JSON__;
    const groupsConfig = __GROUPS_JSON__;

    const nodes = new vis.DataSet(nodesArray);
    const edges = new vis.DataSet(edgesArray);
    const container = document.getElementById('mynetwork');
    const data = { nodes: nodes, edges: edges };
    
    const options = {
        nodes: {
            shape: 'dot',
            size: 25,
            font: { size: 14, face: 'Segoe UI' },
            borderWidth: 2,
            shadow: true
        },
        edges: {
            width: 1,
            color: { color: '#bdc3c7', highlight: '#2c3e50', opacity: 1.0 },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
            smooth: { type: 'continuous' }
        },
        physics: {
            stabilization: false,
            barnesHut: { gravitationalConstant: -2000, springLength: 200, springConstant: 0.04 }
        },
        groups: groupsConfig,
        interaction: { hover: true, tooltipDelay: 200 }
    };

    const network = new vis.Network(container, data, options);
    let clustersActive = false;
    let focusMode = false;

    // --- Populate Search Suggestions ---
    const searchDatalist = document.getElementById('search-suggestions');
    // Sort alphabetically for better UX
    const sortedNodes = [...nodesArray].sort((a, b) => a.pure_label.localeCompare(b.pure_label));
    
    sortedNodes.forEach(node => {
        const option = document.createElement('option');
        option.value = node.pure_label;
        searchDatalist.appendChild(option);
    });

    // --- Dynamic UI Population ---
    const existingGroups = new Set(nodes.get().map(n => n.group));
    const legendEl = document.getElementById('legend');
    const filterSelect = document.getElementById('category-filter');
    const statusMsg = document.getElementById('status-msg');
    
    if (groupsConfig) {
        Object.keys(groupsConfig).forEach(group => {
            if (existingGroups.has(group)) {
                // Legend
                const item = document.createElement('div');
                item.className = 'legend-item';
                const colorBox = document.createElement('div');
                colorBox.className = 'legend-color';
                colorBox.style.backgroundColor = groupsConfig[group].color.background;
                colorBox.style.border = `1px solid ${groupsConfig[group].color.border}`;
                const text = document.createElement('span');
                text.innerText = group.charAt(0).toUpperCase() + group.slice(1);
                item.appendChild(colorBox);
                item.appendChild(text);
                legendEl.appendChild(item);

                // Dropdown
                const option = document.createElement('option');
                option.value = group;
                option.innerText = group.charAt(0).toUpperCase() + group.slice(1);
                filterSelect.appendChild(option);
            }
        });
    }

    // --- Filter Logic ---
    filterSelect.addEventListener('change', function() {
        // Full Reset before filtering
        resetView(true); 
        
        const category = this.value;
        const updates = [];
        let count = 0;
        
        nodes.get().forEach(node => {
            if (category === 'all' || node.group === category) {
                updates.push({id: node.id, hidden: false});
                count++;
            } else {
                updates.push({id: node.id, hidden: true});
            }
        });
        nodes.update(updates);
        network.fit();
        
        if (category !== 'all') updateStatus(`Showing ${count} nodes in '${category}'`);
    });

    // --- Interactions ---
    network.on("click", function (params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            if (network.isCluster(nodeId)) return;
            
            const nodeData = nodes.get(nodeId);
            showContent(nodeData);
            
            // Only dim if we are NOT in focus mode (Focus mode handles its own visibility)
            if (!focusMode) {
                highlightNeighbourhood(nodeId);
            }
        } else {
            // Clicked empty space
            if (!focusMode) resetHighlight();
        }
    });

    // --- Core Logic: Path Focus ---
    document.getElementById('focus-btn').addEventListener('click', function() {
        const selectedIds = network.getSelectedNodes();
        if (selectedIds.length === 0) {
            alert("Please select a node first to focus on its path.");
            return;
        }
        const rootId = selectedIds[0];
        if (network.isCluster(rootId)) {
             alert("Cannot focus on a cluster. Please open it first.");
             return;
        }
        activatePathFocus(rootId);
    });

    function activatePathFocus(rootId) {
        resetHighlight();
        focusMode = true;
        document.getElementById('focus-btn').classList.add('active');
        
        const visibleNodeIds = new Set();
        visibleNodeIds.add(rootId);
        
        findAllConnected(rootId, 'from', visibleNodeIds); // Children
        findAllConnected(rootId, 'to', visibleNodeIds);   // Parents

        const updates = [];
        nodes.get().forEach(n => {
            if (visibleNodeIds.has(n.id)) {
                updates.push({
                    id: n.id, 
                    hidden: false, 
                    color: undefined, 
                    label: n.pure_label
                });
            } else {
                updates.push({id: n.id, hidden: true});
            }
        });
        
        nodes.update(updates);
        network.fit();
        
        updateStatus(`Path Focused: ${visibleNodeIds.size} nodes visible`);
    }

    function findAllConnected(startId, directionField, resultSet) {
        const stack = [startId];
        while (stack.length > 0) {
            const currentId = stack.pop();
            const relevantEdges = edges.get({
                filter: function (item) { return item[directionField] === currentId; }
            });
            relevantEdges.forEach(edge => {
                const nextId = (directionField === 'from') ? edge.to : edge.from;
                if (!resultSet.has(nextId)) {
                    resultSet.add(nextId);
                    stack.push(nextId);
                }
            });
        }
    }

    // --- Highlight Neighbourhood (Dimming effect) ---
    function highlightNeighbourhood(selectedNodeId) {
        const connectedNodes = network.getConnectedNodes(selectedNodeId);
        const allNodes = nodes.get({ returnType: "Object" });
        
        for (let nodeId in allNodes) {
            if (!allNodes[nodeId].hidden) {
                allNodes[nodeId].color = 'rgba(200,200,200,0.5)';
                if (allNodes[nodeId].hiddenLabel === undefined) {
                    allNodes[nodeId].hiddenLabel = allNodes[nodeId].label;
                    allNodes[nodeId].label = undefined;
                }
            }
        }
        
        if (allNodes[selectedNodeId]) {
            allNodes[selectedNodeId].color = undefined; 
            allNodes[selectedNodeId].label = allNodes[selectedNodeId].hiddenLabel || allNodes[selectedNodeId].pure_label;
        }
        
        connectedNodes.forEach(nodeId => {
            if (allNodes[nodeId]) {
                allNodes[nodeId].color = undefined;
                allNodes[nodeId].label = allNodes[nodeId].hiddenLabel || allNodes[nodeId].pure_label;
            }
        });
        
        nodes.update(Object.values(allNodes));
    }

    function resetHighlight() {
        const allNodes = nodes.get();
        const updates = allNodes.map(n => ({
            id: n.id,
            color: undefined,
            label: n.pure_label,
            hiddenLabel: undefined
        }));
        nodes.update(updates);
    }
    
    function resetView(skipFilterReset = false) {
        focusMode = false;
        document.getElementById('focus-btn').classList.remove('active');
        if (!skipFilterReset) document.getElementById('category-filter').value = 'all';
        statusMsg.style.display = 'none';
        
        const allNodes = nodes.get();
        const updates = allNodes.map(n => ({
            id: n.id,
            hidden: false,
            color: undefined,
            label: n.pure_label
        }));
        nodes.update(updates);
        network.fit();
        
        // Reset header colour
        document.querySelector('.panel-header').style.backgroundColor = '#2c3e50';
        document.getElementById('doc-category').innerText = 'Select a node';
        document.getElementById('doc-title').innerText = 'Document Viewer';
    }

    function showContent(nodeData) {
        document.getElementById('doc-title').innerText = nodeData.pure_label; 
        document.getElementById('doc-category').innerText = nodeData.group || 'Group';
        
        // Dynamic Header Colour
        const header = document.querySelector('.panel-header');
        const groupStyle = groupsConfig[nodeData.group];
        
        if (groupStyle && groupStyle.color) {
            header.style.backgroundColor = groupStyle.color.background;
        } else {
            header.style.backgroundColor = '#2c3e50';
        }

        const contentDiv = document.getElementById('md-content');
        if (nodeData.content_html) contentDiv.innerHTML = nodeData.content_html;
        else contentDiv.innerHTML = "<p><em>Content not found or external link.</em></p>";
        document.getElementById('content-container').scrollTop = 0;
    }
    
    function updateStatus(text) {
        statusMsg.innerText = text;
        statusMsg.style.display = 'block';
    }

    // --- Buttons ---
    document.getElementById('cluster-btn').addEventListener('click', toggleClusters);
    function toggleClusters() {
        if (clustersActive) {
            const clusters = Object.keys(network.body.nodes).filter(id => network.isCluster(id));
            clusters.forEach(id => network.openCluster(id));
            clustersActive = false;
            document.getElementById('cluster-btn').classList.remove('active');
        } else {
            const groups = [...new Set(nodes.get().map(n => n.group))];
            groups.forEach(groupName => {
                const clusterOptions = {
                    joinCondition: function(nodeOptions) { return nodeOptions.group === groupName; },
                    clusterNodeProperties: {
                        id: 'cluster_' + groupName,
                        label: groupName.toUpperCase(),
                        color: groupsConfig[groupName]?.color?.background || '#999',
                        shape: 'circle',
                        size: 40,
                        font: { size: 18, color: 'white', face: 'Segoe UI' },
                        borderWidth: 3
                    }
                };
                network.cluster(clusterOptions);
            });
            clustersActive = true;
            document.getElementById('cluster-btn').classList.add('active');
        }
    }

    document.getElementById('search-btn').addEventListener('click', findNode);
    document.getElementById('search-input').addEventListener('keypress', (e) => { if(e.key === 'Enter') findNode() });
    
    // Auto-search on input selection
    document.getElementById('search-input').addEventListener('input', (e) => {
         const val = e.target.value;
         // Check if value matches exactly one of the options
         const match = nodes.get().find(n => n.pure_label === val);
         if (match) {
             findNode();
         }
    });

    document.getElementById('reset-btn').addEventListener('click', () => resetView());

    function findNode() {
        const query = document.getElementById('search-input').value.toLowerCase();
        if (!query) return;
        const found = nodes.get().find(n => n.pure_label.toLowerCase().includes(query));
        if (found) {
            if (found.hidden) resetView(); 
            network.selectNodes([found.id]);
            network.focus(found.id, { scale: 1.5, animation: true });
            highlightNeighbourhood(found.id);
            showContent(found);
        } else {
            alert('Document not found');
        }
    }
</script>
</body>
</html>
"""

class LinkCrawler:
    def __init__(self, root_dir: Path, start_dir: Path):
        self.root = root_dir.resolve()
        self.start_dir = start_dir.resolve()
        
        self.graph = defaultdict(list)
        self.reverse_graph = defaultdict(list)
        self.nodes_meta = {}
        self.visited_dirs = set()
        self.md_parser = MarkdownIt()
        
        self.groups = {
            'default': {'color': {'background': '#95a5a6', 'border': '#7f8c8d'}},
            'principles': {'color': {'background': '#3498db', 'border': '#2980b9'}}, 
            'rules': {'color': {'background': '#e74c3c', 'border': '#c0392b'}},      
            'verification': {'color': {'background': '#2ecc71', 'border': '#27ae60'}}, 
            'domains': {'color': {'background': '#f1c40f', 'border': '#f39c12'}},    
            'operations': {'color': {'background': '#9b59b6', 'border': '#8e44ad'}}, 
            'security': {'color': {'background': '#e67e22', 'border': '#d35400'}},   
            'external': {'color': {'background': '#34495e', 'border': '#2c3e50'}}
        }

    def _normalize_path(self, path: Path) -> str:
        try:
            rel = path.resolve().relative_to(self.root)
            return str(rel).replace('\\', '/')
        except ValueError:
            return str(path.resolve()).replace('\\', '/')

    def _get_category(self, path: Path) -> str:
        try:
            parent_name = path.parent.name.lower()
            if parent_name in self.groups:
                return parent_name
        except:
            pass
        return "default"

    def _read_links_yaml(self, directory: Path):
        links_file = directory / 'links.yaml'
        if not links_file.exists():
            return None
        try:
            with open(links_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except:
            return None

    def _resolve_link_path(self, source_dir: Path, link: str):
        try:
            clean_link = link.replace('\\', '/')
            target_path = (source_dir / clean_link).resolve()
            if not target_path.exists():
                return None
            return target_path, target_path.parent
        except:
            return None

    def _read_content(self, path: Path):
        if not path.exists():
            return "<h3>File not found</h3>"
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return self.md_parser.render(f.read())
        except Exception as e:
            return f"<h3>Error reading file</h3><p>{e}</p>"

    def walk(self, directory: Path):
        if directory in self.visited_dirs:
            return
        
        self.visited_dirs.add(directory)
        
        links_data = self._read_links_yaml(directory)
        if not links_data:
            return

        established_links = links_data.get('established_links', {})
        if not established_links:
            return

        for source_filename, targets in established_links.items():
            source_path = directory / source_filename
            source_id = self._normalize_path(source_path)
            
            if source_id not in self.nodes_meta:
                self.nodes_meta[source_id] = {
                    'path': source_path,
                    'group': self._get_category(source_path),
                    'content_html': self._read_content(source_path)
                }

            if not targets:
                continue

            for target_link in targets:
                resolved = self._resolve_link_path(directory, target_link)
                if not resolved:
                    continue
                
                target_path, target_dir = resolved
                target_id = self._normalize_path(target_path)

                if target_id not in self.nodes_meta:
                    self.nodes_meta[target_id] = {
                        'path': target_path,
                        'group': self._get_category(target_path),
                        'content_html': self._read_content(target_path)
                    }

                if target_id not in self.graph[source_id]:
                    self.graph[source_id].append(target_id)
                
                if source_id not in self.reverse_graph[target_id]:
                    self.reverse_graph[target_id].append(source_id)
                
                if target_dir != directory:
                    self.walk(target_dir)

    def generate(self, output_file: str):
        vis_nodes = []
        for node_id, meta in self.nodes_meta.items():
            # CLEAN LABEL: Just the filename
            label = meta['path'].name
            
            vis_nodes.append({
                'id': node_id,
                'pure_label': label,
                'label': label,
                'group': meta['group'],
                'content_html': meta['content_html'],
                'title': str(meta['path'])
            })

        vis_edges = []
        for source, targets in self.graph.items():
            for target in targets:
                vis_edges.append({'from': source, 'to': target})

        print(f"Generated Graph: {len(vis_nodes)} nodes, {len(vis_edges)} edges.")

        out = HTML_TEMPLATE.replace('__NODES_JSON__', json.dumps(vis_nodes))
        out = out.replace('__EDGES_JSON__', json.dumps(vis_edges))
        out = out.replace('__GROUPS_JSON__', json.dumps(self.groups))
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(out)
        print(f"Saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Visual Map Generator (Link Crawler)")
    parser.add_argument("directory", nargs='?', default=".", help="Directory to start crawling from")
    parser.add_argument("--output", "-o", default="map.html", help="Output file")
    
    args = parser.parse_args()
    
    root_path = Path.cwd().resolve()
    start_path = Path(args.directory).resolve()
    
    if not start_path.exists():
        print(f"Error: Directory {start_path} does not exist.")
        sys.exit(1)

    print(f"Crawling links starting from: {start_path}")
    
    crawler = LinkCrawler(root_path, start_path)
    crawler.walk(start_path)
    crawler.generate(args.output)

if __name__ == "__main__":
    main()
