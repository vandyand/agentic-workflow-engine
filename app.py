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

    st.title("⚡ Agentic Workflow Engine")
    st.caption("Schema-driven workflow orchestration for AI applications")

    # --- Tabs ---
    tab_run, tab_how, tab_arch = st.tabs([
        "🚀 Run Workflows",
        "🔍 How It Works",
        "🏗️ Architecture"
    ])

    with tab_run:
        render_run_workflows_tab()

    with tab_how:
        render_how_it_works_tab()

    with tab_arch:
        render_architecture_tab()


def render_run_workflows_tab():
    """Render the main workflow execution tab."""
    col1, col2 = st.columns([1, 1])

    with col1:
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
            st.caption("⚠️ Custom queries run live and may take longer.")
            selected_query = custom_query
            is_custom = True
        else:
            selected_query = query_options[selected_query_idx]
            is_custom = False

        # Run button
        run_disabled = is_custom and not selected_query
        if st.button("▶️ Run Workflow", disabled=run_disabled, type="primary"):
            run_workflow_and_display(selected_workflow, selected_query, is_custom)

    with col2:
        # DAG visualization
        st.subheader("Workflow DAG")
        workflow_path = WORKFLOWS_DIR / f"{selected_workflow}.yaml"
        if workflow_path.exists():
            workflow = load_workflow(str(workflow_path))
            dot = workflow_to_dot(workflow)
            st.graphviz_chart(dot)
        else:
            st.warning("Workflow file not found")


def run_workflow_and_display(workflow_name: str, query: str, is_custom: bool):
    """Execute workflow and display results."""

    # Store in session state for How It Works tab
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
                display_cached_result(cached)
                return

        # Store result
        st.session_state.execution_result = {
            'success': result.success,
            'logs': [vars(log) for log in result.logs],
            'node_outputs': result.node_outputs,
            'node_executions': [vars(ne) for ne in result.node_executions],
            'execution_time_ms': result.execution_time_ms,
        }
        st.session_state.execution_logs = result.logs

        # Display result header
        if result.success:
            st.success(f"✅ Completed in {result.execution_time_ms}ms")
        else:
            st.error(f"❌ Failed: {result.error}")

        # Show node-by-node execution
        if result.node_executions:
            st.markdown("### Node Execution Details")
            display_node_executions(result.node_executions)

        # Show compact log
        with st.expander("📋 Raw Execution Log", expanded=False):
            for log in result.logs:
                icon = {'info': 'ℹ️', 'success': '✅', 'error': '❌', 'running': '▶️'}.get(log.level, '•')
                st.text(f"[{log.timestamp}] {icon} {log.message}")


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

        # Status icon and color
        if status == 'success':
            icon = '✅'
            border_color = '#28a745'
        elif status == 'error':
            icon = '❌'
            border_color = '#dc3545'
        else:
            icon = '▶️'
            border_color = '#6c757d'

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
                    if isinstance(input_data, str) and len(input_data) > 100:
                        st.code(input_data, language='json')
                    else:
                        st.json(input_data)
                else:
                    st.caption("No input data captured")

            with tab_out:
                if output_data:
                    if isinstance(output_data, str) and len(output_data) > 100:
                        st.code(output_data, language='json')
                    else:
                        st.json(output_data)
                else:
                    st.caption("No output data captured")

        # Visual separator between nodes (except last)
        if i < len(node_executions) - 1:
            st.markdown("<div style='text-align: center; color: #666;'>⬇️</div>", unsafe_allow_html=True)


def display_cached_result(cached: dict):
    """Display a cached result."""
    st.success(f"✅ Cached result from {cached.get('timestamp', 'unknown')}")

    with st.expander("Execution Log", expanded=True):
        for log in cached.get('logs', []):
            if isinstance(log, dict):
                icon = {'info': 'ℹ️', 'success': '✅', 'error': '❌', 'running': '▶️'}.get(log.get('level', ''), '•')
                st.text(f"[{log.get('timestamp', '')}] {icon} {log.get('message', '')}")

    if cached.get('node_outputs'):
        with st.expander("Node Outputs", expanded=False):
            st.json(cached['node_outputs'])


def render_how_it_works_tab():
    """Render the execution log viewer tab."""
    st.subheader("Execution Flow Viewer")
    st.markdown(
        "This tab shows the execution flow when you run a workflow. "
        "Each node displays its inputs, outputs, and timing."
    )

    result = st.session_state.get('execution_result', {})

    if result.get('node_executions'):
        st.markdown("---")
        st.markdown("### Node-by-Node Execution")
        display_node_executions(result['node_executions'])

        # Summary metrics
        st.markdown("---")
        st.markdown("### Execution Summary")
        total_nodes = len(result['node_executions'])
        successful = sum(1 for ne in result['node_executions'] if ne.get('status') == 'success')
        total_time = result.get('execution_time_ms', 0)

        col1, col2, col3 = st.columns(3)
        col1.metric("Nodes Executed", total_nodes)
        col2.metric("Successful", f"{successful}/{total_nodes}")
        col3.metric("Total Time", f"{total_time}ms")

    elif st.session_state.get('execution_logs'):
        # Fallback to old log format
        logs = st.session_state.execution_logs
        st.markdown("---")
        for log in logs:
            if hasattr(log, 'level'):
                level = log.level
                timestamp = log.timestamp
                message = log.message
            else:
                level = log.get('level', 'info')
                timestamp = log.get('timestamp', '')
                message = log.get('message', '')

            icon = {'info': 'ℹ️', 'success': '✅', 'error': '❌', 'running': '▶️'}.get(level, '•')

            if level == 'success':
                st.success(f"[{timestamp}] {message}")
            elif level == 'error':
                st.error(f"[{timestamp}] {message}")
            else:
                st.info(f"[{timestamp}] {icon} {message}")

        if result.get('node_outputs'):
            st.subheader("Node Outputs")
            for node_id, output in result['node_outputs'].items():
                with st.expander(f"📦 {node_id}"):
                    st.json(output)
    else:
        st.info("👆 Run a workflow first to see execution details here.")


def render_architecture_tab():
    """Render the architecture introspection tab."""
    st.subheader("Action Registry")
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
    st.subheader("Workflow Inspector")

    workflow_files = sorted(WORKFLOWS_DIR.glob('*.yaml'))
    workflow_names = [f.stem for f in workflow_files]

    if workflow_names:
        selected = st.selectbox("Select workflow to inspect", workflow_names)
        workflow_path = WORKFLOWS_DIR / f"{selected}.yaml"

        with st.expander("📄 Raw YAML", expanded=False):
            with open(workflow_path, 'r', encoding='utf-8') as f:
                st.code(f.read(), language='yaml')

        with st.expander("🔍 Parsed IR (JSON)", expanded=False):
            workflow = load_workflow(str(workflow_path))
            st.json(workflow)


if __name__ == "__main__":
    main()
