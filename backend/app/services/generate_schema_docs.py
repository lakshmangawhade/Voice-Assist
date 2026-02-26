#!/usr/bin/env python3
"""
Script to extract all table definitions from SQL and generate field descriptions
Run this to generate the FIELD_DESCRIPTIONS dictionary for schema_parser.py
"""

import re
from pathlib import Path
from collections import defaultdict

def extract_all_tables(sql_file_path):
    """Extract all table definitions from SQL file"""
    with open(sql_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Pattern to match CREATE TABLE statements
    pattern = r'CREATE TABLE\s+`?(\w+)`?\s*\((.*?)\)\s*ENGINE'
    tables = {}
    
    matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        table_name = match.group(1).lower()
        table_def = match.group(2)
        
        columns = []
        
        # Parse column definitions
        for line in table_def.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Skip constraint definitions
            if any(line.upper().startswith(k) for k in ['PRIMARY KEY', 'KEY', 'UNIQUE', 'FOREIGN KEY', 'INDEX', 'CONSTRAINT']):
                continue
            
            # Extract column name and type
            col_match = re.match(r'`?(\w+)`?\s+([^,]+?)(?:,|$)', line)
            if col_match:
                col_name = col_match.group(1)
                col_def = col_match.group(2).strip()
                
                # Extract just the type
                type_match = re.match(r'(\w+(?:\([^)]+\))?)', col_def)
                col_type = type_match.group(1) if type_match else col_def.split()[0]
                
                # Check for NOT NULL, DEFAULT, etc.
                is_required = 'NOT NULL' in col_def.upper()
                
                columns.append({
                    'name': col_name,
                    'type': col_type,
                    'required': is_required,
                    'full_def': col_def
                })
        
        if columns:
            tables[table_name] = columns
    
    return tables

def generate_field_description(field_name, field_type, table_name):
    """Generate intelligent description based on field name and patterns"""
    
    # Common patterns and their descriptions
    patterns = {
        'Num$': 'Unique identifier',
        'Num': 'Foreign key reference',
        'DateTime': 'Date and time value',
        'Date': 'Date value',
        'Time': 'Time value',
        'Status': 'Status indicator',
        'Flag': 'Boolean flag',
        'Name$': 'Name or description',
        'Desc$': 'Description or text',
        'Description': 'Descriptive text field',
        'LName': 'Last name',
        'FName': 'First name',
        'MI': 'Middle initial',
        'Address': 'Street address or location',
        'City': 'City name',
        'State': 'State or province',
        'Zip': 'Postal code',
        'Phone': 'Phone number',
        'Email': 'Email address',
        'Code': 'Code or identifier',
        'Type': 'Type or category',
        'Color': 'Color value',
        'Amount': 'Monetary amount',
        'Count': 'Numeric count',
        'Rate': 'Rate or percentage',
        'IsHidden': 'Whether record is hidden from view',
        'IsActive': 'Whether record is active',
        'IsEnabled': 'Whether feature is enabled',
        'TStamp': 'Timestamp of last modification',
        'Entry': 'Data entry field',
        'User': 'User or person reference',
        'Order': 'Display or processing order',
        'Text': 'Text or comment field',
        'Note': 'Informational note or comment',
        'SSN': 'Social Security Number',
        'ID': 'Identifier',
    }
    
    for pattern, desc_base in patterns.items():
        if pattern.lower() in field_name.lower():
            # Create more specific description
            context = table_name.replace('_', ' ').title()
            
            # Very specific patterns
            if field_name == 'AptNum':
                return 'Unique appointment identifier (auto-increment primary key)'
            elif field_name == 'PatNum':
                return 'Patient number - foreign key reference to patient table'
            elif field_name == 'ProvNum':
                return 'Provider/dentist number - foreign key reference to provider table'
            elif field_name == 'ClinicNum':
                return 'Clinic/location number - foreign key reference to clinic table'
            elif field_name == 'AptStatus':
                return 'Appointment status code (0=scheduled, 1=completed, 2=cancelled, etc.)'
            elif field_name == 'PatStatus':
                return 'Patient status code (0=active, 1=inactive, 2=archived, etc.)'
            elif field_name == 'IsHidden':
                return 'Whether record is hidden from view (0=visible, 1=hidden)'
            elif field_name == 'TxtMsgOk':
                return 'Whether patient has opted into text message communications (0=no, 1=yes)'
            elif field_name == 'WirelessPhone':
                return 'Mobile/wireless phone number for SMS and text communication'
            elif field_name == 'SmsStatus':
                return 'SMS delivery status'
            elif field_name.startswith('DateT'):
                return f'{field_name} timestamp value'
            elif field_name.endswith('Phone'):
                return 'Phone number for communication'
            elif 'Num' in field_name and field_name != field_name.replace('Num', ''):
                return f'{field_name.replace("Num", "")} reference number'
            
            return f'{pattern} field related to {context}'
    
    # Default intelligent description
    if field_type.startswith('bigint'):
        return f'{field_name} - numeric reference or identifier'
    elif field_type.startswith('varchar'):
        return f'{field_name} - text value'
    elif field_type.startswith('text'):
        return f'{field_name} - extended text field'
    elif field_type.startswith('int'):
        return f'{field_name} - numeric value'
    elif field_type in ('date', 'datetime', 'timestamp'):
        return f'{field_name} - date/time value'
    elif field_type in ('tinyint', 'smallint'):
        return f'{field_name} - small numeric value or flag'
    elif field_type == 'double':
        return f'{field_name} - decimal/floating-point value'
    else:
        return f'{field_name} - database field'

def main():
    sql_path = Path(__file__).parent / 'data' / 'data.sql'
    
    if not sql_path.exists():
        print(f"SQL file not found: {sql_path}")
        return
    
    print("Extracting all tables from SQL file...")
    tables = extract_all_tables(str(sql_path))
    
    print(f"Found {len(tables)} tables\n")
    
    # Generate Python code
    output = [
        "# AUTO-GENERATED FIELD DESCRIPTIONS - Do not edit manually",
        "# Generated from SQL schema using generate_schema_docs.py",
        "FIELD_DESCRIPTIONS = {\n"
    ]
    
    for table_name in sorted(tables.keys()):
        columns = tables[table_name]
        output.append(f"    '{table_name}': {{")
        
        for col in columns:
            col_name = col['name']
            col_type = col['type']
            
            description = generate_field_description(col_name, col_type, table_name)
            output.append(f"        '{col_name}': '{description}',")
        
        output.append("    },\n")
    
    output.append("}")
    
    # Save to file
    output_file = Path(__file__).parent / 'schema_descriptions.py'
    with open(output_file, 'w') as f:
        f.write('\n'.join(output))
    
    print(f"Generated {output_file}")
    print(f"Total tables: {len(tables)}")
    total_fields = sum(len(cols) for cols in tables.values())
    print(f"Total fields: {total_fields}")
    
    # Print summary
    print("\nTable Summary:")
    for table_name in sorted(tables.keys()):
        print(f"  {table_name}: {len(tables[table_name])} fields")

if __name__ == '__main__':
    main()
