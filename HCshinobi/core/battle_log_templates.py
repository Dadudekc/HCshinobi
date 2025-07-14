"""
Modern Battle Log Templates
Replaces legacy hardcoded battle messages with dynamic templates.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BattleLogTemplate:
    """Template for battle log messages"""
    template: str
    variables: List[str]
    category: str

class ModernBattleLogger:
    """Modern battle logging system with dynamic templates."""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, List[BattleLogTemplate]]:
        """Load battle log templates."""
        return {
            "battle_start": [
                BattleLogTemplate(
                    template="⚔️ **{mission_name}** | Battle Commences!",
                    variables=["mission_name"],
                    category="mission"
                ),
                BattleLogTemplate(
                    template="🎯 **{mission_type}** Mission | Turn {turn}",
                    variables=["mission_type", "turn"],
                    category="mission"
                )
            ],
            "battle_end": [
                BattleLogTemplate(
                    template="🏁 **{mission_name}** | Mission Complete!",
                    variables=["mission_name"],
                    category="mission"
                ),
                BattleLogTemplate(
                    template="🎉 **{winner}** has defeated **{loser}**!",
                    variables=["winner", "loser"],
                    category="combat"
                ),
                BattleLogTemplate(
                    template="✅ **{player}** has completed the mission!",
                    variables=["player"],
                    category="mission"
                )
            ],
            "action": [
                BattleLogTemplate(
                    template="**{actor}** uses **{jutsu}** for **{damage}** damage!",
                    variables=["actor", "jutsu", "damage"],
                    category="combat"
                ),
                BattleLogTemplate(
                    template="**{actor}** attacks for **{damage}** damage!",
                    variables=["actor", "damage"],
                    category="combat"
                ),
                BattleLogTemplate(
                    template="**{actor}** attempts **{jutsu}** but misses!",
                    variables=["actor", "jutsu"],
                    category="combat"
                )
            ],
            "status": [
                BattleLogTemplate(
                    template="**{name}**\nHP: {hp}/{max_hp} [{hp_bar}]\nChakra: {chakra}",
                    variables=["name", "hp", "max_hp", "hp_bar", "chakra"],
                    category="status"
                )
            ],
            "mission_status": [
                BattleLogTemplate(
                    template="📋 **{mission_name}** | Turn {turn}",
                    variables=["mission_name", "turn"],
                    category="mission"
                ),
                BattleLogTemplate(
                    template="🎯 **{mission_type}** | {progress}",
                    variables=["mission_type", "progress"],
                    category="mission"
                )
            ]
        }
    
    def format_battle_start(self, mission_name: str = "Mission") -> str:
        """Format battle start message."""
        template = self.templates["battle_start"][0]
        return template.template.format(mission_name=mission_name)
    
    def format_battle_end(self, winner: str, loser: str, mission_name: str = "Mission") -> str:
        """Format battle end message."""
        end_templates = self.templates["battle_end"]
        messages = []
        
        # Mission completion
        messages.append(end_templates[0].template.format(mission_name=mission_name))
        
        # Combat result
        messages.append(end_templates[1].template.format(winner=winner, loser=loser))
        
        return "\n".join(messages)
    
    def format_action(self, actor: str, jutsu: str, damage: int, success: bool = True) -> str:
        """Format action message."""
        if success:
            template = self.templates["action"][0]
            return template.template.format(actor=actor, jutsu=jutsu, damage=damage)
        else:
            template = self.templates["action"][2]
            return template.template.format(actor=actor, jutsu=jutsu)
    
    def format_basic_attack(self, actor: str, damage: int) -> str:
        """Format basic attack message."""
        template = self.templates["action"][1]
        return template.template.format(actor=actor, damage=damage)
    
    def format_status(self, name: str, hp: int, max_hp: int, chakra: int) -> str:
        """Format status message."""
        template = self.templates["status"][0]
        
        # Create HP bar
        hp_percentage = hp / max_hp if max_hp > 0 else 0
        bar_length = 10
        filled = int(hp_percentage * bar_length)
        hp_bar = "█" * filled + "░" * (bar_length - filled)
        
        return template.template.format(
            name=name,
            hp=hp,
            max_hp=max_hp,
            hp_bar=hp_bar,
            chakra=chakra
        )
    
    def format_mission_status(self, mission_name: str, turn: int) -> str:
        """Format mission status message."""
        template = self.templates["mission_status"][0]
        return template.template.format(mission_name=mission_name, turn=turn)
    
    def create_battle_log(self, actions: List[Dict[str, Any]], mission_name: str = "Mission") -> str:
        """Create a complete battle log from actions."""
        if not actions:
            return "No battle actions recorded."
        
        log_lines = []
        
        # Add battle start
        log_lines.append(self.format_battle_start(mission_name))
        log_lines.append("")
        
        # Add actions
        for action in actions:
            if action.get("type") == "attack":
                if action.get("jutsu"):
                    log_lines.append(self.format_action(
                        action["actor"],
                        action["jutsu"],
                        action["damage"],
                        action.get("success", True)
                    ))
                else:
                    log_lines.append(self.format_basic_attack(
                        action["actor"],
                        action["damage"]
                    ))
        
        # Add battle end if there's a winner
        if actions and "winner" in actions[-1]:
            log_lines.append("")
            log_lines.append(self.format_battle_end(
                actions[-1]["winner"],
                actions[-1]["loser"],
                mission_name
            ))
        
        return "\n".join(log_lines)
    
    def format_modern_battle_summary(self, 
                                   mission_name: str,
                                   winner: str,
                                   loser: str,
                                   turn: int,
                                   actions: List[Dict[str, Any]]) -> str:
        """Format a modern battle summary."""
        summary_lines = []
        
        # Battle header
        summary_lines.append(f"⚔️ **{mission_name}**")
        summary_lines.append("Battle Complete!")
        summary_lines.append("")
        
        # Winner status
        summary_lines.append(f"**{winner}** (You)")
        summary_lines.append(f"HP: {actions[-1].get('winner_hp', 100)}/100 [██████░░░░]")
        summary_lines.append(f"Chakra: {actions[-1].get('winner_chakra', 100)}")
        summary_lines.append(f"Rank: {actions[-1].get('winner_rank', 'Shinobi')}")
        summary_lines.append("")
        
        # Loser status
        summary_lines.append(f"**{loser}**")
        summary_lines.append(f"HP: 0/{actions[-1].get('loser_max_hp', 50)} [░░░░░░░░░░]")
        summary_lines.append(f"Chakra: {actions[-1].get('loser_chakra', 40)}")
        summary_lines.append(f"Rank: {actions[-1].get('loser_rank', 'Enemy')}")
        summary_lines.append("")
        
        # Battle result
        summary_lines.append(f"**{winner}** has defeated **{loser}**!")
        summary_lines.append("")
        
        # Battle log
        summary_lines.append("**Battle Log**")
        for action in actions[-5:]:  # Last 5 actions
            if action.get("type") == "attack":
                if action.get("jutsu"):
                    summary_lines.append(f"{action['actor']} uses {action['jutsu']} for {action['damage']} damage!")
                else:
                    summary_lines.append(f"{action['actor']} attacks for {action['damage']} damage!")
        
        # Mission completion
        summary_lines.append("")
        summary_lines.append(f"**{mission_name}** | Turn {turn}")
        
        return "\n".join(summary_lines) 