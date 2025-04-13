from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
from datetime import datetime
import json
import hashlib
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

class SecurityManager:
    """Manages database security features including encryption, access control, and audit logging."""
    
    def __init__(self, connection, config_dir: str = "security"):
        """Initialize the security manager.
        
        Args:
            connection: Database connection object
            config_dir: Directory for security configuration and logs
        """
        self.connection = connection
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.audit_log_path = self.config_dir / "audit.log"
        self.key_file = self.config_dir / "key.json"
        self._initialize_security()
        
    def _initialize_security(self) -> None:
        """Initialize security configuration and keys."""
        if not self.key_file.exists():
            # Generate new encryption key
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(os.urandom(32))
            
            # Save key info
            with open(self.key_file, 'w') as f:
                json.dump({
                    "key": key.decode(),
                    "salt": base64.b64encode(salt).decode(),
                    "created_at": datetime.now().isoformat()
                }, f, indent=2)
                
        # Initialize Fernet cipher
        with open(self.key_file) as f:
            key_info = json.load(f)
            self.cipher = Fernet(key_info["key"].encode())
            
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt binary data.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data
        """
        return self.cipher.encrypt(data)
        
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt binary data.
        
        Args:
            encrypted_data: Data to decrypt
            
        Returns:
            Decrypted data
        """
        return self.cipher.decrypt(encrypted_data)
        
    def hash_password(self, password: str) -> str:
        """Hash a password using a secure algorithm.
        
        Args:
            password: Password to hash
            
        Returns:
            Hashed password
        """
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000
        )
        return f"{base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"
        
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash.
        
        Args:
            password: Password to verify
            hashed: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        salt_str, key_str = hashed.split('$')
        salt = base64.b64decode(salt_str)
        stored_key = base64.b64decode(key_str)
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000
        )
        return key == stored_key
        
    def log_audit_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log a security audit event.
        
        Args:
            event_type: Type of event (e.g., "login", "access", "modify")
            details: Event details
        """
        timestamp = datetime.now().isoformat()
        event = {
            "timestamp": timestamp,
            "type": event_type,
            "details": details
        }
        
        with open(self.audit_log_path, 'a') as f:
            f.write(json.dumps(event) + "\n")
            
    def get_audit_logs(self, start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      event_type: Optional[str] = None) -> List[Dict]:
        """Get filtered audit logs.
        
        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            event_type: Optional event type filter
            
        Returns:
            List of matching audit events
        """
        events = []
        with open(self.audit_log_path) as f:
            for line in f:
                event = json.loads(line)
                event_time = datetime.fromisoformat(event["timestamp"])
                
                if start_time and event_time < start_time:
                    continue
                if end_time and event_time > end_time:
                    continue
                if event_type and event["type"] != event_type:
                    continue
                    
                events.append(event)
                
        return events
        
    def rotate_encryption_key(self) -> None:
        """Rotate the encryption key and re-encrypt sensitive data."""
        # Generate new key
        new_salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=new_salt,
            iterations=100000,
            backend=default_backend()
        )
        new_key = base64.urlsafe_b64encode(os.urandom(32))
        new_cipher = Fernet(new_key)
        
        # Re-encrypt sensitive data
        # This is a placeholder - implement based on your database schema
        # Should iterate through encrypted columns and re-encrypt with new key
        
        # Save new key
        with open(self.key_file, 'w') as f:
            json.dump({
                "key": new_key.decode(),
                "salt": base64.b64encode(new_salt).decode(),
                "created_at": datetime.now().isoformat(),
                "rotated_at": datetime.now().isoformat()
            }, f, indent=2)
            
        self.cipher = new_cipher
        self.logger.info("Encryption key rotated successfully")
        
    def setup_access_control(self, rules: Dict[str, Dict]) -> None:
        """Set up access control rules.
        
        Args:
            rules: Dict mapping roles to allowed operations
        """
        rules_file = self.config_dir / "access_rules.json"
        with open(rules_file, 'w') as f:
            json.dump(rules, f, indent=2)
            
    def check_access(self, role: str, operation: str, resource: str) -> bool:
        """Check if a role has access to perform an operation.
        
        Args:
            role: Role requesting access
            operation: Operation to perform
            resource: Resource being accessed
            
        Returns:
            True if access is allowed, False otherwise
        """
        rules_file = self.config_dir / "access_rules.json"
        if not rules_file.exists():
            return False
            
        with open(rules_file) as f:
            rules = json.load(f)
            
        if role not in rules:
            return False
            
        role_rules = rules[role]
        if "resources" not in role_rules:
            return False
            
        resource_rules = role_rules["resources"]
        if resource not in resource_rules:
            return False
            
        allowed_operations = resource_rules[resource]
        return operation in allowed_operations
        
    def verify_integrity(self, table: str) -> bool:
        """Verify the integrity of a database table.
        
        Args:
            table: Table name to verify
            
        Returns:
            True if integrity check passes, False otherwise
        """
        try:
            # This is a placeholder - implement based on your database
            # Should:
            # 1. Check table structure
            # 2. Verify constraints
            # 3. Check for corruption
            # 4. Verify checksums if used
            
            return True
            
        except Exception as e:
            self.logger.error(f"Integrity check failed for table {table}: {str(e)}")
            return False
            
    def monitor_security_events(self) -> List[Dict]:
        """Monitor and report security-related events.
        
        Returns:
            List of security events/alerts
        """
        events = []
        try:
            # This is a placeholder - implement based on your needs
            # Should:
            # 1. Check for suspicious activity
            # 2. Monitor failed login attempts
            # 3. Track unusual access patterns
            # 4. Monitor for potential SQL injection
            # 5. Check for unusual data access
            
            return events
            
        except Exception as e:
            self.logger.error(f"Security monitoring failed: {str(e)}")
            return [{"type": "error", "message": str(e)}] 