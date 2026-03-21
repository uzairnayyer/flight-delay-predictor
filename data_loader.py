import pandas as pd
import numpy as np
import os
import sys


# Columns we actually need from the massive CSV
# (This saves memory by not loading all 31 columns)
COLUMNS_TO_LOAD = [
    'MONTH',
    'DAY_OF_WEEK',
    'AIRLINE',
    'ORIGIN_AIRPORT',
    'DESTINATION_AIRPORT',
    'SCHEDULED_DEPARTURE',
    'DEPARTURE_DELAY',
    'TAXI_OUT',
    'SCHEDULED_TIME',
    'DISTANCE',
    'ARRIVAL_DELAY',
]

# Top 15 busiest US airports (we filter to these for cleaner analysis)
TOP_AIRPORTS = [
    'ATL', 'ORD', 'DFW', 'DEN', 'JFK',
    'SFO', 'SEA', 'LAS', 'MCO', 'LAX',
    'BOS', 'MIA', 'PHX', 'MSP', 'DTW',
    'EWR', 'SLC', 'IAH', 'SAN', 'CLT',
]

# Airline code to full name mapping (from airlines.csv in the Kaggle dataset)
AIRLINE_NAMES = {
    'UA': 'United Airlines',
    'AA': 'American Airlines',
    'US': 'US Airways',
    'F9': 'Frontier Airlines',
    'B6': 'JetBlue Airways',
    'OO': 'SkyWest Airlines',
    'AS': 'Alaska Airlines',
    'NK': 'Spirit Airlines',
    'WN': 'Southwest Airlines',
    'DL': 'Delta Air Lines',
    'EV': 'ExpressJet Airlines',
    'HA': 'Hawaiian Airlines',
    'MQ': 'American Eagle',
    'VX': 'Virgin America',
}

# Airport code to city name mapping
AIRPORT_CITIES = {
    'ATL': 'Atlanta',
    'ORD': 'Chicago',
    'DFW': 'Dallas/Fort Worth',
    'DEN': 'Denver',
    'JFK': 'New York (JFK)',
    'SFO': 'San Francisco',
    'SEA': 'Seattle',
    'LAS': 'Las Vegas',
    'MCO': 'Orlando',
    'LAX': 'Los Angeles',
    'BOS': 'Boston',
    'MIA': 'Miami',
    'PHX': 'Phoenix',
    'MSP': 'Minneapolis',
    'DTW': 'Detroit',
    'EWR': 'Newark',
    'SLC': 'Salt Lake City',
    'IAH': 'Houston',
    'SAN': 'San Diego',
    'CLT': 'Charlotte',
}


def load_real_dataset(filepath='data/flights.csv', sample_size=100000, seed=42):
    """
    Load the real 2015 Flight Delays dataset from Kaggle.
    
    This function:
    1. Reads only the columns we need (saves memory)
    2. Filters to major airports only
    3. Samples down to a manageable size
    4. Creates clean column names matching our app
    
    Parameters:
        filepath (str): Path to the flights.csv file
        sample_size (int): Number of rows to sample (100k is good balance)
        seed (int): Random seed for reproducible sampling
    
    Returns:
        pd.DataFrame: Cleaned and sampled flight data
    """
    
    if not os.path.exists(filepath):
        print("ERROR: Dataset file not found!")

    
    print(f"Loading real flight dataset from {filepath}...")
    
    # step 1: Load only needed columns
    # the full CSV is 600MB with 5.8M rows
    # loading only needed columns saves significant memory
    try:
        df_raw = pd.read_csv(
            filepath,
            usecols=COLUMNS_TO_LOAD,
            low_memory=False
        )
        print(f"  Raw dataset loaded: {len(df_raw):,} rows")
    except ValueError as e:
        print(f"\nColumn error: {e}")
        print("The CSV might have different column names.")
        print("Loading all columns to inspect...")
        df_check = pd.read_csv(filepath, nrows=5)
        print(f"Available columns: {df_check.columns.tolist()}")
        sys.exit(1)
    
    # step 2: Filter to flights from/to major airports 
    # some airport codes in the data are numeric (small airports)
    # we keep only well-known 3-letter airport codes
    df_filtered = df_raw[
        (df_raw['ORIGIN_AIRPORT'].isin(TOP_AIRPORTS)) &
        (df_raw['DESTINATION_AIRPORT'].isin(TOP_AIRPORTS))
    ].copy()
    print(f"  After filtering to major airports: {len(df_filtered):,} rows")
    
    # step 3: Drop rows with missing critical values
    critical_cols = ['DEPARTURE_DELAY', 'AIRLINE', 'ORIGIN_AIRPORT', 'DISTANCE']
    before = len(df_filtered)
    df_filtered = df_filtered.dropna(subset=critical_cols)
    dropped = before - len(df_filtered)
    if dropped > 0:
        print(f"  Dropped {dropped:,} rows with missing critical values")
    
    # step 4: Sample down to manageable size
    if len(df_filtered) > sample_size:
        df_sampled = df_filtered.sample(n=sample_size, random_state=seed)
        print(f"  Sampled down to: {len(df_sampled):,} rows")
    else:
        df_sampled = df_filtered
        print(f"  Using all {len(df_sampled):,} filtered rows")
    
    # step 5: Rename columns to match our app's expected format 
    df = df_sampled.rename(columns={
        'ORIGIN_AIRPORT': 'ORIGIN',
        'DESTINATION_AIRPORT': 'DEST',
        'SCHEDULED_DEPARTURE': 'CRS_DEP_TIME',
        'DEPARTURE_DELAY': 'DEP_DELAY',
        'SCHEDULED_TIME': 'CRS_ELAPSED_TIME',
        'ARRIVAL_DELAY': 'ARR_DELAY',
    }).copy()
    
    # step 6: Create derived columns
    
    # extract departure hour from scheduled departure (format: HHMM as integer)
    # e.g., 1430 -> hour 14, 905 -> hour 9, 30 -> hour 0
    df['CRS_DEP_TIME'] = pd.to_numeric(df['CRS_DEP_TIME'], errors='coerce').fillna(1200)
    df['DEP_HOUR'] = (df['CRS_DEP_TIME'] // 100).astype(int).clip(0, 23)
    
    # create DELAYED flag: flight is "delayed" if departure delay > 15 minutes
    # this is the standard definition used by the DOT
    df['DEP_DELAY'] = pd.to_numeric(df['DEP_DELAY'], errors='coerce').fillna(0)
    df['DELAYED'] = (df['DEP_DELAY'] > 15).astype(int)
    
    # sdd airline full names
    df['AIRLINE_NAME'] = df['AIRLINE'].map(AIRLINE_NAMES).fillna(df['AIRLINE'])
    
    #sdd origin city names
    df['ORIGIN_CITY'] = df['ORIGIN'].map(AIRPORT_CITIES).fillna(df['ORIGIN'])
    
    # sdd destination city names
    df['DEST_CITY'] = df['DEST'].map(AIRPORT_CITIES).fillna(df['DEST'])
    
    # Ensure numeric columns are proper types
    df['DISTANCE'] = pd.to_numeric(df['DISTANCE'], errors='coerce').fillna(1000).astype(int)
    df['TAXI_OUT'] = pd.to_numeric(df['TAXI_OUT'], errors='coerce').fillna(16)
    df['CRS_ELAPSED_TIME'] = pd.to_numeric(df['CRS_ELAPSED_TIME'], errors='coerce').fillna(150)
    df['MONTH'] = pd.to_numeric(df['MONTH'], errors='coerce').fillna(6).astype(int).clip(1, 12)
    df['DAY_OF_WEEK'] = pd.to_numeric(df['DAY_OF_WEEK'], errors='coerce').fillna(4).astype(int).clip(1, 7)
    
    df = df.reset_index(drop=True)
    
    # Print summary
    delay_rate = df['DELAYED'].mean() * 100
    print(f"\nDataset Summary")
    print(f"  Total flights: {len(df):,}")
    print(f"  Airlines: {df['AIRLINE'].nunique()}")
    print(f"  Airports: {df['ORIGIN'].nunique()}")
    print(f"  Months covered: {sorted(df['MONTH'].unique())}")
    print(f"  Delay rate: {delay_rate:.1f}%")
    print(f"  Avg departure delay: {df['DEP_DELAY'].mean():.1f} minutes")
    print(f"  Distance range: {df['DISTANCE'].min()} - {df['DISTANCE'].max()} miles")
    print(f"  Missing values remaining: {df.isnull().sum().sum()}")
    
    return df


def get_processed_data(filepath='data/flights.csv', 
                       cache_path='data/flights_processed.csv',
                       sample_size=100000):

    
    if os.path.exists(cache_path):
        print(f"Loading cached processed data from {cache_path}...")
        df = pd.read_csv(cache_path)
        
        expected_cols = ['MONTH', 'DAY_OF_WEEK', 'AIRLINE', 'ORIGIN', 'DEP_HOUR', 
                        'DELAYED', 'DISTANCE', 'AIRLINE_NAME']
        if all(col in df.columns for col in expected_cols):
            print(f"  Loaded {len(df):,} rows from cache")
            return df
        else:
            print("  Cache file has wrong format, reprocessing...")
            os.remove(cache_path)
    
    df = load_real_dataset(filepath=filepath, sample_size=sample_size)
    
    os.makedirs(os.path.dirname(cache_path) if os.path.dirname(cache_path) else '.', exist_ok=True)
    df.to_csv(cache_path, index=False)
    print(f"(Next startup will be much faster)")
    
    return df

if __name__ == '__main__':
    df = get_processed_data()
