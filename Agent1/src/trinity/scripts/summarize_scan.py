import logging
from src.core.project_scanner import ProjectScanner

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    scanner = ProjectScanner(project_root='.')
    
    # Load the existing cache
    cached_data = scanner.load_cache()
    
    if not cached_data or not scanner.cache_path.exists():
        print(f"Could not load analysis cache from {scanner.cache_path}. Run the scan first.")
    else:
        # Get and print the summary
        summary = scanner.get_analysis_summary()
        print("--- Project Analysis Summary (Post Script Move) ---")
        print(summary)
        print("-------------------------------------------------") 