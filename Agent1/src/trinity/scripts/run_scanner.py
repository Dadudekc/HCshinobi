import logging
from src.core.project_scanner import ProjectScanner

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    # Use the updated scanner with default exclusions and large file limit
    scanner = ProjectScanner(project_root='.') 
    analysis_results = scanner.scan_project(max_files=10000) # Use large limit
    
    if analysis_results:
        print(f"Project scan completed successfully. Analyzed {len(analysis_results.get('files', []))} files.")
        print(f"Analysis saved to {scanner.cache_path}")
    else:
        print("Project scan failed or produced no results.") 