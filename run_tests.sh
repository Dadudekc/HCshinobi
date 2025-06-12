#!/bin/bash

# Exit on error
set -e

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Function to check if virtual environment exists and create if needed
ensure_venv() {
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
}

# Function to activate virtual environment
activate_venv() {
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
}

# Function to install dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
    pip install -r requirements-test.txt
}

# Function to ensure __init__.py files exist in all necessary directories
ensure_init_files() {
    echo -e "${YELLOW}Ensuring __init__.py files exist in all necessary directories...${NC}"
    dirs=(
        "HCshinobi"
        "HCshinobi/core"
        "HCshinobi/cogs"
        "HCshinobi/utils"
        "tests"
    )
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            init_file="$dir/__init__.py"
            if [ ! -f "$init_file" ]; then
                echo -e "${GREEN}Creating $init_file${NC}"
                touch "$init_file"
            fi
        fi
    done
}

# Main execution
main() {
    # Get the absolute path of the workspace
    workspace_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo -e "${CYAN}Workspace path: $workspace_path${NC}"

    # Ensure virtual environment exists and is activated
    ensure_venv
    activate_venv

    # Install dependencies
    install_dependencies

    # Ensure __init__.py files exist
    ensure_init_files

    # Set PYTHONPATH
    export PYTHONPATH="$workspace_path"

    # Run pytest with coverage
    echo -e "${YELLOW}Running tests...${NC}"
    pytest --maxfail=5 -v

    echo -e "${GREEN}Tests completed successfully!${NC}"
}

# Run main function
main "$@" || {
    echo -e "${RED}Error: Test execution failed${NC}" >&2
    exit 1
} 