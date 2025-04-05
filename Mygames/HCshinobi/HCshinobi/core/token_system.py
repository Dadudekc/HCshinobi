"""
Token System module for the HCshinobi project.
Manages player tokens, unlocks, persistence, and transaction logging.
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta, timezone
import asyncio
import os
import json
import logging

# Use absolute imports for core modules and constants
from HCshinobi.utils.file_io import load_json, save_json
# Assuming constants.py defines TOKENS_FILE
from .constants import (
    TOKEN_FILE, TOKEN_LOG_FILE, TOKEN_COSTS, MAX_CLAN_BOOST_TOKENS,
    TOKEN_START_AMOUNT, TOKENS_SUBDIR, REROLL_COOLDOWN_HOURS, TOKENS_PER_REROLL
)
from ..utils.logging import get_logger, log_event

logger = logging.getLogger(__name__)

# --- NEW: Custom Exception --- #
class TokenError(Exception):
    """Custom exception for token system errors (e.g., insufficient funds)."""
    pass
# --- END NEW --- #

class TokenSystem:
    """
    Manages tokens for players: balances, unlocks, spending, logging.
    Uses TOKEN_FILE for state and TOKEN_LOG_FILE for history.
    """

    def __init__(self, data_dir: str, token_expiry_hours: int = 24):
        self.base_data_dir = data_dir
        # Construct specific path for token files
        self.tokens_data_dir = os.path.join(data_dir, TOKENS_SUBDIR)
        os.makedirs(self.tokens_data_dir, exist_ok=True)
        
        # Construct full file path for the tokens data file
        self.tokens_file_path = os.path.join(self.tokens_data_dir, TOKEN_FILE)
        
        self.token_expiry = timedelta(hours=token_expiry_hours)
        self.tokens: Dict[str, Dict[str, str]] = {} # Key: user_id_str
        logger.info(f"TokenSystem initialized. Data dir: {self.tokens_data_dir}, Expiry: {self.token_expiry}")
        # Loading is handled by an explicit async call

    async def load_token_data(self):
        """Loads token data from the JSON file, discarding expired tokens."""
        try:
            raw_tokens = load_json(self.tokens_file_path)
            if raw_tokens is None:
                logger.info(f"Tokens file not found or invalid: {self.tokens_file_path}. Starting with no tokens.")
                self.tokens = {}
                return
            elif not isinstance(raw_tokens, dict):
                logger.warning(f"Invalid format in {self.tokens_file_path}, expected dict. Resetting.")
                self.tokens = {}
                return

            valid_tokens = {}
            now = datetime.now(timezone.utc)
            loaded_count = 0
            expired_count = 0

            for user_id, token_info in raw_tokens.items():
                if isinstance(token_info, dict) and 'token' in token_info and 'expiry' in token_info:
                    try:
                        expiry_time = datetime.fromisoformat(token_info['expiry'].replace('Z', '+00:00')) # Handle Z Zulu time
                        if expiry_time > now:
                            valid_tokens[user_id] = token_info
                            loaded_count += 1
                        else:
                            expired_count += 1
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid expiry format for user {user_id} in {self.tokens_file_path}. Discarding token.")
                        expired_count += 1
                else:
                    logger.warning(f"Invalid token data structure for user {user_id} in {self.tokens_file_path}. Discarding.")

            self.tokens = valid_tokens
            logger.info(f"Loaded {loaded_count} valid tokens from {self.tokens_file_path}. Discarded {expired_count} expired or invalid tokens.")
            
            # Optionally, save back immediately to prune the file
            if expired_count > 0:
                await self.save_token_data() 
                 
        except FileNotFoundError:
            logger.info(f"Tokens file not found: {self.tokens_file_path}. Starting with no tokens.")
            self.tokens = {}
        except Exception as e:
            logger.error(f"Error loading token data from {self.tokens_file_path}: {e}", exc_info=True)
            self.tokens = {} # Reset on error

    async def save_token_data(self):
        """Atomically saves the current state of valid tokens."""
        # Although load filters expired, save might include recently expired ones if not cleaned often.
        # Consider adding a cleanup step before saving if needed.
        try:
            success = save_json(self.tokens_file_path, self.tokens)
            if success:
                logger.info(f"Token data saved successfully to {self.tokens_file_path}")
            else:
                logger.error(f"Failed to save token data to {self.tokens_file_path}")
        except Exception as e:
            logger.error(f"Failed to save token data to {self.tokens_file_path}: {e}", exc_info=True)

    async def generate_token(self, user_id: int) -> str:
        """Generates, stores, and returns a new token for a user."""
        user_id_str = str(user_id)
        # Simple token generation (replace with a more secure method if needed)
        new_token = os.urandom(16).hex()
        expiry_time = datetime.now(timezone.utc) + self.token_expiry
        
        self.tokens[user_id_str] = {
            "token": new_token,
            "expiry": expiry_time.isoformat().replace("+00:00", "Z") # Use Z for Zulu/UTC
        }
        await self.save_token_data()
        logger.info(f"Generated new token for user {user_id_str}.")
        return new_token

    async def validate_token(self, user_id: int, token: str) -> bool:
        """Validates if the provided token matches the stored one and is not expired."""
        user_id_str = str(user_id)
        token_info = self.tokens.get(user_id_str)

        if not token_info or token_info.get('token') != token:
            logger.debug(f"Token validation failed for user {user_id_str}: Token mismatch or not found.")
            return False

        try:
            expiry_time = datetime.fromisoformat(token_info['expiry'].replace('Z', '+00:00'))
            if expiry_time <= datetime.now(timezone.utc):
                logger.info(f"Token validation failed for user {user_id_str}: Token expired at {expiry_time}.")
                # Clean up expired token immediately
                del self.tokens[user_id_str]
                await self.save_token_data()
                return False
        except (ValueError, TypeError):
            logger.warning(f"Invalid expiry format encountered during validation for user {user_id_str}. Invalidating token.")
            # Clean up invalid token data
            del self.tokens[user_id_str]
            await self.save_token_data()
            return False

        logger.debug(f"Token validated successfully for user {user_id_str}.")
        return True
        
    async def invalidate_token(self, user_id: int):
        """Removes the token for a specific user, effectively logging them out."""
        user_id_str = str(user_id)
        if user_id_str in self.tokens:
            del self.tokens[user_id_str]
            await self.save_token_data()
            logger.info(f"Invalidated token for user {user_id_str}.")
            return True
        return False

    # Ready hook (if needed, e.g., for periodic cleanup task)
    async def ready_hook(self):
        await self.load_token_data()
        logger.info(f"TokenSystem ready. Loaded {len(self.tokens)} valid tokens.")
        # Optionally start a periodic cleanup task here if load doesn't prune file enough

    def initialize(self):
        """Synchronously load initial token data and logs."""
        self._load_tokens()
        self._load_log()

    def _load_tokens(self):
        """Load player tokens and unlocks synchronously."""
        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(self.tokens_file_path), exist_ok=True)
            data = load_json(self.tokens_file_path)
            if data and isinstance(data, dict):
                self.tokens = data.get("tokens", {})
                logger.info(f"Loaded token data from {self.tokens_file_path}")
            else:
                logger.warning(f"Token file {self.tokens_file_path} not found or invalid. Initializing empty token data.")
                self.tokens = {}
        except Exception as e:
            logger.error(f"Error loading token data: {e}", exc_info=True)
            self.tokens = {}

    def _save_tokens(self):
        """Save player tokens and unlocks synchronously."""
        try:
            data = {"tokens": self.tokens}
            save_json(self.tokens_file_path, data)
            # logger.debug("Token data saved.")
        except Exception as e:
            logger.error(f"Error saving token data: {e}", exc_info=True)

    def _load_log(self):
        """Load transaction log synchronously."""
        try:
            os.makedirs(os.path.dirname(TOKEN_LOG_FILE), exist_ok=True)
            log_data = load_json(TOKEN_LOG_FILE)
            if log_data and isinstance(log_data, list):
                self.transaction_log = log_data
                # logger.debug(f"Loaded {len(self.transaction_log)} log entries.")
            else:
                self.transaction_log = []
        except Exception as e:
            logger.error(f"Error loading transaction log: {e}", exc_info=True)
            self.transaction_log = []

    def _save_log(self):
        """Save transaction log synchronously."""
        try:
            save_json(TOKEN_LOG_FILE, self.transaction_log)
            # logger.debug("Transaction log saved.")
        except Exception as e:
            logger.error(f"Error saving transaction log: {e}", exc_info=True)

    async def _log_transaction(
        self,
        player_id: str,
        transaction_type: str, # e.g., 'add', 'spend', 'unlock'
        amount: int,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a token transaction to TOKEN_LOG_FILE.

        Args:
            player_id: Unique ID of the player.
            transaction_type: Type of transaction.
            amount: Number of tokens involved (positive for add, negative for spend).
            reason: Machine-readable reason (e.g., 'admin_grant', 'clan_boost:Uchiha').
            details: Optional dictionary with context (e.g., {'admin_id': 'xxx'}).
        """
        transaction_record = {
            "timestamp": datetime.now().isoformat(),
            "player_id": player_id,
            "type": transaction_type,
            "amount": amount,
            "reason": reason,
            "balance_after": self.get_player_tokens(player_id), # Record balance *after* change
            **(details or {}) # Merge details dict
        }

        # Load existing transactions or start new list
        transactions = self.transaction_log
        if transactions is None or not isinstance(transactions, list):
            logger.warning(f"Token log file {TOKEN_LOG_FILE} not found or invalid. Starting new log.")
            transactions = []

        transactions.append(transaction_record)

        # Optional: Limit log size
        MAX_LOG_ENTRIES = 10000
        if len(transactions) > MAX_LOG_ENTRIES:
            transactions = transactions[-MAX_LOG_ENTRIES:]

        self.transaction_log = transactions
        self._save_log()

        # Log the event via central logging too
        log_event(
            "token_transaction",
            player_id=player_id,
            transaction_type=transaction_type,
            amount=amount,
            reason=reason,
            new_balance=transaction_record["balance_after"],
            **(details or {})
        )

    def get_player_tokens(self, player_id: str) -> int:
        """Get the token balance for a player, defaults to TOKEN_START_AMOUNT if new."""
        # Return existing balance or the default start amount for players not seen before
        # Note: Does not *grant* start amount, just reports it if player is unknown
        return self.tokens.get(player_id, TOKEN_START_AMOUNT)

    async def ensure_player_exists(self, player_id: str):
        """Ensure a player exists in the token system, initializing if needed."""
        if player_id not in self.tokens:
            self.tokens[player_id] = TOKEN_START_AMOUNT
            await self._log_transaction(player_id, 'grant', TOKEN_START_AMOUNT, 'initial_grant')
            self._save_tokens()
            logger.info(f"Initialized token balance for new player {player_id} to {TOKEN_START_AMOUNT}.")

    async def add_tokens(self, player_id: str, amount: int, reason: str, admin_id: Optional[str] = None) -> int:
        """
        Add tokens to a player's balance. Use negative amount to remove.

        Args:
            player_id: Unique ID of the player.
            amount: Amount of tokens to add (can be negative).
            reason: Reason for the transaction (e.g., 'admin_grant', 'quest_reward').
            admin_id: Optional ID of the admin performing the action.

        Returns:
            The new token balance.

        Raises:
            ValueError: If amount is zero.
        """
        if amount == 0:
             raise ValueError("Cannot add or remove zero tokens.")

        await self.ensure_player_exists(player_id)
        current_balance = self.tokens[player_id]
        new_balance = current_balance + amount

        # Prevent balance going below zero through direct removal
        if new_balance < 0 and amount < 0:
             logger.warning(f"Admin action would reduce player {player_id} tokens below zero. Setting to 0.")
             new_balance = 0
             amount = -current_balance # Adjust amount for logging

        self.tokens[player_id] = new_balance

        details = {"admin_id": admin_id} if admin_id else {}
        transaction_type = 'add' if amount > 0 else 'remove'
        await self._log_transaction(player_id, transaction_type, amount, reason, details)
        self._save_tokens()
        logger.info(f"{transaction_type.capitalize()}ed {abs(amount)} tokens for player {player_id}. Reason: {reason}. New balance: {new_balance}")
        return new_balance

    async def use_tokens(self, player_id: str, amount: int, reason: str) -> int:
        """
        Spend tokens from a player's balance.

        Args:
            player_id: Unique ID of the player.
            amount: Amount of tokens to spend (must be positive).
            reason: Reason for spending tokens (e.g., 'reroll_clan', 'unlock_feature:xyz').

        Returns:
            The remaining token balance.

        Raises:
            ValueError: If amount is not positive.
            TokenError: If the player has insufficient tokens.
        """
        if amount <= 0:
            raise ValueError("Amount to use must be positive.")

        await self.ensure_player_exists(player_id)
        current_balance = self.tokens[player_id]

        if current_balance < amount:
            raise TokenError(f"Insufficient tokens. Required: {amount}, Available: {current_balance}")

        new_balance = current_balance - amount
        self.tokens[player_id] = new_balance

        await self._log_transaction(player_id, "spend", -amount, reason) # Log spend as negative amount
        self._save_tokens()
        logger.info(f"Player {player_id} spent {amount} tokens. Reason: {reason}. Remaining balance: {new_balance}")
        return new_balance

    # Specific use-case methods (examples)

    def use_tokens_for_clan_boost(self, player_id: str, clan_name: str, token_amount: int) -> int:
        """
        Use tokens specifically for boosting a clan roll chance.
        Validates against MAX_CLAN_BOOST_TOKENS.

        Args:
            player_id: ID of the player.
            clan_name: Name of the clan being boosted.
            token_amount: Number of tokens to spend (1 to MAX_CLAN_BOOST_TOKENS).

        Returns:
            Remaining balance after spending tokens.

        Raises:
            ValueError: If token_amount is invalid.
            TokenError: If insufficient funds.
        """
        if not 1 <= token_amount <= MAX_CLAN_BOOST_TOKENS:
            raise ValueError(f"Clan boost token amount must be between 1 and {MAX_CLAN_BOOST_TOKENS}.")

        # Cost might be per token, check constants
        cost_per_token = TOKEN_COSTS.get("clan_boost", 1) # Default to 1 if not set
        total_cost = cost_per_token * token_amount

        return self.use_tokens(
            player_id=player_id,
            amount=total_cost,
            reason=f"clan_boost:{clan_name}" # Include clan in reason
        )

    def use_tokens_for_reroll(self, player_id: str) -> int:
        """
        Use tokens for a clan assignment reroll.

        Args:
            player_id: ID of the player.

        Returns:
            Remaining balance after spending tokens.

        Raises:
            TokenError: If insufficient funds or cost not defined.
        """
        cost = TOKEN_COSTS.get("reroll_clan")
        if cost is None:
             raise TokenError("Reroll cost is not defined in TOKEN_COSTS.")

        return self.use_tokens(player_id=player_id, amount=cost, reason="reroll_clan")

    # --- Feature Unlocks ---

    def get_player_unlocks(self, player_id: str) -> List[str]:
        """Get the list of features unlocked by a player."""
        return self.player_unlocks.get(player_id, [])

    def has_unlock(self, player_id: str, feature_name: str) -> bool:
         """Check if a player has unlocked a specific feature."""
         return feature_name in self.get_player_unlocks(player_id)

    async def unlock_feature(self, player_id: str, feature_name: str) -> int:
        """
        Unlock a feature for a player by spending the required tokens.
        Feature names should correspond to keys in TOKEN_COSTS like "unlock_feature_xyz".

        Args:
            player_id: ID of the player.
            feature_name: The unique name of the feature to unlock.

        Returns:
            The remaining token balance after unlocking.

        Raises:
            ValueError: If feature name is invalid or cost not defined.
            TokenError: If player already has the unlock or insufficient funds.
        """
        if self.has_unlock(player_id, feature_name):
            raise TokenError(f"Feature '{feature_name}' is already unlocked.")

        cost_key = f"unlock_feature_{feature_name}" # Construct key for TOKEN_COSTS
        cost = TOKEN_COSTS.get(cost_key)
        if cost is None:
            raise ValueError(f"Cost for feature '{feature_name}' (key: '{cost_key}') not defined in TOKEN_COSTS.")
        if cost <= 0:
             raise ValueError(f"Feature '{feature_name}' has an invalid cost ({cost}).")

        # Spend tokens first (will raise TokenError if insufficient)
        remaining_balance = await self.use_tokens(
            player_id=player_id,
            amount=cost,
            reason=f"unlock_feature:{feature_name}"
        )

        # Add feature to player's unlocks
        if player_id not in self.player_unlocks:
            self.player_unlocks[player_id] = []

        # Add only if not already present (double check)
        if feature_name not in self.player_unlocks[player_id]:
            self.player_unlocks[player_id].append(feature_name)
            self._save_tokens() # Save after modifying unlocks
            logger.info(f"Player {player_id} unlocked feature: {feature_name} for {cost} tokens.")
        else:
             # This case should ideally not be reached due to the initial check
             logger.warning(f"Player {player_id} attempted to unlock feature '{feature_name}' which was already present after spending tokens. Inconsistency?.") 

        return remaining_balance 