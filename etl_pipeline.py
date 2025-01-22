import os
from datetime import datetime
from typing import List, Dict
import pandas as pd
from prefect import flow, task
from prefect.tasks import task_input_hash
from prefect_snowflake.database import SnowflakeConnector
from snowflake.connector.pandas_tools import write_pandas
import hashlib
# Snowflake ETL pipline with prefect
# Configuration
SNOWFLAKE_CONNECTOR_BLOCK = "snowflake-demo"
RAW_DATABASE = "RAW_DB"
ANALYTICS_DATABASE = "ANALYTICS_DB"
RAW_SCHEMA = "RAW"
ANALYTICS_SCHEMA = "ANALYTICS"

# Sample DDL creation
DDL_STATEMENTS = {
    "products": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.PRODUCTS (
            product_id VARCHAR,
            product_name VARCHAR,
            category VARCHAR,
            price DECIMAL(10,2),
            created_at TIMESTAMP_NTZ,
            _etl_loaded_at TIMESTAMP_NTZ
        )
    """,
    "locations": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.LOCATIONS (
            location_id VARCHAR,
            location_name VARCHAR,
            address VARCHAR,
            city VARCHAR,
            state VARCHAR,
            country VARCHAR,
            created_at TIMESTAMP_NTZ,
            _etl_loaded_at TIMESTAMP_NTZ
        )
    """,
    "customers": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.CUSTOMERS (
            customer_id VARCHAR,
            first_name VARCHAR,
            last_name VARCHAR,
            email VARCHAR,
            created_at TIMESTAMP_NTZ,
            _etl_loaded_at TIMESTAMP_NTZ
        )
    """,
    "orders": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.ORDERS (
            order_id VARCHAR,
            customer_id VARCHAR,
            order_date TIMESTAMP_NTZ,
            location_id VARCHAR,
            created_at TIMESTAMP_NTZ,
            _etl_loaded_at TIMESTAMP_NTZ
        )
    """,
    "sales": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.SALES (
            sale_id VARCHAR,
            order_id VARCHAR,
            product_id VARCHAR,
            quantity INTEGER,
            sale_amount DECIMAL(10,2),
            created_at TIMESTAMP_NTZ,
            _etl_loaded_at TIMESTAMP_NTZ
        )
    """
}

# Dimensional model DDL statements
DIM_FACT_DDLS = {
    "dim_products": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.DIM_PRODUCTS (
            product_sk INTEGER IDENTITY(1,1),
            product_id VARCHAR,
            product_name VARCHAR,
            category VARCHAR,
            price DECIMAL(10,2),
            created_at TIMESTAMP_NTZ,
            _etl_loaded_at TIMESTAMP_NTZ,
            CONSTRAINT pk_dim_products PRIMARY KEY (product_sk)
        )
    """,
    "dim_locations": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.DIM_LOCATIONS (
            location_sk INTEGER IDENTITY(1,1),
            location_id VARCHAR,
            location_name VARCHAR,
            address VARCHAR,
            city VARCHAR,
            state VARCHAR,
            country VARCHAR,
            created_at TIMESTAMP_NTZ,
            _etl_loaded_at TIMESTAMP_NTZ,
            CONSTRAINT pk_dim_locations PRIMARY KEY (location_sk)
        )
    """,
    "dim_customers": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.DIM_CUSTOMERS (
            customer_sk INTEGER IDENTITY(1,1),
            customer_id VARCHAR,
            first_name VARCHAR,
            last_name VARCHAR,
            email VARCHAR,
            created_at TIMESTAMP_NTZ,
            _etl_loaded_at TIMESTAMP_NTZ,
            CONSTRAINT pk_dim_customers PRIMARY KEY (customer_sk)
        )
    """,
    "dim_dates": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.DIM_DATES (
            date_sk INTEGER IDENTITY(1,1),
            date_id DATE,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            quarter INTEGER,
            _etl_loaded_at TIMESTAMP_NTZ,
            CONSTRAINT pk_dim_dates PRIMARY KEY (date_sk)
        )
    """,
    "fact_sales": """
        CREATE TABLE IF NOT EXISTS {database}.{schema}.FACT_SALES (
            sale_sk INTEGER IDENTITY(1,1),
            sale_id VARCHAR,
            order_id VARCHAR,
            customer_sk INTEGER,
            product_sk INTEGER,
            location_sk INTEGER,
            date_sk INTEGER,
            quantity INTEGER,
            sale_amount DECIMAL(10,2),
            created_at TIMESTAMP_NTZ,
            _etl_loaded_at TIMESTAMP_NTZ,
            CONSTRAINT pk_fact_sales PRIMARY KEY (sale_sk),
            CONSTRAINT fk_customer FOREIGN KEY (customer_sk) REFERENCES {database}.{schema}.DIM_CUSTOMERS(customer_sk),
            CONSTRAINT fk_product FOREIGN KEY (product_sk) REFERENCES {database}.{schema}.DIM_PRODUCTS(product_sk),
            CONSTRAINT fk_location FOREIGN KEY (location_sk) REFERENCES {database}.{schema}.DIM_LOCATIONS(location_sk),
            CONSTRAINT fk_date FOREIGN KEY (date_sk) REFERENCES {database}.{schema}.DIM_DATES(date_sk)
        )
    """
}

@task(retries=3, cache_key_fn=task_input_hash)
def create_raw_tables(connector: SnowflakeConnector) -> None:
    """Create raw tables in Snowflake"""
    with connector.get_connection() as conn:
        for table, ddl in DDL_STATEMENTS.items():
            conn.execute(ddl.format(database=RAW_DATABASE, schema=RAW_SCHEMA))

@task(retries=3, cache_key_fn=task_input_hash)
def create_dimension_tables(connector: SnowflakeConnector) -> None:
    """Create dimension and fact tables in Snowflake"""
    with connector.get_connection() as conn:
        for table, ddl in DIM_FACT_DDLS.items():
            conn.execute(ddl.format(database=ANALYTICS_DATABASE, schema=ANALYTICS_SCHEMA))

@task(retries=3)
def load_raw_data(connector: SnowflakeConnector, file_path: str, table_name: str) -> None:
    """Load CSV data into raw tables"""
    df = pd.read_csv(file_path)
    df['created_at'] = datetime.now()
    df['_etl_loaded_at'] = datetime.now()
    
    with connector.get_connection() as conn:
        success, nchunks, nrows, _ = write_pandas(
            conn=conn,
            df=df,
            table_name=table_name,
            database=RAW_DATABASE,
            schema=RAW_SCHEMA
        )
        
        if not success:
            raise Exception(f"Failed to load {table_name}")

@task(retries=3)
def load_dimension_table(connector: SnowflakeConnector, table_name: str, transformation_query: str) -> None:
    """Load dimension tables from raw data"""
    with connector.get_connection() as conn:
        conn.execute(f"TRUNCATE TABLE {ANALYTICS_DATABASE}.{ANALYTICS_SCHEMA}.{table_name}")
        conn.execute(transformation_query.format(
            raw_db=RAW_DATABASE,
            raw_schema=RAW_SCHEMA,
            analytics_db=ANALYTICS_DATABASE,
            analytics_schema=ANALYTICS_SCHEMA
        ))

@task(retries=3)
def load_fact_sales(connector: SnowflakeConnector) -> None:
    """Load fact sales table"""
    query = """
    INSERT INTO {analytics_db}.{analytics_schema}.FACT_SALES (
        sale_id, order_id, customer_sk, product_sk, location_sk, date_sk,
        quantity, sale_amount, created_at, _etl_loaded_at
    )
    SELECT 
        s.sale_id,
        s.order_id,
        c.customer_sk,
        p.product_sk,
        l.location_sk,
        d.date_sk,
        s.quantity,
        s.sale_amount,
        s.created_at,
        CURRENT_TIMESTAMP()
    FROM {raw_db}.{raw_schema}.SALES s
    JOIN {raw_db}.{raw_schema}.ORDERS o ON s.order_id = o.order_id
    JOIN {analytics_db}.{analytics_schema}.DIM_CUSTOMERS c ON o.customer_id = c.customer_id
    JOIN {analytics_db}.{analytics_schema}.DIM_PRODUCTS p ON s.product_id = p.product_id
    JOIN {analytics_db}.{analytics_schema}.DIM_LOCATIONS l ON o.location_id = l.location_id
    JOIN {analytics_db}.{analytics_schema}.DIM_DATES d ON DATE(o.order_date) = d.date_id
    """
    
    with connector.get_connection() as conn:
        conn.execute(f"TRUNCATE TABLE {ANALYTICS_DATABASE}.{ANALYTICS_SCHEMA}.FACT_SALES")
        conn.execute(query.format(
            raw_db=RAW_DATABASE,
            raw_schema=RAW_SCHEMA,
            analytics_db=ANALYTICS_DATABASE,
            analytics_schema=ANALYTICS_SCHEMA
        ))

@flow(name="Load Raw Data")
def load_raw_data_flow(connector: SnowflakeConnector, file_paths: Dict[str, str]):
    """Flow to load raw data in parallel"""
    create_raw_tables(connector)
    
    # Load all raw tables in parallel
    for table_name, file_path in file_paths.items():
        load_raw_data.submit(connector, file_path, table_name)

@flow(name="Load Dimensional Model")
def load_dimensional_model_flow(connector: SnowflakeConnector):
    """Flow to load dimensional model"""
    create_dimension_tables(connector)
    
    # Load dimensions
    dim_transforms = {
        "DIM_PRODUCTS": """
            INSERT INTO {analytics_db}.{analytics_schema}.DIM_PRODUCTS
            SELECT 
                product_id,
                product_name,
                category,
                price,
                created_at,
                CURRENT_TIMESTAMP()
            FROM {raw_db}.{raw_schema}.PRODUCTS
        """,
        "DIM_LOCATIONS": """
            INSERT INTO {analytics_db}.{analytics_schema}.DIM_LOCATIONS
            SELECT 
                location_id,
                location_name,
                address,
                city,
                state,
                country,
                created_at,
                CURRENT_TIMESTAMP()
            FROM {raw_db}.{raw_schema}.LOCATIONS
        """,
        "DIM_CUSTOMERS": """
            INSERT INTO {analytics_db}.{analytics_schema}.DIM_CUSTOMERS
            SELECT 
                customer_id,
                first_name,
                last_name,
                email,
                created_at,
                CURRENT_TIMESTAMP()
            FROM {raw_db}.{raw_schema}.CUSTOMERS
        """
    }
    
    # Load dimensions in parallel
    for dim_name, transform_query in dim_transforms.items():
        load_dimension_table.submit(connector, dim_name, transform_query)
    
    # Load fact table after dimensions
    load_fact_sales(connector)

@flow(name="Retail ETL Pipeline")
def main_flow():
    """Main ETL flow"""
    connector = SnowflakeConnector.load(SNOWFLAKE_CONNECTOR_BLOCK)
    
    # Define file paths
    file_paths = {
        "PRODUCTS": "data/products.csv",
        "LOCATIONS": "data/locations.csv",
        "CUSTOMERS": "data/customers.csv",
        "ORDERS": "data/orders.csv",
        "SALES": "data/sales.csv"
    }
    
    # Execute raw data load
    load_raw_data_flow(connector, file_paths)
    
    # Execute dimensional model load
    load_dimensional_model_flow(connector)

if __name__ == "__main__":
    main_flow()