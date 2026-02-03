"""DAG visualization utilities using Graphviz."""
import yaml
from typing import Dict, List, Any


def load_workflow(path: str) -> Dict[str, Any]:
    """Load a workflow YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def workflow_to_dot(workflow: Dict[str, Any]) -> str:
    """Convert a workflow IR to Graphviz DOT format.

    Args:
        workflow: Parsed workflow dict with 'nodes' list

    Returns:
        DOT format string for Graphviz rendering
    """
    nodes: List[Dict[str, Any]] = workflow.get('nodes', [])

    lines = [
        'digraph workflow {',
        '    rankdir=TB;',
        '    node [shape=box, style="rounded,filled", fillcolor="#e8f4f8", fontname="Arial"];',
        '    edge [color="#666666"];',
        '',
    ]

    # Add nodes
    for node in nodes:
        node_id = node['id']
        action_ref = node.get('actionRef', 'unknown')
        # Shorten action ref for display
        short_action = action_ref.split('.')[-1] if '.' in action_ref else action_ref
        label = f"{node_id}\\n({short_action})"
        lines.append(f'    "{node_id}" [label="{label}"];')

    lines.append('')

    # Add edges
    for node in nodes:
        node_id = node['id']
        depends_on = node.get('dependsOn', [])
        for dep in depends_on:
            lines.append(f'    "{dep}" -> "{node_id}";')

    lines.append('}')
    return '\n'.join(lines)


def get_node_details(workflow: Dict[str, Any], node_id: str) -> Dict[str, Any]:
    """Get details for a specific node."""
    nodes = workflow.get('nodes', [])
    for node in nodes:
        if node['id'] == node_id:
            return node
    return {}
