def add_proposal(
    category: str,
    title: str,
    context: str,
    current_behavior: str,
    proposed_change: str,
    impact: str,
    implementation_notes: str = "",
    priority: int = 4
) -> bool:
    """
    Adds a new proposal to the proposal bank (rulebook_update_proposals.md).
    
    Args:
        category: One of ['ENHANCEMENT', 'BUG', 'REFACTOR', 'OPTIMIZATION', 'SECURITY', 'DOCS']
        title: Brief descriptive title
        context: Where/when this was encountered
        current_behavior: What exists now or what's missing
        proposed_change: What should be done
        impact: Expected benefits/improvements
        implementation_notes: Optional technical details
        priority: 1 (Critical) to 4 (Nice to have)
        
    Returns:
        bool: True if proposal was added successfully
    """
    from pathlib import Path
    import datetime
    import sys
    import os
    
    # Import config for proposal file path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import config
    
    proposals_file = config.PROPOSALS_FILE_PATH
    
    # Validate category
    valid_categories = ['ENHANCEMENT', 'BUG', 'REFACTOR', 'OPTIMIZATION', 'SECURITY', 'DOCS']
    if category.upper() not in valid_categories:
        print(f"Invalid category: {category}. Must be one of {valid_categories}")
        return False
        
    # Validate priority
    if not 1 <= priority <= 4:
        print(f"Invalid priority: {priority}. Must be between 1 and 4")
        return False
        
    # Format the proposal
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    proposal = f"""
### [P{priority}][{category.upper()}] {title}

**Added:** {timestamp}

**Context:** 
{context}

**Current Behavior:** 
{current_behavior}

**Proposed Change:** 
{proposed_change}

**Impact:** 
{impact}
"""
    
    if implementation_notes:
        proposal += f"""
**Implementation Notes:** 
{implementation_notes}
"""
    
    proposal += "\n---\n"
    
    try:
        # Ensure the directory exists
        proposals_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file if it doesn't exist
        if not proposals_file.exists():
            with proposals_file.open('w', encoding='utf-8') as f:
                f.write("# Proposal Bank\n\n")
        
        # Append the new proposal
        with proposals_file.open('a', encoding='utf-8') as f:
            f.write(proposal)
            
        print(f"✅ Successfully added proposal: {title}")
        return True
        
    except Exception as e:
        print(f"Error adding proposal: {e}")
        return False 