"""Mission templates and progression chains."""
from typing import Dict, Any, Optional, List

# Clan-specific mission requirements
CLAN_REQUIREMENTS = {
    "Uchiha": {
        "special_items": ["sharingan_scroll", "fire_chakra_paper"],
        "bonus_rewards": {
            "fire_style_scroll": 0.3,  # 30% chance on mission completion
            "sharingan_training_manual": 0.1
        }
    },
    "Hyuga": {
        "special_items": ["byakugan_scroll", "gentle_fist_manual"],
        "bonus_rewards": {
            "chakra_control_scroll": 0.3,
            "advanced_taijutsu_scroll": 0.2
        }
    },
    "Nara": {
        "special_items": ["shadow_binding_scroll", "tactical_manual"],
        "bonus_rewards": {
            "shadow_technique_scroll": 0.3,
            "strategy_guide": 0.2
        }
    },
    "Akimichi": {
        "special_items": ["food_pills", "expansion_jutsu_scroll"],
        "bonus_rewards": {
            "special_food_pill_recipe": 0.3,
            "body_enhancement_scroll": 0.2
        }
    }
}

# Mission chain definitions
MISSION_CHAINS = {
    "chunin_exam_preparation": {
        "chain_id": "chunin_prep",
        "name": "Path to Chunin",
        "description": "Series of missions to prepare for the Chunin exams",
        "required_rank": "genin",
        "missions": [
            {
                "id": "basic_training",
                "name": "Basic Training",
                "type": "training",
                "required_items": ["training_scroll", "kunai_set"],
                "unlocks": ["advanced_training", "special_training_manual"]
            },
            {
                "id": "advanced_training",
                "name": "Advanced Combat Training",
                "type": "combat",
                "required_items": ["special_training_manual", "chakra_weights"],
                "unlocks": ["team_tactics", "advanced_weapon_scroll"]
            },
            {
                "id": "team_tactics",
                "name": "Team Coordination",
                "type": "team",
                "required_items": ["advanced_weapon_scroll", "communication_seal"],
                "unlocks": ["final_preparation", "team_formation_manual"]
            },
            {
                "id": "final_preparation",
                "name": "Final Exam Preparation",
                "type": "challenge",
                "required_items": ["team_formation_manual", "soldier_pills"],
                "unlocks": ["chunin_exam_ready", "chunin_candidate_headband"]
            }
        ]
    },
    "anbu_recruitment": {
        "chain_id": "anbu_recruit",
        "name": "ANBU Recruitment",
        "description": "Secret missions to prove worthy of ANBU",
        "required_rank": "chunin",
        "required_level": 20,
        "missions": [
            {
                "id": "stealth_assessment",
                "name": "Shadow Operations",
                "type": "stealth",
                "required_items": ["anbu_invitation", "stealth_cloak"],
                "unlocks": ["assassination_training", "anbu_mask_fragment"]
            },
            {
                "id": "assassination_training",
                "name": "Silent Strike",
                "type": "assassination",
                "required_items": ["anbu_mask_fragment", "poisoned_blade"],
                "unlocks": ["intelligence_gathering", "anbu_tattoo_design"]
            },
            {
                "id": "intelligence_gathering",
                "name": "Deep Cover",
                "type": "espionage",
                "required_items": ["anbu_tattoo_design", "cipher_scroll"],
                "unlocks": ["final_test", "anbu_cipher_key"]
            },
            {
                "id": "final_test",
                "name": "ANBU Initiation",
                "type": "challenge",
                "required_items": ["anbu_cipher_key", "black_ops_gear"],
                "unlocks": ["anbu_membership", "anbu_mask"]
            }
        ]
    }
}

# Extended mission templates
EXTENDED_MISSION_TEMPLATES = {
    "easy": {
        "training": {
            "name_template": "Training: {focus}",
            "description_template": "Complete {focus} training exercises under supervision.",
            "required_items": ["training_scroll", "practice_weapons"],
            "recommended_items": ["training_weights"],
            "min_level": 1,
            "bonus_objectives": {
                "no_breaks": {
                    "description": "Complete all exercises without breaks",
                    "reward": {"xp": 100, "ryo": 200}
                }
            }
        },
        "gathering": {
            "name_template": "Gather {item}",
            "description_template": "Collect {quantity} {item} from {location}.",
            "required_items": ["gathering_pouch", "field_guide"],
            "recommended_items": ["preservation_scroll"],
            "min_level": 1,
            "reward_multiplier": 1.0,
            "bonus_objectives": [
                {
                    "description": "Gather extra rare specimens",
                    "reward": {"items": ["rare_herb"]}
                }
            ]
        }
    },
    "medium": {
        "escort": {
            "name_template": "Escort {vip}",
            "description_template": "Safely escort {vip} to {destination} while avoiding {threat}.",
            "required_items": ["communication_scroll", "medical_kit"],
            "recommended_items": ["barrier_tags", "smoke_bombs"],
            "min_level": 5,
            "reward_multiplier": 2.0,
            "bonus_objectives": [
                {
                    "description": "Complete journey ahead of schedule",
                    "reward": {"ryo": 1000}
                },
                {
                    "description": "Avoid all combat encounters",
                    "reward": {"items": ["stealth_specialist_badge"]}
                }
            ]
        },
        "investigation": {
            "name_template": "Investigate {incident}",
            "description_template": "Uncover the truth behind {incident} in {location}.",
            "required_items": ["investigation_kit", "camera"],
            "recommended_items": ["disguise_kit", "truth_serum"],
            "min_level": 5,
            "reward_multiplier": 2.0,
            "bonus_objectives": [
                {
                    "description": "Find additional evidence",
                    "reward": {"items": ["classified_intel"]}
                }
            ]
        }
    },
    "hard": {
        "assassination": {
            "name_template": "Eliminate {target}",
            "description_template": "Eliminate {target} who has been causing trouble in {location}.",
            "required_items": ["assassination_manual", "poison_kit", "stealth_gear"],
            "recommended_items": ["escape_scroll", "smoke_bombs"],
            "min_level": 10,
            "reward_multiplier": 3.0,
            "bonus_objectives": [
                {
                    "description": "Leave no witnesses",
                    "reward": {"items": ["anbu_recommendation"]}
                }
            ]
        },
        "siege": {
            "name_template": "Siege of {location}",
            "description_template": "Lead an assault on {location} to {objective}.",
            "required_items": ["siege_plans", "soldier_pills", "explosive_tags"],
            "recommended_items": ["summoning_contract", "barrier_breaker"],
            "min_level": 10,
            "reward_multiplier": 3.0,
            "bonus_objectives": [
                {
                    "description": "Minimize civilian casualties",
                    "reward": {"items": ["hero_medal"]}
                }
            ]
        }
    }
}

# Special event missions
EVENT_MISSIONS = {
    "chunin_exams": {
        "name_template": "Chunin Exam: {phase}",
        "description_template": "Compete in {phase} of the Chunin Exams.",
        "phases": ["written_test", "forest_of_death", "preliminary_matches", "final_tournament"],
        "required_items": {
            "written_test": ["exam_pass", "writing_materials"],
            "forest_of_death": ["heaven_scroll", "earth_scroll", "survival_kit"],
            "preliminary_matches": ["tournament_badge", "medical_clearance"],
            "final_tournament": ["finalist_badge", "arena_pass"]
        },
        "rewards": {
            "written_test": {"xp": 500, "items": ["chunin_knowledge_scroll"]},
            "forest_of_death": {"xp": 1000, "items": ["survival_specialist_badge"]},
            "preliminary_matches": {"xp": 1500, "items": ["combat_specialist_badge"]},
            "final_tournament": {"xp": 2000, "items": ["chunin_vest"], "rank": "chunin"}
        }
    }
}

# Progressive reward system
REWARD_TIERS = {
    "D": {
        "base_xp": 100,
        "base_ryo": 500,
        "item_chances": {
            "common": 0.8,
            "uncommon": 0.2,
            "rare": 0.05
        }
    },
    "C": {
        "base_xp": 300,
        "base_ryo": 1500,
        "item_chances": {
            "common": 0.6,
            "uncommon": 0.4,
            "rare": 0.1,
            "very_rare": 0.05
        }
    },
    "B": {
        "base_xp": 800,
        "base_ryo": 4000,
        "item_chances": {
            "uncommon": 0.6,
            "rare": 0.3,
            "very_rare": 0.1,
            "legendary": 0.05
        }
    },
    "A": {
        "base_xp": 2000,
        "base_ryo": 10000,
        "item_chances": {
            "rare": 0.5,
            "very_rare": 0.3,
            "legendary": 0.1,
            "unique": 0.05
        }
    },
    "S": {
        "base_xp": 5000,
        "base_ryo": 25000,
        "item_chances": {
            "very_rare": 0.4,
            "legendary": 0.3,
            "unique": 0.1,
            "artifact": 0.05
        }
    }
}

# Mission validation schemas
MISSION_SCHEMA = {
    "required_fields": [
        "id", "name", "description", "objectives",
        "requirements", "rewards", "challenges",
        "failure_conditions"
    ],
    "objective_fields": [
        "description", "required_items", "completion_criteria"
    ],
    "challenge_fields": [
        "type", "difficulty", "description", "required_items"
    ],
    "reward_fields": [
        "xp", "ryo", "items", "bonus_conditions"
    ]
}

# Mission adaptation parameters
ADAPTATION_PARAMETERS = {
    "difficulty_range": (-1.0, 1.0),  # Min/max difficulty adjustment
    "reward_range": (-1.0, 1.0),      # Min/max reward adjustment
    "challenge_types": [
        "combat", "skill", "stealth", "survival",
        "intelligence", "teamwork"
    ],
    "difficulty_thresholds": {
        "easy": {"min": 1, "max": 3},
        "medium": {"min": 4, "max": 7},
        "hard": {"min": 8, "max": 10}
    }
}

def validate_mission_data(mission_data: Dict[str, Any]) -> List[str]:
    """Validate mission data structure and return list of errors."""
    errors = []
    
    # Check required fields
    for field in MISSION_SCHEMA["required_fields"]:
        if field not in mission_data:
            errors.append(f"Missing required field: {field}")
    
    # Validate objectives
    if "objectives" in mission_data:
        for i, objective in enumerate(mission_data["objectives"]):
            for field in MISSION_SCHEMA["objective_fields"]:
                if field not in objective:
                    errors.append(f"Missing field '{field}' in objective {i}")
    
    # Validate challenges
    if "challenges" in mission_data:
        for i, challenge in enumerate(mission_data["challenges"]):
            for field in MISSION_SCHEMA["challenge_fields"]:
                if field not in challenge:
                    errors.append(f"Missing field '{field}' in challenge {i}")
            if challenge.get("type") not in ADAPTATION_PARAMETERS["challenge_types"]:
                errors.append(f"Invalid challenge type in challenge {i}")
            
            difficulty = challenge.get("difficulty")
            if not isinstance(difficulty, (int, float)):
                errors.append(f"Invalid difficulty value in challenge {i}")
            elif difficulty < 1 or difficulty > 10:
                errors.append(f"Difficulty must be between 1 and 10 in challenge {i}")
    
    # Validate rewards
    if "rewards" in mission_data:
        for field in MISSION_SCHEMA["reward_fields"]:
            if field not in mission_data["rewards"]:
                errors.append(f"Missing reward field: {field}")
    
    return errors

def validate_adaptation_data(adaptation_data: Dict[str, Any]) -> List[str]:
    """Validate mission adaptation data and return list of errors."""
    errors = []
    
    # Check difficulty adjustment
    diff_adj = adaptation_data.get("difficulty_adjustment")
    if diff_adj is not None:
        min_diff, max_diff = ADAPTATION_PARAMETERS["difficulty_range"]
        if not isinstance(diff_adj, (int, float)):
            errors.append("difficulty_adjustment must be a number")
        elif diff_adj < min_diff or diff_adj > max_diff:
            errors.append(f"difficulty_adjustment must be between {min_diff} and {max_diff}")
    
    # Check reward adjustment
    reward_adj = adaptation_data.get("reward_adjustment")
    if reward_adj is not None:
        min_reward, max_reward = ADAPTATION_PARAMETERS["reward_range"]
        if not isinstance(reward_adj, (int, float)):
            errors.append("reward_adjustment must be a number")
        elif reward_adj < min_reward or reward_adj > max_reward:
            errors.append(f"reward_adjustment must be between {min_reward} and {max_reward}")
    
    # Validate additional challenges
    if "additional_challenges" in adaptation_data:
        for i, challenge in enumerate(adaptation_data["additional_challenges"]):
            if "type" not in challenge:
                errors.append(f"Missing type in additional challenge {i}")
            elif challenge["type"] not in ADAPTATION_PARAMETERS["challenge_types"]:
                errors.append(f"Invalid challenge type in additional challenge {i}")
            
            if "difficulty" not in challenge:
                errors.append(f"Missing difficulty in additional challenge {i}")
            elif not isinstance(challenge["difficulty"], (int, float)):
                errors.append(f"Invalid difficulty value in additional challenge {i}")
    
    return errors

def calculate_adapted_difficulty(
    base_difficulty: str,
    performance_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate adapted difficulty based on performance data."""
    thresholds = ADAPTATION_PARAMETERS["difficulty_thresholds"][base_difficulty]
    
    # Calculate performance score (0-1)
    completion_time = performance_data.get("completion_time", 0)
    objectives_completed = performance_data.get("objectives_completed", 0)
    total_objectives = performance_data.get("total_objectives", 1)
    damage_taken = performance_data.get("damage_taken", 0)
    
    time_score = min(1.0, 1.0 / (completion_time / performance_data.get("expected_time", 1)))
    objective_score = objectives_completed / total_objectives
    health_score = max(0.0, 1.0 - (damage_taken / 100))
    
    performance_score = (time_score + objective_score + health_score) / 3
    
    # Calculate difficulty adjustment
    current_difficulty = (thresholds["max"] + thresholds["min"]) / 2
    if performance_score > 0.8:
        new_difficulty = min(thresholds["max"], current_difficulty + 1)
    elif performance_score < 0.4:
        new_difficulty = max(thresholds["min"], current_difficulty - 1)
    else:
        new_difficulty = current_difficulty
        
    return {
        "new_difficulty": new_difficulty,
        "performance_score": performance_score,
        "difficulty_adjustment": new_difficulty - current_difficulty
    }

# Reward calculation functions
def calculate_mission_rewards(
    difficulty: str,
    mission_type: str,
    clan: Optional[str] = None,
    bonus_objectives_completed: Optional[list] = None
) -> Dict[str, Any]:
    """Calculate total rewards for a mission including clan bonuses."""
    # Get base tier rewards
    tier = "D" if difficulty == "easy" else "C" if difficulty == "medium" else "B"
    rewards = REWARD_TIERS[tier].copy()
    
    # Add clan bonuses if applicable
    if clan and clan in CLAN_REQUIREMENTS:
        clan_info = CLAN_REQUIREMENTS[clan]
        if "bonus_rewards" in clan_info:
            rewards["clan_bonus_items"] = clan_info["bonus_rewards"]
    
    # Add mission-type specific rewards
    template = EXTENDED_MISSION_TEMPLATES[difficulty][mission_type]
    if "bonus_objectives" in template:
        rewards["bonus_objectives"] = template["bonus_objectives"]
        
    # Calculate completed bonus objectives
    if bonus_objectives_completed:
        bonus_rewards = {"xp": 0, "ryo": 0, "items": []}
        for objective in bonus_objectives_completed:
            if objective in template.get("bonus_objectives", []):
                obj_reward = template["bonus_objectives"][objective]["reward"]
                bonus_rewards["xp"] += obj_reward.get("xp", 0)
                bonus_rewards["ryo"] += obj_reward.get("ryo", 0)
                bonus_rewards["items"].extend(obj_reward.get("items", []))
        rewards["bonus_rewards"] = bonus_rewards
    
    return rewards

def get_clan_requirements(clan: str) -> Dict[str, Any]:
    """Get requirements and bonuses for a specific clan."""
    return CLAN_REQUIREMENTS.get(clan, {})

def get_mission_template(difficulty: str, mission_type: str) -> Dict[str, Any]:
    """Get mission template by difficulty and type."""
    return EXTENDED_MISSION_TEMPLATES[difficulty][mission_type] 