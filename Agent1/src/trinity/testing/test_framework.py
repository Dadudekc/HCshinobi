from typing import Any, Dict, List, Optional, Callable, Tuple
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

class SQLQueryBuilder:
    """Helper class for building SQL queries."""
    
    @staticmethod
    def build_select_count(table: str, where_clause: str = None, where_values: List = None) -> Tuple[str, List]:
        """Build a SELECT COUNT query.
        
        Args:
            table: Table name
            where_clause: Optional WHERE clause
            where_values: Values for WHERE clause placeholders
            
        Returns:
            Tuple of (query string, parameter values)
        """
        sql = f"SELECT COUNT(*) FROM {table}"
        values = where_values or []
        
        if where_clause:
            sql += f" WHERE {where_clause}"
            
        return sql, values
        
    @staticmethod
    def build_select(table: str, columns: List[str], where_clause: str = None, 
                    where_values: List = None, order_by: str = None) -> Tuple[str, List]:
        """Build a SELECT query.
        
        Args:
            table: Table name
            columns: Columns to select
            where_clause: Optional WHERE clause
            where_values: Values for WHERE clause placeholders
            order_by: Optional ORDER BY clause
            
        Returns:
            Tuple of (query string, parameter values)
        """
        sql = f"SELECT {', '.join(columns)} FROM {table}"
        values = where_values or []
        
        if where_clause:
            sql += f" WHERE {where_clause}"
            
        if order_by:
            sql += f" ORDER BY {order_by}"
            
        return sql, values
        
    @staticmethod
    def build_insert(table: str, columns: List[str]) -> str:
        """Build an INSERT query.
        
        Args:
            table: Table name
            columns: Column names
            
        Returns:
            INSERT query string
        """
        placeholders = ','.join(['?'] * len(columns))
        column_str = ','.join(columns)
        return f"INSERT INTO {table} ({column_str}) VALUES ({placeholders})"
        
    @staticmethod
    def build_conditions(conditions: Dict) -> Tuple[str, List]:
        """Build WHERE conditions from a dictionary.
        
        Args:
            conditions: Dict of column-value pairs
            
        Returns:
            Tuple of (WHERE clause string, parameter values)
        """
        where_clauses = []
        values = []
        
        for column, value in conditions.items():
            where_clauses.append(f"{column} = ?")
            values.append(value)
            
        where_sql = " AND ".join(where_clauses)
        return where_sql, values

class DatabaseTestFixture:
    """Manages test data and database state for testing."""
    
    class DatabaseError(Exception):
        """Base class for database test framework errors."""
        pass
        
    class ConnectionError(DatabaseError):
        """Raised when there are connection issues."""
        pass
        
    class TransactionError(DatabaseError):
        """Raised when there are transaction-related issues."""
        pass
        
    class FixtureError(DatabaseError):
        """Raised when there are fixture-related issues."""
        pass
        
    class SchemaError(DatabaseError):
        """Raised when there are schema validation issues."""
        pass
        
    class VersionError(DatabaseError):
        """Raised when there are version compatibility issues."""
        pass
        
    def __init__(self, connection, fixtures_dir: str = "test_fixtures", 
                 timeout: int = 30, max_retries: int = 3):
        """Initialize the test fixture manager.
        
        Args:
            connection: Database connection object
            fixtures_dir: Directory containing fixture files
            timeout: Connection timeout in seconds
            max_retries: Maximum number of connection retries
            
        Raises:
            ConnectionError: If connection is None or invalid
            SchemaError: If schema validation fails
            VersionError: If version compatibility check fails
        """
        if connection is None:
            raise self.ConnectionError("Database connection cannot be None")
            
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Validate database version
        try:
            version = self._get_database_version(connection)
            self._validate_version_compatibility(version)
        except Exception as e:
            raise self.VersionError(f"Version compatibility check failed: {str(e)}")
            
        # Validate schema
        try:
            self._validate_schema(connection)
        except Exception as e:
            raise self.SchemaError(f"Schema validation failed: {str(e)}")
            
        # Verify connection with retries
        for attempt in range(max_retries):
            try:
                connection.execute("SELECT 1")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise self.ConnectionError(f"Failed to establish connection after {max_retries} attempts: {str(e)}")
                continue
            
        self.connection = connection
        self.fixtures_dir = Path(fixtures_dir)
        self.fixtures_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self._state_stack = []
        self._tracked_tables = set()
        self._states = []
        self._in_transaction = False
        self._savepoints = []
        self._transaction_start_time = None
        self._memory_usage_threshold = 0.9  # 90% memory usage warning
        
    def _get_database_version(self, connection) -> str:
        """Get database version.
        
        Returns:
            Database version string
        """
        try:
            cursor = connection.execute("SELECT sqlite_version()")
            return cursor.fetchone()[0]
        except:
            # Fallback for other database types
            return "unknown"
            
    def _validate_version_compatibility(self, version: str) -> None:
        """Validate database version compatibility.
        
        Args:
            version: Database version string
            
        Raises:
            VersionError: If version is incompatible
        """
        # Add specific version checks based on requirements
        if version == "unknown":
            self.logger.warning("Unable to determine database version")
        else:
            # Example version check
            major_version = int(version.split('.')[0])
            if major_version < 3:
                raise self.VersionError(f"Database version {version} is not supported")
                
    def _validate_schema(self, connection) -> None:
        """Validate database schema.
        
        Raises:
            SchemaError: If schema validation fails
        """
        required_tables = {"users", "posts"}  # Example required tables
        existing_tables = set()
        
        try:
            cursor = connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
        except:
            # Fallback for other database types
            pass
            
        missing_tables = required_tables - existing_tables
        if missing_tables:
            raise self.SchemaError(f"Missing required tables: {missing_tables}")
            
    def _validate_table_exists(self, table: str) -> None:
        """Validate that a table exists in the database.
        
        Args:
            table: Table name to validate
            
        Raises:
            FixtureError: If table does not exist
        """
        sql, _ = SQLQueryBuilder.build_select_count(table)
        try:
            self.connection.execute(sql)
        except Exception as e:
            raise self.FixtureError(f"Table '{table}' does not exist: {str(e)}")
            
    def _validate_columns(self, table: str, columns: List[str]) -> None:
        """Validate that columns exist in the table.
        
        Args:
            table: Table name
            columns: List of column names to validate
            
        Raises:
            FixtureError: If any column does not exist
        """
        try:
            cursor = self.connection.execute(f"SELECT * FROM {table} LIMIT 1")
            valid_columns = {desc[0] for desc in cursor.description}
            
            invalid_columns = set(columns) - valid_columns
            if invalid_columns:
                raise self.FixtureError(
                    f"Invalid columns for table '{table}': {', '.join(invalid_columns)}"
                )
        except Exception as e:
            if not isinstance(e, self.FixtureError):
                raise self.FixtureError(f"Error validating columns: {str(e)}")
            raise
            
    def load_fixture(self, name: str) -> Dict:
        """Load test data from a fixture file.
        
        Args:
            name: Name of the fixture file (without .json extension)
            
        Returns:
            Dict containing the fixture data
        """
        fixture_path = self.fixtures_dir / f"{name}.json"
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {name}")
            
        with open(fixture_path) as f:
            return json.load(f)
            
    def save_fixture(self, name: str, data: Dict) -> None:
        """Save test data to a fixture file.
        
        Args:
            name: Name of the fixture file (without .json extension)
            data: Data to save
        """
        fixture_path = self.fixtures_dir / f"{name}.json"
        with open(fixture_path, 'w') as f:
            json.dump(data, f, indent=2)
            
    def _batch_insert_data(self, table: str, rows: List[Dict], batch_size: int = 100) -> None:
        """Insert test data into a table using batch operations.
        
        Args:
            table: Table name
            rows: List of row data to insert
            batch_size: Number of rows to insert in each batch
            
        Raises:
            FixtureError: If table or columns are invalid
        """
        if not rows:
            return
            
        self._validate_table_exists(table)
        self._tracked_tables.add(table)
        
        columns = list(rows[0].keys())
        self._validate_columns(table, columns)
        
        insert_sql = SQLQueryBuilder.build_insert(table, columns)
        
        try:
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                batch_values = [
                    [row[col] for col in columns]
                    for row in batch
                ]
                self.connection.executemany(insert_sql, batch_values)
        except Exception as e:
            raise self.FixtureError(f"Error batch inserting data into '{table}': {str(e)}")
            
    def setup_test_data(self, fixture_name: str, batch_size: int = 100) -> None:
        """Set up test data in the database from a fixture using batch operations.
        
        Args:
            fixture_name: Name of the fixture to load
            batch_size: Number of rows to insert in each batch
        """
        data = self.load_fixture(fixture_name)
        self._state_stack.append(self._get_current_state())
        
        for table, rows in data.items():
            self._batch_insert_data(table, rows, batch_size)
            
    def teardown_test_data(self) -> None:
        """Clean up test data and restore previous state."""
        if not self._state_stack:
            return
            
        previous_state = self._state_stack.pop()
        self._restore_state(previous_state)
        
    def _get_current_state(self) -> Dict:
        """Get current database state for the test tables.
        
        Returns:
            Dict containing current table data
        """
        state = {}
        for table in self._tracked_tables:
            cursor = self.connection.execute(f"SELECT * FROM {table}")
            columns = [desc[0] for desc in cursor.description]
            rows = []
            for row in cursor.fetchall():
                rows.append(dict(zip(columns, row)))
            state[table] = rows
        return state
        
    def _restore_state(self, state: Dict) -> None:
        """Restore database to a previous state.
        
        Args:
            state: Previous database state to restore
        """
        with self.transaction():
            # Clear current data
            for table in state.keys():
                self.connection.execute(f"DELETE FROM {table}")
                
            # Insert previous state
            for table, rows in state.items():
                self._insert_data(table, rows)
        
    def _insert_data(self, table: str, rows: List[Dict]) -> None:
        """Insert test data into a table.
        
        Args:
            table: Table name
            rows: List of row data to insert
            
        Raises:
            FixtureError: If table or columns are invalid
        """
        if not rows:
            return
            
        self._validate_table_exists(table)
        
        # Track this table for state management
        self._tracked_tables.add(table)
        
        # Get column names from first row
        columns = list(rows[0].keys())
        self._validate_columns(table, columns)
        
        insert_sql = SQLQueryBuilder.build_insert(table, columns)
        
        try:
            # Insert each row
            for row in rows:
                values = [row[col] for col in columns]
                self.connection.execute(insert_sql, values)
        except Exception as e:
            raise self.FixtureError(f"Error inserting data into '{table}': {str(e)}")
            
    def begin_transaction(self) -> None:
        """Begin a new transaction with timeout monitoring."""
        if self._in_transaction:
            raise self.TransactionError("Transaction already in progress")
            
        try:
            self.connection.execute("BEGIN TRANSACTION")
            self._in_transaction = True
            self._transaction_start_time = datetime.now()
        except Exception as e:
            raise self.ConnectionError(f"Error beginning transaction: {str(e)}")
            
    def _check_transaction_timeout(self) -> None:
        """Check if transaction has exceeded timeout."""
        if self._transaction_start_time:
            duration = (datetime.now() - self._transaction_start_time).total_seconds()
            if duration > self.timeout:
                self.logger.warning(f"Transaction timeout exceeded: {duration}s")
                
    def _monitor_memory_usage(self) -> None:
        """Monitor memory usage and log warnings."""
        try:
            import psutil
            memory = psutil.Process().memory_percent()
            if memory > self._memory_usage_threshold:
                self.logger.warning(f"High memory usage detected: {memory:.1f}%")
        except ImportError:
            pass  # psutil not available
            
    def commit_transaction(self) -> None:
        """Commit the current transaction.
        
        Raises:
            TransactionError: If no transaction is in progress
            ConnectionError: If connection error occurs
        """
        if not self._in_transaction:
            raise self.TransactionError("No transaction in progress")
            
        try:
            self.connection.execute("COMMIT")
            self._in_transaction = False
            self._savepoints.clear()
        except Exception as e:
            raise self.ConnectionError(f"Error committing transaction: {str(e)}")
            
    def rollback_transaction(self) -> None:
        """Rollback the current transaction.
        
        Raises:
            TransactionError: If no transaction is in progress
            ConnectionError: If connection error occurs
        """
        if not self._in_transaction:
            raise self.TransactionError("No transaction in progress")
            
        try:
            self.connection.execute("ROLLBACK")
            self._in_transaction = False
            self._savepoints.clear()
        except Exception as e:
            raise self.ConnectionError(f"Error rolling back transaction: {str(e)}")
            
    def create_savepoint(self, name: str) -> None:
        """Create a savepoint in the current transaction.
        
        Args:
            name: Savepoint name
        """
        if not self._in_transaction:
            raise RuntimeError("No transaction in progress")
            
        self.connection.execute(f"SAVEPOINT {name}")
        self._savepoints.append(name)
        
    def rollback_to_savepoint(self, name: str) -> None:
        """Rollback to a savepoint in the current transaction.
        
        Args:
            name: Savepoint name
        """
        if not self._in_transaction:
            raise RuntimeError("No transaction in progress")
            
        if name not in self._savepoints:
            raise ValueError(f"No savepoint named {name}")
            
        self.connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
        
        # Remove any savepoints created after this one
        index = self._savepoints.index(name)
        self._savepoints = self._savepoints[:index + 1]
        
    def release_savepoint(self, name: str) -> None:
        """Release a savepoint in the current transaction.
        
        Args:
            name: Savepoint name
        """
        if not self._in_transaction:
            raise RuntimeError("No transaction in progress")
            
        if name not in self._savepoints:
            raise ValueError(f"No savepoint named {name}")
            
        self.connection.execute(f"RELEASE SAVEPOINT {name}")
        self._savepoints.remove(name)
        
    @contextmanager
    def transaction(self):
        """Context manager for transaction handling.
        
        Yields:
            None
        
        Example:
            with fixture.transaction():
                # Do something in transaction
                pass  # Transaction automatically committed if no error
        """
        self.begin_transaction()
        try:
            yield
            self.commit_transaction()
        except:
            self.rollback_transaction()
            raise
            
    def verify_state(self, expected_state: Dict) -> bool:
        """Verify the database is in the expected state.
        
        Args:
            expected_state: Expected database state
            
        Returns:
            True if state matches, False otherwise
        """
        current_state = self._get_current_state()
        return current_state == expected_state
        
    def optimize_snapshot_comparison(self, snapshot_name: str, tables: List[str] = None) -> bool:
        """Optimized comparison of current state with a saved snapshot.
        
        Args:
            snapshot_name: Name of the snapshot to compare against
            tables: Optional list of specific tables to compare
            
        Returns:
            True if states match, False otherwise
            
        Raises:
            FileNotFoundError: If snapshot does not exist
        """
        snapshots = sorted(self.fixtures_dir.glob(f"snapshot_{snapshot_name}_*.json"))
        if not snapshots:
            raise FileNotFoundError(f"No snapshots found for: {snapshot_name}")
            
        latest_snapshot = snapshots[-1]
        with open(latest_snapshot) as f:
            snapshot_state = json.load(f)
            
        # If no specific tables provided, use all tracked tables
        tables_to_compare = tables or list(self._tracked_tables)
        
        for table in tables_to_compare:
            # Compare row counts first
            current_count = self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            snapshot_count = len(snapshot_state.get(table, []))
            
            if current_count != snapshot_count:
                return False
                
            # If counts match, compare actual data
            cursor = self.connection.execute(f"SELECT * FROM {table} ORDER BY ROWID")
            columns = [desc[0] for desc in cursor.description]
            
            for i, row in enumerate(cursor):
                current_row = dict(zip(columns, row))
                snapshot_row = snapshot_state[table][i]
                
                if current_row != snapshot_row:
                    return False
                    
        return True
        
    def create_snapshot(self, name: str, tables: List[str] = None) -> None:
        """Create a named snapshot of the current database state.
        
        Args:
            name: Name for the snapshot
            tables: Optional list of specific tables to snapshot
        """
        state = {}
        tables_to_snapshot = tables or self._tracked_tables
        
        for table in tables_to_snapshot:
            cursor = self.connection.execute(f"SELECT * FROM {table} ORDER BY ROWID")
            columns = [desc[0] for desc in cursor.description]
            rows = []
            
            # Fetch rows in batches for memory efficiency
            while True:
                batch = cursor.fetchmany(1000)
                if not batch:
                    break
                rows.extend([dict(zip(columns, row)) for row in batch])
                
            state[table] = rows
            
        snapshot_path = self.fixtures_dir / f"snapshot_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(snapshot_path, 'w') as f:
            json.dump(state, f, indent=2)
            
    def compare_with_snapshot(self, snapshot_name: str) -> bool:
        """Compare current state with a saved snapshot.
        
        Args:
            snapshot_name: Name of the snapshot to compare against
            
        Returns:
            True if states match, False otherwise
        """
        snapshots = sorted(self.fixtures_dir.glob(f"snapshot_{snapshot_name}_*.json"))
        if not snapshots:
            raise FileNotFoundError(f"No snapshots found for: {snapshot_name}")
            
        latest_snapshot = snapshots[-1]
        with open(latest_snapshot) as f:
            snapshot_state = json.load(f)
            
        return self.verify_state(snapshot_state)

    def verify_database_consistency(self) -> None:
        """Verify database consistency with enhanced checks.
        
        Raises:
            ConnectionError: If consistency check fails
        """
        try:
            # Basic consistency check
            self.connection.execute("PRAGMA integrity_check")
            self.connection.execute("PRAGMA foreign_key_check")
            
            # Check for deadlocks
            self.connection.execute("PRAGMA lock_status")
            
            # Check for long-running transactions
            self._check_transaction_timeout()
            
            # Monitor memory usage
            self._monitor_memory_usage()
            
        except Exception as e:
            raise self.ConnectionError(f"Database consistency check failed: {str(e)}")

class DatabaseTestCase:
    """Base class for database tests with fixture support."""
    
    def __init__(self, connection):
        """Initialize the test case.
        
        Args:
            connection: Database connection object
        """
        self.connection = connection
        self.fixture = DatabaseTestFixture(connection)
        
    def setUp(self) -> None:
        """Set up test environment."""
        pass
        
    def tearDown(self) -> None:
        """Clean up test environment."""
        self.fixture.teardown_test_data()
        
    def assertDatabaseState(self, expected_state: Dict, msg: str = None) -> None:
        """Assert that the database is in the expected state.
        
        Args:
            expected_state: Expected database state
            msg: Optional assertion message
        """
        if not self.fixture.verify_state(expected_state):
            raise AssertionError(msg or "Database state does not match expected state")
            
    def assert_row_count(self, table: str, expected_count: int, where_clause: str = None) -> None:
        """Assert that a table has the expected number of rows.
        
        Args:
            table: Table name
            expected_count: Expected number of rows
            where_clause: Optional WHERE clause for filtering
        """
        sql, values = SQLQueryBuilder.build_select_count(table, where_clause)
        cursor = self.connection.execute(sql, values)
        actual_count = cursor.fetchone()[0]
        
        assert actual_count == expected_count, \
            f"Expected {expected_count} rows in {table}, but found {actual_count}"
            
    def assert_row_exists(self, table: str, conditions: Dict) -> None:
        """Assert that a row matching conditions exists.
        
        Args:
            table: Table name
            conditions: Dict of column-value pairs to match
        """
        where_sql, values = SQLQueryBuilder.build_conditions(conditions)
        sql, _ = SQLQueryBuilder.build_select_count(table, where_sql)
        
        cursor = self.connection.execute(sql, values)
        count = cursor.fetchone()[0]
        
        assert count > 0, \
            f"No row found in {table} matching conditions: {conditions}"
            
    def assert_row_not_exists(self, table: str, conditions: Dict) -> None:
        """Assert that no row matching conditions exists.
        
        Args:
            table: Table name
            conditions: Dict of column-value pairs to match
        """
        where_sql, values = SQLQueryBuilder.build_conditions(conditions)
        sql, _ = SQLQueryBuilder.build_select_count(table, where_sql)
        
        cursor = self.connection.execute(sql, values)
        count = cursor.fetchone()[0]
        
        assert count == 0, \
            f"Found {count} rows in {table} matching conditions: {conditions}"
            
    def assert_column_value(self, table: str, column: str, expected_value: Any, 
                          where_clause: str = None, where_values: List = None) -> None:
        """Assert that a column has the expected value.
        
        Args:
            table: Table name
            column: Column name
            expected_value: Expected column value
            where_clause: Optional WHERE clause for filtering
            where_values: Values for WHERE clause placeholders
        """
        sql, values = SQLQueryBuilder.build_select(table, [column], where_clause, where_values)
        cursor = self.connection.execute(sql, values)
        row = cursor.fetchone()
        
        assert row is not None, f"No row found in {table}"
        actual_value = row[0]
        
        assert actual_value == expected_value, \
            f"Expected {column} to be {expected_value}, but was {actual_value}"

    def assert_transaction_state(self, expected_in_transaction: bool) -> None:
        """Assert that the transaction state matches the expected state.
        
        Args:
            expected_in_transaction: Expected transaction state
        """
        actual_state = self.fixture._in_transaction
        assert actual_state == expected_in_transaction, \
            f"Expected transaction state to be {expected_in_transaction}, but was {actual_state}"
            
    def assert_savepoint_exists(self, savepoint_name: str) -> None:
        """Assert that a savepoint exists.
        
        Args:
            savepoint_name: Name of the savepoint to check
        """
        assert savepoint_name in self.fixture._savepoints, \
            f"Expected savepoint '{savepoint_name}' to exist"
            
    def assert_savepoint_count(self, expected_count: int) -> None:
        """Assert the number of active savepoints.
        
        Args:
            expected_count: Expected number of savepoints
        """
        actual_count = len(self.fixture._savepoints)
        assert actual_count == expected_count, \
            f"Expected {expected_count} savepoints, but found {actual_count}"
            
    def test_transaction_management(self) -> None:
        """Test transaction management functionality."""
        # Test basic transaction
        self.fixture.begin_transaction()
        self.assert_transaction_state(True)
        
        # Test savepoint creation
        self.fixture.create_savepoint("sp1")
        self.assert_savepoint_exists("sp1")
        self.assert_savepoint_count(1)
        
        # Test multiple savepoints
        self.fixture.create_savepoint("sp2")
        self.assert_savepoint_count(2)
        
        # Test rollback to savepoint
        self.fixture.rollback_to_savepoint("sp1")
        self.assert_savepoint_count(1)
        
        # Test commit
        self.fixture.commit_transaction()
        self.assert_transaction_state(False)
        self.assert_savepoint_count(0)
        
    def test_transaction_context_manager(self) -> None:
        """Test transaction context manager functionality."""
        # Test successful transaction
        with self.fixture.transaction():
            self.assert_transaction_state(True)
            self.fixture.create_savepoint("sp1")
            self.assert_savepoint_exists("sp1")
        self.assert_transaction_state(False)
        self.assert_savepoint_count(0)
        
        # Test transaction rollback on error
        try:
            with self.fixture.transaction():
                self.assert_transaction_state(True)
                raise Exception("Test error")
        except Exception:
            self.assert_transaction_state(False)
            self.assert_savepoint_count(0)
            
    def test_nested_transactions(self) -> None:
        """Test nested transaction handling."""
        self.fixture.begin_transaction()
        try:
            # Should raise an error
            self.fixture.begin_transaction()
            assert False, "Expected RuntimeError for nested transaction"
        except RuntimeError:
            pass
        finally:
            self.fixture.rollback_transaction()
            
        self.assert_transaction_state(False)
        self.assert_savepoint_count(0)

    def assert_snapshot_exists(self, snapshot_name: str) -> None:
        """Assert that a snapshot exists.
        
        Args:
            snapshot_name: Name of the snapshot to check
        """
        snapshots = list(self.fixture.fixtures_dir.glob(f"snapshot_{snapshot_name}_*.json"))
        assert len(snapshots) > 0, f"No snapshots found with name: {snapshot_name}"
        
    def assert_matches_snapshot(self, snapshot_name: str, msg: str = None) -> None:
        """Assert that current state matches a snapshot.
        
        Args:
            snapshot_name: Name of the snapshot to compare against
            msg: Optional assertion message
        """
        assert self.fixture.compare_with_snapshot(snapshot_name), \
            msg or f"Current state does not match snapshot: {snapshot_name}"
            
    def test_snapshot_management(self) -> None:
        """Test snapshot creation and comparison functionality."""
        test_data = {
            "users": [
                {"id": 1, "name": "Test User 1"},
                {"id": 2, "name": "Test User 2"}
            ]
        }
        
        # Set up initial state
        with self.fixture.transaction():
            self.fixture._insert_data("users", test_data["users"])
            
        # Create snapshot
        snapshot_name = "test_snapshot"
        self.fixture.create_snapshot(snapshot_name)
        self.assert_snapshot_exists(snapshot_name)
        
        # Verify initial state matches
        self.assert_matches_snapshot(snapshot_name)
        
        # Modify data
        with self.fixture.transaction():
            self.connection.execute("UPDATE users SET name = ? WHERE id = ?", 
                                 ["Modified User", 1])
                                 
        # Should not match snapshot after modification
        try:
            self.assert_matches_snapshot(snapshot_name)
            assert False, "Expected snapshot mismatch after modification"
        except AssertionError:
            pass
            
        # Restore to snapshot state
        with self.fixture.transaction():
            self.fixture._insert_data("users", test_data["users"])
            
        # Should match snapshot again
        self.assert_matches_snapshot(snapshot_name)
        
    def test_snapshot_comparison_edge_cases(self) -> None:
        """Test snapshot comparison with edge cases."""
        # Test empty state
        snapshot_name = "empty_snapshot"
        self.fixture.create_snapshot(snapshot_name)
        self.assert_matches_snapshot(snapshot_name)
        
        # Test with special characters in data
        special_data = {
            "users": [
                {"id": 1, "name": "User 'with' \"quotes\""},
                {"id": 2, "name": "User with \n newline"}
            ]
        }
        
        with self.fixture.transaction():
            self.fixture._insert_data("users", special_data["users"])
            
        special_snapshot = "special_chars"
        self.fixture.create_snapshot(special_snapshot)
        self.assert_matches_snapshot(special_snapshot)
        
        # Test non-existent snapshot
        try:
            self.assert_matches_snapshot("non_existent")
            assert False, "Expected error for non-existent snapshot"
        except FileNotFoundError:
            pass

    def test_fixture_loading_and_saving(self) -> None:
        """Integration test for fixture loading and saving."""
        # Test data with various data types and special characters
        test_data = {
            "users": [
                {"id": 1, "name": "Test User", "active": True, "score": 10.5},
                {"id": 2, "name": "User with 'quotes'", "active": False, "score": None}
            ],
            "posts": [
                {"id": 1, "user_id": 1, "title": "First \"post\"", "content": "Content\nwith\nnewlines"},
                {"id": 2, "user_id": 1, "title": "Second post", "content": "Regular content"}
            ]
        }
        
        # Save test data as fixture
        fixture_name = "integration_test"
        self.fixture.save_fixture(fixture_name, test_data)
        
        # Verify fixture was saved correctly
        loaded_data = self.fixture.load_fixture(fixture_name)
        assert loaded_data == test_data, "Loaded fixture data does not match saved data"
        
        # Test batch loading with different batch sizes
        batch_sizes = [1, 2, 50]  # Test different batch scenarios
        for batch_size in batch_sizes:
            # Clear previous data
            with self.fixture.transaction():
                self.connection.execute("DELETE FROM users")
                self.connection.execute("DELETE FROM posts")
                
            # Load fixture with current batch size
            self.fixture.setup_test_data(fixture_name, batch_size)
            
            # Verify data was loaded correctly
            self.assert_row_count("users", len(test_data["users"]))
            self.assert_row_count("posts", len(test_data["posts"]))
            
            # Verify specific records
            self.assert_row_exists("users", {"id": 1, "name": "Test User"})
            self.assert_row_exists("posts", {"id": 2, "title": "Second post"})
            
    def test_large_dataset_performance(self) -> None:
        """Test performance with larger datasets."""
        # Generate larger test dataset
        large_data = {
            "users": [
                {"id": i, "name": f"User {i}", "active": i % 2 == 0, "score": float(i)}
                for i in range(1, 1001)  # 1000 users
            ],
            "posts": [
                {"id": i, "user_id": (i % 100) + 1, "title": f"Post {i}", "content": f"Content {i}"}
                for i in range(1, 5001)  # 5000 posts
            ]
        }
        
        fixture_name = "large_dataset"
        self.fixture.save_fixture(fixture_name, large_data)
        
        # Test loading with different batch sizes and measure performance
        batch_sizes = [10, 100, 500]
        for batch_size in batch_sizes:
            # Clear previous data
            with self.fixture.transaction():
                self.connection.execute("DELETE FROM users")
                self.connection.execute("DELETE FROM posts")
                
            # Load and verify data
            start_time = datetime.now()
            self.fixture.setup_test_data(fixture_name, batch_size)
            end_time = datetime.now()
            
            # Log performance metrics
            duration = (end_time - start_time).total_seconds()
            self.logger.info(f"Batch size {batch_size}: Loaded {len(large_data['users'])} users and "
                           f"{len(large_data['posts'])} posts in {duration:.2f} seconds")
            
            # Verify data integrity
            self.assert_row_count("users", len(large_data["users"]))
            self.assert_row_count("posts", len(large_data["posts"]))
            
    def test_snapshot_optimization(self) -> None:
        """Test optimized snapshot functionality."""
        # Set up test data
        test_data = {
            "users": [{"id": i, "name": f"User {i}"} for i in range(1, 101)],
            "posts": [{"id": i, "title": f"Post {i}"} for i in range(1, 201)]
        }
        
        with self.fixture.transaction():
            for table, rows in test_data.items():
                self.fixture._batch_insert_data(table, rows)
                
        # Test full snapshot
        self.fixture.create_snapshot("full_snapshot")
        assert self.fixture.optimize_snapshot_comparison("full_snapshot"), \
            "Full snapshot comparison failed"
            
        # Test partial snapshot
        self.fixture.create_snapshot("users_only", ["users"])
        assert self.fixture.optimize_snapshot_comparison("users_only", ["users"]), \
            "Partial snapshot comparison failed"
            
        # Test snapshot after modifications
        with self.fixture.transaction():
            self.connection.execute("UPDATE users SET name = ? WHERE id = ?", 
                                 ["Modified User", 1])
                                 
        assert not self.fixture.optimize_snapshot_comparison("full_snapshot"), \
            "Snapshot should not match after modification"
            
        # Test performance with large dataset
        large_data = {
            "users": [{"id": i, "name": f"User {i}"} for i in range(1, 10001)]
        }
        
        with self.fixture.transaction():
            self.connection.execute("DELETE FROM users")
            self.fixture._batch_insert_data("users", large_data["users"], batch_size=500)
            
        start_time = datetime.now()
        self.fixture.create_snapshot("large_snapshot")
        create_duration = (datetime.now() - start_time).total_seconds()
        
        start_time = datetime.now()
        assert self.fixture.optimize_snapshot_comparison("large_snapshot"), \
            "Large snapshot comparison failed"
        compare_duration = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(f"Large snapshot metrics - Create: {create_duration:.2f}s, "
                        f"Compare: {compare_duration:.2f}s")

class DatabaseTestRunner:
    """Runs database tests with setup and teardown support."""
    
    def __init__(self, connection_factory: Callable[[], Any], pool_size: int = 5,
                 max_wait_time: int = 30, connection_timeout: int = 10):
        """Initialize the test runner with enhanced connection management.
        
        Args:
            connection_factory: Function that creates database connections
            pool_size: Maximum number of connections in the pool
            max_wait_time: Maximum time to wait for a connection in seconds
            connection_timeout: Connection timeout in seconds
        """
        self.connection_factory = connection_factory
        self.pool_size = pool_size
        self.max_wait_time = max_wait_time
        self.connection_timeout = connection_timeout
        self.logger = logging.getLogger(__name__)
        self._connection_pool = []
        self._active_connections = set()
        self._metrics = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "total_time": 0.0,
            "avg_test_time": 0.0,
            "connection_reuse_rate": 0.0,
            "connection_errors": 0,
            "peak_connections": 0,
            "connection_wait_times": [],
            "deadlock_count": 0,
            "timeout_count": 0
        }
        
    def _update_metrics(self, test_time: float, reused_connection: bool, had_error: bool) -> None:
        """Update performance metrics.
        
        Args:
            test_time: Time taken to run the test
            reused_connection: Whether a connection was reused
            had_error: Whether there was an error
        """
        self._metrics["total_tests"] += 1
        self._metrics["total_time"] += test_time
        self._metrics["avg_test_time"] = self._metrics["total_time"] / self._metrics["total_tests"]
        
        if reused_connection:
            self._metrics["connection_reuse_rate"] = (
                self._metrics["connection_reuse_rate"] * (self._metrics["total_tests"] - 1) + 1
            ) / self._metrics["total_tests"]
            
        if had_error:
            self._metrics["connection_errors"] += 1
            
        current_connections = len(self._active_connections)
        self._metrics["peak_connections"] = max(self._metrics["peak_connections"], current_connections)
        
    def get_performance_report(self) -> Dict:
        """Get a detailed performance report.
        
        Returns:
            Dict containing performance metrics
        """
        return {
            "test_metrics": {
                "total_tests": self._metrics["total_tests"],
                "passed_tests": self._metrics["passed_tests"],
                "failed_tests": self._metrics["failed_tests"],
                "success_rate": (
                    self._metrics["passed_tests"] / self._metrics["total_tests"]
                    if self._metrics["total_tests"] > 0 else 0
                )
            },
            "timing_metrics": {
                "total_time": f"{self._metrics['total_time']:.2f}s",
                "avg_test_time": f"{self._metrics['avg_test_time']:.2f}s"
            },
            "connection_metrics": {
                "pool_size": self.pool_size,
                "active_connections": len(self._active_connections),
                "pooled_connections": len(self._connection_pool),
                "peak_connections": self._metrics["peak_connections"],
                "connection_reuse_rate": f"{self._metrics['connection_reuse_rate']*100:.1f}%",
                "connection_errors": self._metrics["connection_errors"]
            }
        }
        
    def _get_connection(self) -> Any:
        """Get a connection from the pool with timeout and retry logic."""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < self.max_wait_time:
            # Try to get connection from pool
            while self._connection_pool:
                connection = self._connection_pool.pop()
                try:
                    # Verify connection is still valid
                    connection.execute("SELECT 1")
                    self._active_connections.add(connection)
                    return connection
                except Exception:
                    self.logger.warning("Removing invalid connection from pool")
                    continue
                    
            # Create new connection if pool is not full
            if len(self._active_connections) < self.pool_size:
                try:
                    connection = self.connection_factory()
                    # Set timeout if supported
                    try:
                        connection.execute(f"PRAGMA busy_timeout = {self.connection_timeout * 1000}")
                    except:
                        pass
                    self._active_connections.add(connection)
                    return connection
                except Exception as e:
                    self.logger.error(f"Failed to create connection: {str(e)}")
                    
        self._metrics["timeout_count"] += 1
        raise RuntimeError(f"Failed to get connection within {self.max_wait_time} seconds")
        
    def _return_connection(self, connection: Any) -> None:
        """Return a connection to the pool.
        
        Args:
            connection: Database connection to return
        """
        if connection in self._active_connections:
            self._active_connections.remove(connection)
            try:
                # Verify connection is still valid before returning to pool
                connection.execute("SELECT 1")
                self._connection_pool.append(connection)
            except Exception:
                self.logger.warning("Discarding invalid connection")
                try:
                    connection.close()
                except:
                    pass
                    
    def run_test(self, test_case: DatabaseTestCase) -> bool:
        """Run a single test case.
        
        Args:
            test_case: Test case to run
            
        Returns:
            True if test passed, False otherwise
        """
        connection = None
        start_time = datetime.now()
        reused_connection = False
        had_error = False
        
        try:
            connection = self._get_connection()
            reused_connection = len(self._connection_pool) > 0
            test_case.connection = connection
            
            test_case.setUp()
            test_case.run()
            self._metrics["passed_tests"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self._metrics["failed_tests"] += 1
            had_error = True
            return False
            
        finally:
            test_case.tearDown()
            if connection:
                self._return_connection(connection)
                
            end_time = datetime.now()
            test_time = (end_time - start_time).total_seconds()
            self._update_metrics(test_time, reused_connection, had_error)
            
    def run_tests(self, test_cases: List[DatabaseTestCase]) -> Dict:
        """Run multiple test cases.
        
        Args:
            test_cases: List of test cases to run
            
        Returns:
            Dict containing test results and performance metrics
        """
        results = {
            "total": len(test_cases),
            "passed": 0,
            "failed": 0,
            "failures": [],
            "errors": []
        }
        
        start_time = datetime.now()
        
        for test_case in test_cases:
            try:
                if self.run_test(test_case):
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    results["failures"].append({
                        "test": test_case.__class__.__name__,
                        "method": test_case._testMethodName
                    })
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "test": test_case.__class__.__name__,
                    "error": str(e)
                })
                
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Add performance metrics to results
        results["performance"] = self.get_performance_report()
        results["total_time"] = f"{total_time:.2f}s"
        results["avg_test_time"] = f"{total_time/len(test_cases):.2f}s"
        
        return results
        
    def cleanup(self) -> None:
        """Clean up all database connections."""
        # Close all active connections
        for conn in self._active_connections:
            try:
                conn.close()
            except:
                pass
        self._active_connections.clear()
        
        # Close all pooled connections
        while self._connection_pool:
            try:
                self._connection_pool.pop().close()
            except:
                pass 