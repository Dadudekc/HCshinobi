import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Constants
RULEBOOK_PATH = os.getenv("RULEBOOK_PATH", "rulebook.md")
PROPOSALS_FILE_PATH = os.getenv("PROPOSALS_FILE_PATH", "rulebook_update_proposals.md")

def load_rules_from_rulebook(rulebook_path: Path) -> Dict[str, Any]:
    """Load rules from the rulebook markdown file."""
    rules = {}
    try:
        content = Path(rulebook_path).read_text(encoding='utf-8')
        rule_blocks = content.split("### Rule")
        
        for block in rule_blocks[1:]:  # Skip first empty block
            if "```yaml" in block and "```" in block:
                yaml_content = block.split("```yaml")[1].split("```")[0]
                try:
                    rule_data = yaml.safe_load(yaml_content)
                    if isinstance(rule_data, dict) and 'rules' in rule_data:
                        rule = rule_data['rules'][0]
                        rules[rule['id']] = rule
                except yaml.YAMLError:
                    continue
    except Exception as e:
        print(f"Error loading rules: {e}")
    return rules

def generate_reflection(alert_data: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a reflection based on the alert data and current rules."""
    reflection = {
        'type': 'agent_reflection',
        'reflection_agent': os.getenv('AGENT_NAME', 'UnknownAgent'),
        'violating_agent': alert_data.get('violating_agent'),
        'mentioned_rule_id': None,
        'suggested_action': 'monitor_situation',
        'proposal_content': None,
        'thoughts': []
    }

    # Extract rule ID if mentioned in analysis
    analysis = alert_data.get('analysis', '')
    for rule_id in rules.keys():
        if rule_id in analysis:
            reflection['mentioned_rule_id'] = rule_id
            break

    # Determine if we need to propose a new rule
    needs_proposal = False
    if 'unclear' in alert_data.get('halt_reason', '').lower() or \
       'vague' in alert_data.get('halt_reason', '').lower() or \
       'not found' in analysis.lower():
        needs_proposal = True

    if needs_proposal:
        reflection['suggested_action'] = 'propose_rule_update'
        reflection['proposal_content'] = f"""### [REFLECT] Proposal
**Target Rule ID:** {reflection['mentioned_rule_id'] or 'NEW_RULE'}

**Reasoning:** {alert_data.get('analysis')}

**Proposed Change Summary:**
Based on the alert from {alert_data.get('violating_agent')}, 
we need to clarify the rules regarding: {alert_data.get('halt_reason')}
"""
        reflection['thoughts'].append("Action: Proposing clarification/new rule.")
    else:
        reflection['thoughts'].append("Action: Monitoring situation.")

    return reflection

def save_reflection(reflection_data: Dict[str, Any], outbox_path: Path) -> None:
    """Save reflection data to a JSON file in the outbox."""
    reflection_id = reflection_data.get('reflection_id')
    if not reflection_id:
        return
    
    outfile = Path(outbox_path) / f"{reflection_id}.json"
    with open(outfile, 'w') as f:
        json.dump(reflection_data, f, indent=2)

def submit_proposal(proposal_content: Optional[str], reflection_id: str) -> None:
    """Submit a proposal to the proposals file."""
    if not proposal_content:
        return

    proposals_path = Path(PROPOSALS_FILE_PATH)
    header = f"\n### Proposal from Reflection '{reflection_id}'\n"
    with open(proposals_path, 'a') as f:
        f.write(f"{header}{proposal_content}\n")

class AlertHandler(FileSystemEventHandler):
    """Handles new alert files in the inbox directory."""
    
    def __init__(self, agent_name: str, inbox_path: str, outbox_path: str):
        self.agent_name = agent_name
        self.inbox_path = Path(inbox_path)
        self.outbox_path = Path(outbox_path)
        self.rules = load_rules_from_rulebook(Path(RULEBOOK_PATH))

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            try:
                with open(event.src_path, 'r') as f:
                    alert_data = json.load(f)
                
                if alert_data.get('type') == 'rule_alert':
                    reflection = generate_reflection(alert_data, self.rules)
                    reflection['reflection_id'] = f"reflect-{alert_data['message_id']}"
                    
                    save_reflection(reflection, self.outbox_path)
                    
                    if reflection.get('proposal_content'):
                        submit_proposal(
                            reflection['proposal_content'],
                            reflection['reflection_id']
                        )
            except Exception as e:
                print(f"Error processing alert: {e}")

def start_monitoring(agent_name: str, inbox_path: str, outbox_path: str):
    """Start monitoring the inbox for new alerts."""
    event_handler = AlertHandler(agent_name, inbox_path, outbox_path)
    observer = Observer()
    observer.schedule(event_handler, inbox_path, recursive=False)
    observer.start()
    return observer 