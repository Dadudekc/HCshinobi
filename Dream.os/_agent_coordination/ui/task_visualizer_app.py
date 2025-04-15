import streamlit as st
import pandas as pd
import json
from pathlib import Path
import time
import logging
import sys

# Configure logging for the visualizer
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TaskVisualizerApp")

# --- Import Task Utils --- 
# Add project root to path to find _agent_coordination
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from _agent_coordination.task_utils import read_tasks
    logger.info("Successfully imported task_utils.")
except ImportError as e:
    logger.error(f"Failed to import task_utils: {e}. Visualizer will not function properly.")
    # Define a dummy function if import fails
    def read_tasks(*args, **kwargs):
        st.error(f"Error importing task utilities: {e}. Cannot read tasks.")
        return []

# --- Configuration ---
TASK_LIST_PATH = project_root / "task_list.json"
REFRESH_INTERVAL_SECONDS = 5 # How often to refresh the data

def load_task_data(file_path: Path) -> pd.DataFrame:
    """Loads task data from task_list.json into a Pandas DataFrame."""
    tasks = read_tasks(file_path)
    if not tasks:
        # Return empty dataframe with expected columns if file is empty or read fails
        return pd.DataFrame(columns=[
            'task_id', 'status', 'task_type', 'action', 'target_agent', 
            'timestamp_created', 'timestamp_updated', 'result_summary', 'error_message', 'params'
        ])
        
    try:
        # Convert list of dicts to DataFrame
        df = pd.DataFrame(tasks)
        # Ensure all expected columns exist, fill missing with None or default
        expected_cols = [
            'task_id', 'status', 'task_type', 'action', 'target_agent', 
            'timestamp_created', 'timestamp_updated', 'result_summary', 'error_message', 'params'
        ]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        # Select and order columns for display
        display_cols = [
            'task_id', 'status', 'task_type', 'action', 'target_agent', 
            'timestamp_created', 'timestamp_updated', 'result_summary', 'error_message'
            # Optionally add 'params' back if needed, but it can be large
        ]
        df_display = df[display_cols]
        
        # Basic type conversion/handling for display
        df_display['timestamp_created'] = pd.to_datetime(df_display['timestamp_created'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        df_display['timestamp_updated'] = pd.to_datetime(df_display['timestamp_updated'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        df_display = df_display.fillna('N/A') # Replace NaNs for display
        
        return df_display.sort_values(by='timestamp_created', ascending=False) # Show newest first
    except Exception as e:
        logger.error(f"Error processing task data into DataFrame: {e}", exc_info=True)
        st.error(f"Error processing task data: {e}")
        # Return empty dataframe on processing error
        return pd.DataFrame(columns=[
            'task_id', 'status', 'task_type', 'action', 'target_agent', 
            'timestamp_created', 'timestamp_updated', 'result_summary', 'error_message'
        ])

# --- Streamlit App Layout ---
st.set_page_config(page_title="Dream.OS Task Visualizer", layout="wide")

st.title("Dream.OS Task Visualizer")
st.caption(f"Monitoring task list: {TASK_LIST_PATH}")

# Placeholder for the data display
data_placeholder = st.empty()

# --- Main Loop for Refreshing Data ---
while True:
    try:
        logger.debug("Loading task data...")
        df_tasks = load_task_data(TASK_LIST_PATH)
        
        # Update the placeholder with the new data
        with data_placeholder.container():
            st.subheader("Current Tasks")
            st.dataframe(df_tasks, use_container_width=True)
            
            st.caption(f"Last refreshed: {time.strftime('%Y-%m-%d %H:%M:%S')}. Refreshes every {REFRESH_INTERVAL_SECONDS} seconds.")
            
    except Exception as e:
        logger.error(f"Error during data refresh loop: {e}", exc_info=True)
        with data_placeholder.container():
             st.error(f"An error occurred during refresh: {e}")

    # Wait for the next refresh cycle
    time.sleep(REFRESH_INTERVAL_SECONDS)
    # Rerun is implicit in Streamlit's loop when run as a script,
    # but for long-running loops, manual rerun can sometimes be needed
    # st.experimental_rerun() # Use if needed, might cause full page reload 