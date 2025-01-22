import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import uuid
# sample data generator
def generate_products(n=100):
    categories = ['Electronics', 'Clothing', 'Books', 'Home & Garden', 'Sports']
    
    df = pd.DataFrame({
        'product_id': [str(uuid.uuid4()) for _ in range(n)],
        'product_name': [f'Product_{i}' for i in range(n)],
        'category': np.random.choice(categories, n),
        'price': np.random.uniform(10, 1000, n).round(2)
    })
    return df

def generate_locations(n=50):
    states = ['CA', 'NY', 'TX', 'FL', 'IL']
    
    df = pd.DataFrame({
        'location_id': [str(uuid.uuid4()) for _ in range(n)],
        'location_name': [f'Store_{i}' for i in range(n)],
        'address': [f'{i} Main St' for i in range(n)],
        'city': [f'City_{i}' for i in range(n)],
        'state': np.random.choice(states, n),
        'country': 'USA'
    })
    return df

def generate_customers