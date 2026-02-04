"""Agentic Workflow Engine — Portfolio Demo.

A schema-driven workflow engine showcasing:
- DAG-based workflow orchestration
- Tool calling and LLM integration
- Production-grade error handling and retries
"""
import json
from pathlib import Path

import streamlit as st

from utils.dag_viz import load_workflow, workflow_to_dot
from utils.cache_manager import (
    get_preset_queries,
    load_cached_result,
)
from utils.executor import execute_workflow, ExecutionResult, NodeExecution


# --- Constants ---
ROOT = Path(__file__).parent
WORKFLOWS_DIR = ROOT / 'workflows'
REGISTRY_DIR = ROOT / 'registry'

WORKFLOW_INFO = {
    'arxiv_search': {
        'name': 'arXiv Search',
        'description': 'Search arXiv for academic papers and parse results',
        'icon': '📚',
    },
    'wiki_summary': {
        'name': 'Wikipedia Summary',
        'description': 'Search Wikipedia and extract article summaries',
        'icon': '📖',
    },
    'error_recovery': {
        'name': 'Error Recovery Demo',
        'description': 'Demonstrates retry logic and error handling',
        'icon': '🔄',
    },
}


def main():
    st.set_page_config(
        page_title="Agentic Workflow Engine",
        page_icon="⚡",
        layout="wide",
    )

    # --- Sidebar: Workflow Selection and DAG ---
    with st.sidebar:
        st.title("⚡ Workflow Engine")
        st.caption("Schema-driven orchestration")

        st.markdown("---")

        # Workflow selection
        workflow_options = list(WORKFLOW_INFO.keys())
        workflow_labels = [
            f"{WORKFLOW_INFO[w]['icon']} {WORKFLOW_INFO[w]['name']}"
            for w in workflow_options
        ]

        selected_idx = st.selectbox(
            "Select Workflow",
            range(len(workflow_options)),
            format_func=lambda i: workflow_labels[i],
            key="workflow_select"
        )
        selected_workflow = workflow_options[selected_idx]
        st.caption(WORKFLOW_INFO[selected_workflow]['description'])

        # Query selection
        presets = get_preset_queries(selected_workflow)
        query_options = presets + ["Custom (live only)"]

        selected_query_idx = st.selectbox(
            "Select Query",
            range(len(query_options)),
            format_func=lambda i: query_options[i],
            key="query_select"
        )

        if query_options[selected_query_idx] == "Custom (live only)":
            custom_query = st.text_input(
                "Enter custom query",
                key="custom_query"
            )
            st.caption("⚠️ Custom queries run live.")
            selected_query = custom_query
            is_custom = True
        else:
            selected_query = query_options[selected_query_idx]
            is_custom = False

        # Run button
        run_disabled = is_custom and not selected_query
        run_clicked = st.button("▶️ Run Workflow", disabled=run_disabled, type="primary", use_container_width=True)

        # Store selection in session state for main area
        st.session_state.selected_workflow = selected_workflow
        st.session_state.selected_query = selected_query
        st.session_state.is_custom = is_custom

        st.markdown("---")

        # DAG visualization in sidebar
        st.subheader("Workflow DAG")
        workflow_path = WORKFLOWS_DIR / f"{selected_workflow}.yaml"
        if workflow_path.exists():
            workflow = load_workflow(str(workflow_path))
            dot = workflow_to_dot(workflow)
            st.graphviz_chart(dot, use_container_width=True)
        else:
            st.warning("Workflow file not found")

    # --- Main Area: Tabs ---
    tab_run, tab_how, tab_arch = st.tabs([
        "🚀 Run Workflows",
        "🔍 How It Works",
        "🏗️ Architecture"
    ])

    with tab_run:
        render_run_workflows_tab(run_clicked)

    with tab_how:
        render_how_it_works_tab()

    with tab_arch:
        render_architecture_tab()


def render_run_workflows_tab(run_clicked: bool):
    """Render the main workflow execution tab."""

    st.header("Workflow Execution")

    # Show current selection
    selected_workflow = st.session_state.get('selected_workflow', 'arxiv_search')
    selected_query = st.session_state.get('selected_query', '')
    is_custom = st.session_state.get('is_custom', False)

    if selected_query:
        st.info(f"**Workflow:** {WORKFLOW_INFO[selected_workflow]['icon']} {WORKFLOW_INFO[selected_workflow]['name']}  \n**Query:** {selected_query}")
    else:
        st.info("Select a workflow and query from the sidebar, then click **Run Workflow**.")
        return

    # Execute if button was clicked
    if run_clicked:
        run_workflow_and_display(selected_workflow, selected_query, is_custom)

    # Display previous results if available
    elif st.session_state.get('execution_result'):
        display_execution_result(st.session_state.execution_result)


def run_workflow_and_display(workflow_name: str, query: str, is_custom: bool):
    """Execute workflow and display results."""

    # Initialize session state
    if 'execution_result' not in st.session_state:
        st.session_state.execution_result = None
    if 'execution_logs' not in st.session_state:
        st.session_state.execution_logs = []

    with st.spinner(f"Running {workflow_name}..."):
        # Try live execution
        result = execute_workflow(workflow_name, query, timeout_seconds=30)

        # If failed and not custom, try cache
        if not result.success and not is_custom:
            cached = load_cached_result(workflow_name, query)
            if cached:
                st.info("📦 Showing cached result (live execution failed)")
                st.session_state.execution_result = cached
                st.session_state.execution_logs = cached.get('logs', [])
                display_execution_result(cached)
                return

        # Store result
        st.session_state.execution_result = {
            'success': result.success,
            'logs': [vars(log) for log in result.logs],
            'node_outputs': result.node_outputs,
            'node_executions': [vars(ne) for ne in result.node_executions],
            'execution_time_ms': result.execution_time_ms,
            'error': result.error,
        }
        st.session_state.execution_logs = result.logs

        display_execution_result(st.session_state.execution_result)


def display_execution_result(result: dict):
    """Display execution result with node details."""

    # Status header
    if result.get('success'):
        st.success(f"✅ Completed in {result.get('execution_time_ms', 0)}ms")
    else:
        st.error(f"❌ Failed: {result.get('error', 'Unknown error')}")

    # Final Result - show the actual useful output first
    if result.get('success') and result.get('node_executions'):
        display_final_result(result['node_executions'])

    # Node execution details (collapsed by default now)
    if result.get('node_executions'):
        with st.expander("🔧 Node Execution Details", expanded=False):
            display_node_executions(result['node_executions'])

        # Summary metrics
        st.markdown("---")
        total_nodes = len(result['node_executions'])
        successful = sum(1 for ne in result['node_executions'] if ne.get('status') == 'success')
        total_time = result.get('execution_time_ms', 0)

        col1, col2, col3 = st.columns(3)
        col1.metric("Nodes Executed", total_nodes)
        col2.metric("Successful", f"{successful}/{total_nodes}")
        col3.metric("Total Time", f"{total_time}ms")

    # Raw execution log
    if result.get('logs'):
        with st.expander("📋 Raw Execution Log", expanded=False):
            for log in result['logs']:
                if isinstance(log, dict):
                    icon = {'info': 'ℹ️', 'success': '✅', 'error': '❌', 'running': '▶️'}.get(log.get('level', ''), '•')
                    st.text(f"[{log.get('timestamp', '')}] {icon} {log.get('message', '')}")


def display_final_result(node_executions):
    """Display the final workflow result in a user-friendly format."""
    if not node_executions:
        return

    # Get the last node's output
    last_node = node_executions[-1]
    output = last_node.get('output_data') if isinstance(last_node, dict) else getattr(last_node, 'output_data', None)
    node_id = last_node.get('node_id', 'result') if isinstance(last_node, dict) else getattr(last_node, 'node_id', 'result')

    if not output:
        return

    st.markdown("### 📄 Result")

    # Parse if it's a string
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            pass

    # Handle truncated data
    if isinstance(output, dict) and output.get('_truncated'):
        sample = output.get('_sample', output.get('_preview', {}))
        if sample:
            output = sample

    # Extract the actual result value
    result_value = None
    if isinstance(output, dict):
        # Common result key patterns
        for key in ['result', 'text', 'content', 'extract', 'summary', 'data', 'json']:
            if key in output:
                result_value = output[key]
                break
        if result_value is None:
            result_value = output
    else:
        result_value = output

    # Handle nested truncated data
    if isinstance(result_value, dict) and result_value.get('_truncated'):
        sample = result_value.get('_sample', result_value.get('_preview', {}))
        if sample:
            result_value = sample

    # Display based on content type
    if isinstance(result_value, str):
        # Text content - display in a nice box
        if len(result_value) > 100:
            st.markdown(f"""
<div style="background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4;">
{result_value}
</div>
""", unsafe_allow_html=True)
        else:
            st.info(result_value)

    elif isinstance(result_value, list):
        # List of items - display as cards or bullets
        if len(result_value) > 0:
            st.markdown(f"**Found {len(result_value)} items:**")
            for i, item in enumerate(result_value[:10]):  # Show first 10
                if isinstance(item, dict):
                    # Try to extract title/name
                    title = item.get('title') or item.get('name') or item.get('key') or f"Item {i+1}"
                    with st.expander(f"**{i+1}.** {title}"):
                        st.json(item)
                else:
                    st.markdown(f"- {item}")
            if len(result_value) > 10:
                st.caption(f"... and {len(result_value) - 10} more items")

    elif isinstance(result_value, dict):
        # Check if it's arXiv/feed data with entries
        if 'feed' in result_value:
            display_arxiv_results(result_value)
        elif 'entry' in result_value:
            display_arxiv_results({'feed': result_value})
        else:
            # Generic dict - show as expandable JSON
            with st.expander("View full result", expanded=True):
                st.json(result_value)
    else:
        st.write(result_value)


def display_arxiv_results(data):
    """Display arXiv search results in a nice format."""
    try:
        feed = data.get('feed', data)
        entries = feed.get('entry', [])

        # Ensure entries is a list
        if isinstance(entries, dict):
            entries = [entries]

        if not entries:
            st.warning("No papers found")
            return

        st.markdown(f"**Found {len(entries)} papers:**")

        for i, entry in enumerate(entries[:10]):
            title = entry.get('title', 'Untitled')
            if isinstance(title, dict):
                title = title.get('#text', str(title))

            # Clean up title (remove newlines)
            title = ' '.join(title.split())

            summary = entry.get('summary', '')
            if isinstance(summary, dict):
                summary = summary.get('#text', str(summary))
            summary = ' '.join(summary.split())[:300]

            authors = entry.get('author', [])
            if isinstance(authors, dict):
                authors = [authors]
            author_names = []
            for a in authors[:3]:
                name = a.get('name', '') if isinstance(a, dict) else str(a)
                if name:
                    author_names.append(name)
            author_str = ', '.join(author_names)
            if len(authors) > 3:
                author_str += f" +{len(authors)-3} more"

            link = entry.get('id', '')
            if isinstance(link, dict):
                link = link.get('#text', '')

            with st.expander(f"**{i+1}.** {title}"):
                if author_str:
                    st.caption(f"👥 {author_str}")
                if summary:
                    st.markdown(summary + "...")
                if link:
                    st.markdown(f"[📄 View on arXiv]({link})")

    except Exception as e:
        st.error(f"Error displaying results: {e}")
        st.json(data)


def parse_json_safe(data):
    """Parse data into a JSON-displayable format.

    Handles strings that might be JSON, truncated strings, etc.
    Always returns something st.json() can display nicely.
    """
    if data is None:
        return None

    # If it's already a dict or list, return as-is
    if isinstance(data, (dict, list)):
        return data

    # If it's a string, try to parse it as JSON
    if isinstance(data, str):
        # Check if it's a truncated string (ends with "... (X chars total)")
        if "... (" in data and " chars total)" in data:
            # Try to parse the non-truncated part
            truncated_part = data.split("... (")[0]
            try:
                # Won't work for truncated JSON, but try anyway
                return json.loads(truncated_part)
            except (json.JSONDecodeError, ValueError):
                # Return as a structured object showing it's truncated
                return {"_truncated": True, "_preview": truncated_part[:200] + "...", "_note": "Data truncated for display"}

        # Try to parse as JSON
        try:
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            # Return as a simple value
            return {"_value": data}

    # For other types, wrap in a dict
    return {"_value": str(data)}


def display_node_executions(node_executions):
    """Display rich node execution details."""
    for i, ne in enumerate(node_executions):
        # Handle both NodeExecution objects and dicts
        if hasattr(ne, 'node_id'):
            node_id = ne.node_id
            action = ne.action
            status = ne.status
            duration_ms = ne.duration_ms
            input_data = ne.input_data
            output_data = ne.output_data
            error = ne.error
        else:
            node_id = ne.get('node_id', 'unknown')
            action = ne.get('action', '')
            status = ne.get('status', 'unknown')
            duration_ms = ne.get('duration_ms', 0)
            input_data = ne.get('input_data')
            output_data = ne.get('output_data')
            error = ne.get('error')

        # Status icon
        if status == 'success':
            icon = '✅'
        elif status == 'error':
            icon = '❌'
        else:
            icon = '▶️'

        # Node header with metrics
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.markdown(f"**{icon} {node_id}**")
        with col2:
            st.caption(f"`{action}`")
        with col3:
            st.caption(f"{duration_ms}ms")

        # Expandable details
        with st.expander(f"Details for {node_id}", expanded=(status == 'error')):
            if error:
                st.error(f"**Error:** {error}")

            tab_in, tab_out = st.tabs(["📥 Input", "📤 Output"])

            with tab_in:
                if input_data:
                    parsed = parse_json_safe(input_data)
                    if parsed:
                        st.json(parsed)
                    else:
                        st.caption("No input data")
                else:
                    st.caption("No input data captured")

            with tab_out:
                if output_data:
                    parsed = parse_json_safe(output_data)
                    if parsed:
                        st.json(parsed)
                    else:
                        st.caption("No output data")
                else:
                    st.caption("No output data captured")

        # Visual separator between nodes (except last)
        if i < len(node_executions) - 1:
            st.markdown("<div style='text-align: center; color: #666;'>⬇️</div>", unsafe_allow_html=True)


def render_how_it_works_tab():
    """Render the execution flow explanation tab."""
    st.header("How It Works")

    st.markdown("""
    This workflow engine executes **DAG-based workflows** where each node represents an action:

    1. **Workflow Definition** - YAML files define nodes, their actions, inputs, and dependencies
    2. **Topological Sort** - Nodes are ordered based on their dependencies
    3. **Sequential Execution** - Each node runs in order, with outputs passed to dependent nodes
    4. **Error Handling** - Configurable retries with exponential backoff

    ### Execution Flow
    """)

    result = st.session_state.get('execution_result', {})

    if result.get('node_executions'):
        display_node_executions(result['node_executions'])

        # Summary
        st.markdown("---")
        st.markdown("### Execution Summary")
        total_nodes = len(result['node_executions'])
        successful = sum(1 for ne in result['node_executions'] if ne.get('status') == 'success')
        total_time = result.get('execution_time_ms', 0)

        col1, col2, col3 = st.columns(3)
        col1.metric("Nodes Executed", total_nodes)
        col2.metric("Successful", f"{successful}/{total_nodes}")
        col3.metric("Total Time", f"{total_time}ms")
    else:
        st.info("👆 Run a workflow first to see execution details here.")


def render_architecture_tab():
    """Render the architecture introspection tab."""
    st.header("Architecture")

    st.markdown("### Action Registry")
    st.markdown("Available actions in this workflow engine:")

    # List all registry files
    registry_files = sorted(REGISTRY_DIR.glob('*.json'))

    for reg_file in registry_files:
        action_name = reg_file.stem.replace('.v1', '').replace('_', '.')

        with st.expander(f"🔧 {action_name}"):
            try:
                with open(reg_file, 'r', encoding='utf-8') as f:
                    schema = json.load(f)

                # Navigate nested structure: versions -> action -> version
                input_schema = {}
                output_schema = {}
                title = action_name

                versions = schema.get('versions', {})
                for action_key, action_versions in versions.items():
                    for version_key, version_data in action_versions.items():
                        title = version_data.get('title', action_name)
                        input_schema = version_data.get('inputSchema', {})
                        output_schema = version_data.get('outputSchema', {})
                        break  # Use first version found
                    break  # Use first action found

                st.markdown(f"**Title:** {title}")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Input Schema:**")
                    st.json(input_schema)
                with col2:
                    st.markdown("**Output Schema:**")
                    st.json(output_schema)
            except Exception as e:
                st.error(f"Error loading schema: {e}")

    st.markdown("---")
    st.markdown("### Workflow Inspector")

    workflow_files = sorted(WORKFLOWS_DIR.glob('*.yaml'))
    workflow_names = [f.stem for f in workflow_files]

    if workflow_names:
        selected = st.selectbox("Select workflow to inspect", workflow_names, key="arch_workflow_select")
        workflow_path = WORKFLOWS_DIR / f"{selected}.yaml"

        with st.expander("📄 Raw YAML", expanded=False):
            with open(workflow_path, 'r', encoding='utf-8') as f:
                st.code(f.read(), language='yaml')

        with st.expander("🔍 Parsed IR (JSON)", expanded=False):
            workflow = load_workflow(str(workflow_path))
            st.json(workflow)


if __name__ == "__main__":
    main()
