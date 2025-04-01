"""
Token System module for the HCshinobi project.
Manages player tokens, unlocks, persistence, and transaction logging.
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import asyncio
import os

# Use centralized constants, utils
from .constants import (
    TOKEN_FILE, TOKEN_LOG_FILE, TOKEN_COSTS, MAX_CLAN_BOOST_TOKENS,
    TOKEN_START_AMOUNT
)
from ..utils.file_io import load_json, save_json
from ..utils.logging import get_logger, log_event

logger = get_logger(__name__)

class TokenError(Exception):
    """Exception raised for token-related errors (e.g., insufficient funds)."""
    pass

class TokenSystem:
    """
    Manages tokens for players: balances, unlocks, spending, logging.
    Uses TOKEN_FILE for state and TOKEN_LOG_FILE for history.
    """

    def __init__(self, token_file: str = TOKEN_FILE, log_file: str = TOKEN_LOG_FILE):
        """Initialize the token system."""
        self.token_file = token_file # Store path
        self.log_file = log_file # Store path
        self.player_tokens: Dict[str, int] = {}
        self.player_unlocks: Dict[str, List[str]] = {}
        self.transaction_log: List[Dict[str, Any]] = []
        # Defer loading to async initialize method
        # self._load_tokens()
        # self._load_log()

    async def initialize(self):
        """Asynchronously load initial token data and logs."""
        await self._load_tokens()
        await self._load_log()

    async def _load_tokens(self):
        """Load player tokens and unlocks asynchronously."""
        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            data = await load_json(self.token_file)
            if data and isinstance(data, dict):
                self.player_tokens = data.get("tokens", {})
                self.player_unlocks = data.get("unlocks", {})
                logger.info(f"Loaded token data from {self.token_file}")
            else:
                logger.warning(f"Token file {self.token_file} not found or invalid. Initializing empty token data.")
                self.player_tokens = {}
                self.player_unlocks = {}
                # Optionally save empty structure immediately
                # await self._save_tokens()
        except Exception as e:
            logger.error(f"Error loading token data: {e}", exc_info=True)
            self.player_tokens = {}
            self.player_unlocks = {}

    async def _save_tokens(self):
        """Save player tokens and unlocks asynchronously."""
        try:
            data = {"tokens": self.player_tokens, "unlocks": self.player_unlocks}
            await save_json(self.token_file, data)
            # logger.debug("Token data saved.")
        except Exception as e:
            logger.error(f"Error saving token data: {e}", exc_info=True)

    async def _load_log(self):
        """Load transaction log asynchronously."""
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            log_data = await load_json(self.log_file)
            if log_data and isinstance(log_data, list):
                self.transaction_log = log_data
                # logger.debug(f"Loaded {len(self.transaction_log)} log entries.")
            else:
                self.transaction_log = []
        except Exception as e:
            logger.error(f"Error loading transaction log: {e}", exc_info=True)
            self.transaction_log = []

    async def _save_log(self):
        """Save transaction log asynchronously."""
        try:
            await save_json(self.log_file, self.transaction_log)
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
            logger.warning(f"Token log file {self.log_file} not found or invalid. Starting new log.")
            transactions = []

        transactions.append(transaction_record)

        # Optional: Limit log size
        MAX_LOG_ENTRIES = 10000
        if len(transactions) > MAX_LOG_ENTRIES:
            transactions = transactions[-MAX_LOG_ENTRIES:]

        self.transaction_log = transactions
        await self._save_log()

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
        return self.player_tokens.get(player_id, TOKEN_START_AMOUNT)

    async def ensure_player_exists(self, player_id: str):
        """Ensure a player exists in the token system, initializing if needed."""
        if player_id not in self.player_tokens:
            self.player_tokens[player_id] = TOKEN_START_AMOUNT
            await self._log_transaction(player_id, 'grant', TOKEN_START_AMOUNT, 'initial_grant')
            await self._save_tokens()
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

        await self.ensure_player_exists(player_id) # Add await
        current_balance = self.player_tokens[player_id]
        new_balance = current_balance + amount

        # Prevent balance going below zero through direct removal
        if new_balance < 0 and amount < 0:
             logger.warning(f"Admin action would reduce player {player_id} tokens below zero. Setting to 0.")
             new_balance = 0
             amount = -current_balance # Adjust amount for logging

        self.player_tokens[player_id] = new_balance

        details = {"admin_id": admin_id} if admin_id else {}
        transaction_type = 'add' if amount > 0 else 'remove'
        await self._log_transaction(player_id, transaction_type, amount, reason, details)
        await self._save_tokens()
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

        await self.ensure_player_exists(player_id) # Add await
        current_balance = self.player_tokens[player_id]

        if current_balance < amount:
            raise TokenError(f"Insufficient tokens. Required: {amount}, Available: {current_balance}")

        new_balance = current_balance - amount
        self.player_tokens[player_id] = new_balance

        await self._log_transaction(player_id, "spend", -amount, reason) # Log spend as negative amount
        await self._save_tokens()
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
            await self._save_tokens() # Save after modifying unlocks
            logger.info(f"Player {player_id} unlocked feature: {feature_name} for {cost} tokens.")
        else:
             # This case should ideally not be reached due to the initial check
             logger.warning(f"Player {player_id} attempted to unlock feature '{feature_name}' which was already present after spending tokens. Inconsistency?.")

        return remaining_balance 