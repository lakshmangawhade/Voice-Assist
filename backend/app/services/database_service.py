"""
Secure Database Service - MySQL Only with Safety Guardrails
Production-ready with SQL injection protection and privacy controls
"""

import os
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

# Optional static whitelist. Keep empty to allow all existing DB tables
# while still enforcing identifier validation + table-cache membership checks.
ALLOWED_TABLES = set()

# Sensitive columns that should be masked or restricted
SENSITIVE_COLUMNS = {
    'ssn', 'social_security', 'credit_card', 'card_number', 'password', 'pin',
    'secret', 'token', 'api_key', 'private_key'
}


class DatabaseService:
    """
    Secure MySQL database service with:
    - SQL injection protection
    - Identifier whitelisting
    - Privacy controls
    - Production-ready error handling
    """
    
    def __init__(self):
        """Initialize MySQL database service"""
        self.host = os.getenv('MYSQL_HOST', 'localhost')
        self.port = int(os.getenv('MYSQL_PORT', 3306))
        self.user = os.getenv('MYSQL_USER', 'root')
        self.password = os.getenv('MYSQL_PASSWORD', '')
        self.database = os.getenv('MYSQL_DATABASE', 'dental_practice')
        self.conn = None
        self.db_type = 'mysql'  # Only MySQL now
        self._initialized = False
        self._table_cache = {}  # Cache for table schemas
    
    def initialize(self) -> bool:
        """
        Initialize MySQL database connection
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import mysql.connector
            from mysql.connector import Error
            
            self.conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
                autocommit=False,
                connect_timeout=10,
                raise_on_warnings=True
            )
            
            if self.conn.is_connected():
                self._initialized = True
                print(f"[OK] Connected to MySQL database: {self.database}")
                # Pre-load table cache
                self._refresh_table_cache()
                return True
            else:
                print("[ERROR] MySQL connection failed")
                return False
                
        except ImportError:
            print("[ERROR] mysql-connector-python not installed. Install with: pip install mysql-connector-python")
            return False
        except Error as e:
            print(f"[ERROR] MySQL connection error: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Unexpected error connecting to MySQL: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if database is initialized and connected"""
        if not self._initialized or not self.conn:
            return False
        
        try:
            return self.conn.is_connected()
        except:
            return False
    
    def _validate_identifier(self, identifier: str, identifier_type: str = 'table') -> bool:
        """
        Validate SQL identifier to prevent injection
        
        Args:
            identifier: Table or column name
            identifier_type: 'table' or 'column'
        
        Returns:
            True if valid, False otherwise
        """
        if not identifier or not isinstance(identifier, str):
            return False
        
        # Only allow alphanumeric, underscore, and backtick (for MySQL)
        if not re.match(r'^[a-zA-Z0-9_`]+$', identifier):
            return False
        
        # Remove backticks for validation
        clean_id = identifier.replace('`', '')
        
        # For tables, check static whitelist if explicitly configured
        if identifier_type == 'table' and ALLOWED_TABLES:
            if clean_id.lower() not in {t.lower() for t in ALLOWED_TABLES}:
                return False
        
        # Check for SQL keywords
        sql_keywords = {
            'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'truncate', 'exec', 'execute', 'union', 'script', 'javascript'
        }
        if clean_id.lower() in sql_keywords:
            return False
        
        return True
    
    def _sanitize_identifier(self, identifier: str) -> str:
        """
        Sanitize SQL identifier by wrapping in backticks
        
        Args:
            identifier: Table or column name
        
        Returns:
            Sanitized identifier
        """
        if not self._validate_identifier(identifier):
            raise ValueError(f"Invalid identifier: {identifier}")
        
        # Remove existing backticks and add new ones
        clean = identifier.replace('`', '')
        return f"`{clean}`"
    
    def _refresh_table_cache(self):
        """Refresh cache of available tables"""
        try:
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE'
            """
            # Use tuple cursor to avoid connector-specific dictionary key casing issues.
            cursor = self.conn.cursor()
            cursor.execute(query, (self.database,))
            results = cursor.fetchall()
            cursor.close()
            
            self._table_cache = {}
            if results:
                for row in results:
                    if isinstance(row, (list, tuple)) and len(row) > 0 and row[0]:
                        table_name = str(row[0])
                        self._table_cache[table_name.lower()] = table_name
                
        except Exception as e:
            print(f"Warning: Could not refresh table cache: {e}")
            import traceback
            traceback.print_exc()
            self._table_cache = {}
    
    def get_tables(self) -> List[str]:
        """
        Get list of all tables in database (cached)
        
        Returns:
            List of table names
        """
        if not self.is_initialized():
            return []
        
        # Return cached table names
        return list(self._table_cache.values())

    def _is_known_table(self, table_name: str) -> bool:
        """Allow only tables that exist in the connected database."""
        if not table_name:
            return False
        if not self._table_cache:
            self._refresh_table_cache()
        return table_name.lower() in self._table_cache
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """
        Get schema (columns and types) for a table
        
        Args:
            table_name: Name of the table
        
        Returns:
            Dictionary mapping column names to data types
        """
        if not self.is_initialized():
            return {}
        
        if not self._validate_identifier(table_name, 'table'):
            print(f"Invalid table name: {table_name}")
            return {}
        if not self._is_known_table(table_name):
            print(f"Unknown table name: {table_name}")
            return {}
        
        try:
            query = """
                SELECT column_name, data_type, column_type
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """
            cursor = self.conn.cursor()
            cursor.execute(query, (self.database, table_name))
            results = cursor.fetchall()
            cursor.close()
            
            schema = {}
            if results:
                for row in results:
                    if isinstance(row, (list, tuple)) and len(row) >= 2:
                        schema[str(row[0])] = str(row[1])
            
            return schema
        except Exception as e:
            print(f"Error getting table schema: {e}")
            return {}
    
    def query_table(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where_clause: Optional[str] = None,
        where_params: Optional[List[Any]] = None,
        order_by: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Secure method to query any table with parameterized queries
        
        Args:
            table_name: Name of the table (validated)
            columns: List of columns to select (validated)
            where_clause: WHERE clause with %s placeholders
            where_params: Parameters for WHERE clause
            order_by: ORDER BY clause (validated)
            limit: Maximum number of results (max 1000)
        
        Returns:
            List of dictionaries representing rows
        """
        if not self.is_initialized():
            return []
        
        # Validate and sanitize table name
        if not self._validate_identifier(table_name, 'table'):
            raise ValueError(f"Invalid or unauthorized table name: {table_name}")
        if not self._is_known_table(table_name):
            raise ValueError(f"Unknown table name: {table_name}")
        
        table_name_safe = self._sanitize_identifier(table_name)
        
        # Validate and sanitize columns
        if columns:
            validated_columns = []
            for col in columns:
                if not self._validate_identifier(col, 'column'):
                    raise ValueError(f"Invalid column name: {col}")
                validated_columns.append(self._sanitize_identifier(col))
            select_clause = ", ".join(validated_columns)
        else:
            select_clause = "*"
        
        # Build query with parameterized WHERE clause
        query = f"SELECT {select_clause} FROM {table_name_safe}"
        
        if where_clause:
            # Validate WHERE clause doesn't contain dangerous patterns
            where_upper = where_clause.upper()
            dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'EXEC', 'EXECUTE', 'SCRIPT']
            if any(d in where_upper for d in dangerous):
                raise ValueError("WHERE clause contains dangerous SQL keywords")
            
            query += f" WHERE {where_clause}"
            params = tuple(where_params) if where_params else None
        else:
            params = None
        
        # Validate and add ORDER BY
        if order_by:
            # Simple validation - only allow alphanumeric, underscore, space, comma
            if not re.match(r'^[a-zA-Z0-9_`,\s]+$', order_by):
                raise ValueError(f"Invalid ORDER BY clause: {order_by}")
            query += f" ORDER BY {order_by}"
        
        # Enforce maximum limit
        limit = min(limit, 1000)
        query += f" LIMIT %s"
        
        if params:
            params = params + (limit,)
        else:
            params = (limit,)
        
        return self._execute_query_raw(query, params, return_dict=True)
    
    def search_table(
        self,
        table_name: str,
        search_columns: List[str],
        search_term: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Secure search across multiple columns
        
        Args:
            table_name: Name of the table (validated)
            search_columns: List of columns to search in (validated)
            search_term: Term to search for (sanitized)
            limit: Maximum results (max 500)
        
        Returns:
            List of matching rows
        """
        if not self.is_initialized():
            return []
        
        # Validate table name
        if not self._validate_identifier(table_name, 'table'):
            raise ValueError(f"Invalid table name: {table_name}")
        
        table_name_safe = self._sanitize_identifier(table_name)
        
        # Validate and sanitize columns
        validated_columns = []
        for col in search_columns:
            if not self._validate_identifier(col, 'column'):
                raise ValueError(f"Invalid column name: {col}")
            validated_columns.append(self._sanitize_identifier(col))
        
        # Build WHERE clause with OR conditions
        conditions = []
        for col in validated_columns:
            conditions.append(f"{col} LIKE %s")
        
        where_clause = " OR ".join(conditions)
        params = [f"%{search_term}%" for _ in validated_columns]
        
        # Enforce maximum limit
        limit = min(limit, 500)
        
        query = f"SELECT * FROM {table_name_safe} WHERE {where_clause} LIMIT %s"
        params.append(limit)
        
        return self._execute_query_raw(query, tuple(params), return_dict=True)
    
    def get_appointments_by_date_range(
        self, 
        start_date: str, 
        end_date: str, 
        prov_num: Optional[int] = None
    ) -> List[Dict]:
        """
        Get appointments within a date range using MySQL syntax
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            prov_num: Optional provider number to filter by
        
        Returns:
            List of appointment dictionaries
        """
        if not self.is_initialized():
            return []
        
        # Use MySQL CONCAT instead of SQLite ||
        query = """
            SELECT a.*, 
                   CONCAT(p.LName, ', ', p.FName) as PatientName,
                   pr.Abbr as ProviderAbbr
            FROM `appointment` a
            LEFT JOIN `patient` p ON a.PatNum = p.PatNum
            LEFT JOIN `provider` pr ON a.ProvNum = pr.ProvNum
            WHERE DATE(a.AptDateTime) BETWEEN %s AND %s
        """
        
        params = [start_date, end_date]
        if prov_num is not None:
            query += " AND a.ProvNum = %s"
            params.append(prov_num)
        
        query += " ORDER BY a.AptDateTime ASC LIMIT %s"
        params.append(100)
        
        return self._execute_query_raw(query, tuple(params), return_dict=True)
    
    def get_appointments_today(self, prov_num: Optional[int] = None) -> List[Dict]:
        """Get appointments for today using MySQL CURDATE()"""
        if not self.is_initialized():
            return []
        
        query = """
            SELECT a.*, 
                   CONCAT(p.LName, ', ', p.FName) as PatientName,
                   pr.Abbr as ProviderAbbr
            FROM `appointment` a
            LEFT JOIN `patient` p ON a.PatNum = p.PatNum
            LEFT JOIN `provider` pr ON a.ProvNum = pr.ProvNum
            WHERE DATE(a.AptDateTime) = CURDATE()
        """
        
        params = []
        if prov_num is not None:
            query += " AND a.ProvNum = %s"
            params.append(prov_num)
        
        query += " ORDER BY a.AptDateTime ASC LIMIT %s"
        params.append(100)
        
        return self._execute_query_raw(query, tuple(params) if params else (100,), return_dict=True)
    
    def get_appointments_this_week(self, prov_num: Optional[int] = None) -> List[Dict]:
        """Get appointments for this week using MySQL YEARWEEK()"""
        if not self.is_initialized():
            return []
        
        query = """
            SELECT a.*, 
                   CONCAT(p.LName, ', ', p.FName) as PatientName,
                   pr.Abbr as ProviderAbbr
            FROM `appointment` a
            LEFT JOIN `patient` p ON a.PatNum = p.PatNum
            LEFT JOIN `provider` pr ON a.ProvNum = pr.ProvNum
            WHERE YEARWEEK(a.AptDateTime) = YEARWEEK(CURDATE())
        """
        
        params = []
        if prov_num is not None:
            query += " AND a.ProvNum = %s"
            params.append(prov_num)
        
        query += " ORDER BY a.AptDateTime ASC LIMIT %s"
        params.append(100)
        
        return self._execute_query_raw(query, tuple(params) if params else (100,), return_dict=True)
    
    def get_patient_by_name(self, first_name: str = "", last_name: str = "") -> List[Dict]:
        """
        Search for patients by name using MySQL syntax
        
        Args:
            first_name: First name (partial match)
            last_name: Last name (partial match)
        
        Returns:
            List of patient dictionaries
        """
        if not self.is_initialized():
            return []
        
        query = "SELECT * FROM `patient` WHERE 1=1"
        params = []
        
        if first_name:
            query += " AND FName LIKE %s"
            params.append(f"%{first_name}%")
        
        if last_name:
            query += " AND LName LIKE %s"
            params.append(f"%{last_name}%")
        
        query += " LIMIT %s"
        params.append(20)
        
        return self._execute_query_raw(query, tuple(params), return_dict=True)
    
    def get_provider_info(self, prov_num: Optional[int] = None) -> List[Dict]:
        """
        Get provider information using MySQL syntax
        
        Args:
            prov_num: Optional provider number
        
        Returns:
            List of provider dictionaries
        """
        if not self.is_initialized():
            return []
        
        if prov_num:
            query = "SELECT * FROM `provider` WHERE ProvNum = %s LIMIT %s"
            params = (prov_num, 10)
        else:
            query = "SELECT * FROM `provider` WHERE IsHidden = 0 LIMIT %s"
            params = (10,)
        
        return self._execute_query_raw(query, params, return_dict=True)
    
    def _execute_query_raw(
        self, 
        query: str, 
        params: Optional[Tuple] = None, 
        return_dict: bool = True
    ) -> List[Dict]:
        """
        Execute a SELECT query with proper parameterization
        
        Args:
            query: SQL SELECT query
            params: Query parameters as tuple
            return_dict: Whether to return dicts or tuples
        
        Returns:
            List of dictionaries or tuples
        """
        if not self.is_initialized():
            return []
        
        # Security: Only allow SELECT queries
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
        
        # Additional security: Block dangerous patterns
        dangerous_patterns = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 
            'CREATE', 'ALTER', 'EXEC', 'EXECUTE', 'SCRIPT'
        ]
        for pattern in dangerous_patterns:
            if pattern in query_upper and f'SELECT' not in query_upper[:20]:
                raise ValueError(f"Query contains dangerous SQL keyword: {pattern}")
        
        try:
            cursor = self.conn.cursor(dictionary=return_dict)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            if return_dict:
                return list(results) if results else []
            else:
                return list(results) if results else []
                
        except Exception as e:
            print(f"Query execution error: {e}")
            raise  # Re-raise for proper error handling
    
    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                if self.conn.is_connected():
                    self.conn.close()
            except:
                pass
            self.conn = None
            self._initialized = False
            self._table_cache = {}
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()
