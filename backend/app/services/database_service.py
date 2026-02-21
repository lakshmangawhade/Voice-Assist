"""
Database Service for loading SQL data and executing queries
Uses SQLite for lightweight, file-based database
"""

import sqlite3
import re
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, date


class DatabaseService:
    """Service for managing database connections and queries"""
    
    def __init__(self, sql_file_path: Optional[str] = None, db_path: Optional[str] = None):
        """
        Initialize database service
        
        Args:
            sql_file_path: Path to the SQL dump file
            db_path: Path to SQLite database file (defaults to data/dental_practice.db)
        """
        backend_dir = Path(__file__).parent.parent.parent
        self.sql_file_path = sql_file_path or str(backend_dir / "data" / "data.sql")
        
        if db_path is None:
            db_dir = backend_dir / "data"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "dental_practice.db")
        
        self.db_path = db_path
        self.conn = None
        self._initialized = False
    
    def initialize_database(self) -> bool:
        """
        Parse SQL file and initialize database
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create connection
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
            
            # Read SQL file
            if not os.path.exists(self.sql_file_path):
                print(f"SQL file not found: {self.sql_file_path}")
                return False
            
            with open(self.sql_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                sql_content = f.read()
            
            # Execute SQL statements
            self._execute_sql_statements(sql_content)
            
            self._initialized = True
            print(f"Database initialized successfully at {self.db_path}")
            return True
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _execute_sql_statements(self, sql_content: str):
        """Execute SQL statements, converting MySQL to SQLite syntax"""
        cursor = self.conn.cursor()
        
        # Use regex-based parsing for CREATE TABLE (more reliable)
        import re
        
        statements = []
        processed_tables = set()
        
        # Find all CREATE TABLE statements using regex (handles multiline)
        create_table_pattern = r'CREATE TABLE\s+`?(\w+)`?\s*\((.*?)\)\s*ENGINE'
        create_matches = re.finditer(create_table_pattern, sql_content, re.DOTALL | re.IGNORECASE)
        
        for match in create_matches:
            table_name = match.group(1)
            table_def = match.group(2)
            
            # Reconstruct CREATE TABLE statement
            full_sql = f"CREATE TABLE {table_name} ({table_def})"
            
            # Convert to SQLite
            converted = self._convert_mysql_to_sqlite(full_sql)
            if converted and table_name not in processed_tables:
                statements.append(converted)
                processed_tables.add(table_name)
        
        # Find INSERT statements (line by line for better reliability)
        for line in sql_content.split('\n'):
            stripped = line.strip()
            if 'INSERT INTO' in stripped.upper() and 'VALUES' in stripped.upper():
                # Extract table name and values
                match = re.search(r'INSERT INTO\s+`?(\w+)`?\s+VALUES\s+(.+)', stripped, re.IGNORECASE)
                if match:
                    table_name = match.group(1)
                    values = match.group(2).rstrip(';').rstrip()
                    # Only process INSERT if table exists
                    if table_name in processed_tables:
                        insert_sql = f"INSERT INTO {table_name} VALUES {values}"
                        converted = self._convert_insert_statement(insert_sql)
                        if converted:
                            statements.append(converted)
        
        # Execute CREATE TABLE statements first
        create_statements = [s for s in statements if s.strip().upper().startswith('CREATE TABLE')]
        insert_statements = [s for s in statements if s.strip().upper().startswith('INSERT INTO')]
        
        print(f"Found {len(create_statements)} CREATE TABLE statements to execute")
        print(f"Found {len(insert_statements)} INSERT statements to execute")
        
        # Execute CREATE statements
        successful_tables = []
        error_count = 0
        for stmt in create_statements:
            try:
                if stmt.strip():
                    cursor.execute(stmt)
                    # Extract table name to track success
                    match = re.search(r'CREATE TABLE\s+(\w+)', stmt, re.IGNORECASE)
                    if match:
                        successful_tables.append(match.group(1))
            except sqlite3.Error as e:
                error_msg = str(e).lower()
                if "already exists" not in error_msg:
                    error_count += 1
                    # Print first 5 errors for debugging
                    if error_count <= 5:
                        match = re.search(r'CREATE TABLE\s+(\w+)', stmt, re.IGNORECASE)
                        table_name = match.group(1) if match else "unknown"
                        print(f"Error creating table {table_name}: {e}")
                        if error_count == 5:
                            print(f"  ... (suppressing further errors)")
        
        self.conn.commit()
        print(f"Successfully created {len(successful_tables)} tables")
        
        # Execute INSERT statements in batches for efficiency
        insert_count = 0
        for stmt in insert_statements:
            try:
                if stmt.strip():
                    cursor.execute(stmt)
                    insert_count += 1
                    # Commit every 1000 inserts
                    if insert_count % 1000 == 0:
                        self.conn.commit()
            except sqlite3.Error as e:
                error_msg = str(e).lower()
                if "no such table" not in error_msg and "UNIQUE constraint" not in error_msg:
                    # Skip expected errors
                    pass
        
        self.conn.commit()
        print(f"Inserted {insert_count} records")
    
    def _convert_mysql_to_sqlite(self, sql: str) -> Optional[str]:
        """Convert MySQL CREATE TABLE syntax to SQLite"""
        # Remove MySQL-specific syntax
        sql = re.sub(r'\bAUTO_INCREMENT\b', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'ENGINE=\w+.*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'DEFAULT CHARSET=\w+.*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'ON UPDATE CURRENT_TIMESTAMP', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'CURRENT_TIMESTAMP', "datetime('now')", sql, flags=re.IGNORECASE)
        sql = re.sub(r'bigint\(20\)', 'INTEGER', sql, flags=re.IGNORECASE)
        sql = re.sub(r'int\(11\)', 'INTEGER', sql, flags=re.IGNORECASE)
        sql = re.sub(r'tinyint\([^)]+\)', 'INTEGER', sql, flags=re.IGNORECASE)
        sql = re.sub(r'smallint\([^)]+\)', 'INTEGER', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bdouble\b', 'REAL', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bunsigned\b', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'date\s+NOT NULL', 'TEXT NOT NULL', sql, flags=re.IGNORECASE)
        sql = re.sub(r'date\s+DEFAULT', 'TEXT DEFAULT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'date\s*,', 'TEXT,', sql, flags=re.IGNORECASE)
        sql = re.sub(r'date\s*\)', 'TEXT)', sql, flags=re.IGNORECASE)
        sql = re.sub(r'datetime\s+NOT NULL', 'TEXT NOT NULL', sql, flags=re.IGNORECASE)
        sql = re.sub(r'datetime\s+DEFAULT', 'TEXT DEFAULT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'datetime\s*,', 'TEXT,', sql, flags=re.IGNORECASE)
        sql = re.sub(r'datetime\s*\)', 'TEXT)', sql, flags=re.IGNORECASE)
        sql = re.sub(r'timestamp\s+NOT NULL', 'TEXT NOT NULL', sql, flags=re.IGNORECASE)
        sql = re.sub(r'timestamp\s+DEFAULT', 'TEXT DEFAULT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'text\s+NOT NULL', 'TEXT NOT NULL', sql, flags=re.IGNORECASE)
        sql = re.sub(r'varchar\([^)]+\)', 'TEXT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'char\([^)]+\)', 'TEXT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'`', '', sql)  # Remove backticks
        
        # Remove KEY constraints (SQLite doesn't support them in CREATE TABLE)
        # Keep PRIMARY KEY but remove other KEY definitions
        sql = re.sub(r',\s*KEY\s+\w+\s*\([^)]+\)', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s+KEY\s+\w+\s*\([^)]+\)', '', sql, flags=re.IGNORECASE)
        
        # Handle PRIMARY KEY - move it to column definition if it's separate
        # First, handle INTEGER PRIMARY KEY AUTOINCREMENT pattern
        sql = re.sub(r'(\w+)\s+INTEGER\s+NOT NULL\s+PRIMARY KEY', r'\1 INTEGER PRIMARY KEY', sql, flags=re.IGNORECASE)
        
        # Clean up extra commas and spaces (but preserve newlines in table definition)
        sql = re.sub(r',\s*,+', ',', sql)  # Remove multiple commas
        sql = re.sub(r',\s*\)', ')', sql)  # Remove trailing comma before closing paren
        sql = re.sub(r'\s+', ' ', sql)  # Normalize whitespace to single spaces
        sql = re.sub(r'\s*,\s*', ', ', sql)  # Normalize comma spacing
        sql = re.sub(r'\(\s+', '(', sql)  # Remove space after opening paren
        sql = re.sub(r'\s+\)', ')', sql)  # Remove space before closing paren
        
        # Fix PRIMARY KEY syntax - ensure it's properly formatted
        sql = re.sub(r',\s*PRIMARY KEY\s*\(([^)]+)\)', r', PRIMARY KEY (\1)', sql, flags=re.IGNORECASE)
        
        # Only return if it's a valid CREATE TABLE statement
        if 'CREATE TABLE' in sql.upper():
            return sql
        return None
    
    def _convert_insert_statement(self, sql: str) -> Optional[str]:
        """Convert MySQL INSERT statement to SQLite"""
        # Remove backticks
        sql = sql.replace('`', '')
        # Remove MySQL-specific syntax
        sql = re.sub(r'/\*.*?\*/', '', sql)  # Remove comments
        return sql if 'INSERT INTO' in sql.upper() else None
    
    def is_initialized(self) -> bool:
        """Check if database is initialized"""
        return self._initialized and self.conn is not None
    
    def get_appointments_by_date_range(self, start_date: str, end_date: str, prov_num: Optional[int] = None) -> List[Dict]:
        """
        Get appointments within a date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            prov_num: Optional provider number to filter by
        
        Returns:
            List of appointment dictionaries
        """
        if not self.is_initialized():
            return []
        
        query = """
            SELECT a.*, 
                   p.LName || ', ' || p.FName as PatientName,
                   pr.Abbr as ProviderAbbr
            FROM appointment a
            LEFT JOIN patient p ON a.PatNum = p.PatNum
            LEFT JOIN provider pr ON a.ProvNum = pr.ProvNum
            WHERE DATE(a.AptDateTime) BETWEEN ? AND ?
        """
        
        params = [start_date, end_date]
        if prov_num is not None:
            query += " AND a.ProvNum = ?"
            params.append(prov_num)
        
        query += " ORDER BY a.AptDateTime ASC"
        
        return self._execute_query(query, params)
    
    def get_appointments_today(self, prov_num: Optional[int] = None) -> List[Dict]:
        """Get appointments for today"""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.get_appointments_by_date_range(today, today, prov_num)
    
    def get_appointments_this_week(self, prov_num: Optional[int] = None) -> List[Dict]:
        """Get appointments for this week"""
        today = datetime.now()
        start_of_week = today.strftime('%Y-%m-%d')
        end_of_week = (today.replace(day=today.day + 7)).strftime('%Y-%m-%d')
        return self.get_appointments_by_date_range(start_of_week, end_of_week, prov_num)
    
    def get_patient_by_name(self, first_name: str = "", last_name: str = "") -> List[Dict]:
        """
        Search for patients by name
        
        Args:
            first_name: First name (partial match)
            last_name: Last name (partial match)
        
        Returns:
            List of patient dictionaries
        """
        if not self.is_initialized():
            return []
        
        query = "SELECT * FROM patient WHERE 1=1"
        params = []
        
        if first_name:
            query += " AND FName LIKE ?"
            params.append(f"%{first_name}%")
        
        if last_name:
            query += " AND LName LIKE ?"
            params.append(f"%{last_name}%")
        
        query += " LIMIT 20"
        
        return self._execute_query(query, params)
    
    def get_provider_info(self, prov_num: Optional[int] = None) -> List[Dict]:
        """
        Get provider information
        
        Args:
            prov_num: Optional provider number
        
        Returns:
            List of provider dictionaries
        """
        if not self.is_initialized():
            return []
        
        if prov_num:
            query = "SELECT * FROM provider WHERE ProvNum = ?"
            params = [prov_num]
        else:
            query = "SELECT * FROM provider WHERE IsHidden = 0"
            params = []
        
        return self._execute_query(query, params)
    
    def get_icd9_by_code(self, icd9_code: str) -> List[Dict]:
        """
        Get ICD9 records by code
        
        Args:
            icd9_code: ICD9 code (e.g., "001", "001.0")
        
        Returns:
            List of ICD9 dictionaries
        """
        if not self.is_initialized():
            return []
        
        query = "SELECT * FROM icd9 WHERE ICD9Code = ? LIMIT 10"
        params = [icd9_code]
        
        return self._execute_query(query, params)
    
    def get_icd9_by_description(self, description: str, limit: int = 20) -> List[Dict]:
        """
        Search ICD9 records by description
        
        Args:
            description: Description search term (partial match)
            limit: Maximum number of results
        
        Returns:
            List of ICD9 dictionaries
        """
        if not self.is_initialized():
            return []
        
        query = "SELECT * FROM icd9 WHERE Description LIKE ? ORDER BY ICD9Code LIMIT ?"
        params = [f"%{description}%", limit]
        
        return self._execute_query(query, params)
    
    def get_icd9_by_date(self, date: str) -> List[Dict]:
        """
        Get ICD9 records by date
        
        Args:
            date: Date in YYYY-MM-DD format
        
        Returns:
            List of ICD9 dictionaries
        """
        if not self.is_initialized():
            return []
        
        query = "SELECT * FROM icd9 WHERE DATE(DateTStamp) = ? ORDER BY ICD9Code LIMIT 100"
        params = [date]
        
        return self._execute_query(query, params)
    
    def get_icd9_by_num(self, icd9_num: int) -> List[Dict]:
        """
        Get ICD9 record by ICD9Num
        
        Args:
            icd9_num: ICD9 number (primary key)
        
        Returns:
            List of ICD9 dictionaries (usually one)
        """
        if not self.is_initialized():
            return []
        
        query = "SELECT * FROM icd9 WHERE ICD9Num = ?"
        params = [icd9_num]
        
        return self._execute_query(query, params)
    
    def search_icd9(self, code: Optional[str] = None, description: Optional[str] = None, 
                     date: Optional[str] = None, icd9_num: Optional[int] = None, 
                     limit: int = 20) -> List[Dict]:
        """
        Flexible ICD9 search with multiple criteria
        
        Args:
            code: ICD9 code
            description: Description search term
            date: Date in YYYY-MM-DD format
            icd9_num: ICD9 number
            limit: Maximum results
        
        Returns:
            List of ICD9 dictionaries
        """
        if not self.is_initialized():
            return []
        
        query = "SELECT * FROM icd9 WHERE 1=1"
        params = []
        
        if icd9_num:
            query += " AND ICD9Num = ?"
            params.append(icd9_num)
        elif code:
            query += " AND ICD9Code = ?"
            params.append(code)
        elif description:
            query += " AND Description LIKE ?"
            params.append(f"%{description}%")
        elif date:
            query += " AND DATE(DateTStamp) = ?"
            params.append(date)
        else:
            return []
        
        query += " ORDER BY ICD9Code LIMIT ?"
        params.append(limit)
        
        return self._execute_query(query, params)
    
    def _execute_query(self, query: str, params: List[Any] = None) -> List[Dict]:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL SELECT query
            params: Query parameters
        
        Returns:
            List of dictionaries representing rows
        """
        if not self.conn:
            return []
        
        # Security: Only allow SELECT queries
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
        
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            result = []
            for row in rows:
                result.append(dict(row))
            
            return result
        except sqlite3.Error as e:
            print(f"Query execution error: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self._initialized = False

