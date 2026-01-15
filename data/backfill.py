import ibis
import pandas as pd
import numpy as np

con = ibis.postgres.connect(
    user="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="my_db",
)


print(con)  


def pandas_to_ibis_schema(df):
    """
    Convert pandas DataFrame dtypes to Ibis schema.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame to convert
        
    Returns:
    --------
    ibis.Schema
        Ibis schema object
    """
    type_mapping = {
        'int8': 'int8',
        'int16': 'int16',
        'int32': 'int32',
        'int64': 'int64',
        'uint8': 'uint8',
        'uint16': 'uint16',
        'uint32': 'uint32',
        'uint64': 'uint64',
        'float32': 'float32',
        'float64': 'float64',
        'float': 'float64',
        'bool': 'bool',
        'object': 'string',
        'string': 'string',
        'datetime64[ns]': 'timestamp',
        'timedelta64[ns]': 'interval',
    }
    
    schema_dict = {}
    
    for col, dtype in df.dtypes.items():
        dtype_str = str(dtype)
        
        # Handle datetime with timezone
        if 'datetime64' in dtype_str:
            if 'UTC' in dtype_str or 'tz' in dtype_str:
                schema_dict[col] = 'timestamp'
            else:
                schema_dict[col] = 'timestamp'
        # Handle categorical
        elif dtype.name == 'category':
            schema_dict[col] = 'string'
        # Handle other types
        else:
            schema_dict[col] = type_mapping.get(dtype.name, 'string')
    
    return ibis.schema(schema_dict)


# Usage example:
df = pd.read_csv("../data/air_traffic.csv")

df["Activity Period Start Date"] = pd.to_datetime(df["Activity Period Start Date"], format="%Y/%m/%d")


# Convert to Ibis schema
schema = pandas_to_ibis_schema(df)

print(schema)

con.create_table('air_traffic', df, schema=schema, overwrite=True)

print(f"Successfully loaded {len(df)} rows into air_traffic table")


con.sql("SELECT * FROM air_traffic LIMIT 10").execute()


