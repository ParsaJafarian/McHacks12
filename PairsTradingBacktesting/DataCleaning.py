import pandas as pd
import os

def determine_global_time_range(csv_files, date_str, freq='5S'):
    """
    Determines the global start and end datetime across all CSV files.
    """
    min_datetime = None
    max_datetime = None

    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path)
            if df.empty or 'timestamp' not in df.columns:
                continue

            # Process timestamps
            df['timestamp'] = pd.to_datetime(date_str + ' ' + df['timestamp'].astype(str).str[:15])

            if df.empty:
                continue

            file_min = df['timestamp'].min()
            file_max = df['timestamp'].max()

            if min_datetime is None or file_min < min_datetime:
                min_datetime = file_min
            if max_datetime is None or file_max > max_datetime:
                max_datetime = file_max

        except Exception as e:
            print(f"Error processing {file_path} for global time range: {e}")

    if min_datetime is None or max_datetime is None:
        raise ValueError("No valid datetime entries found across all files.")

    # Floor to the previous 5-second mark and ceil to the next 5-second mark
    min_datetime = min_datetime.floor('5S')
    max_datetime = max_datetime.ceil('5S')

    return min_datetime, max_datetime

def read_and_process_stock(file_path, date_str, global_start_datetime, global_end_datetime, freq='5S', output_directory='./processed_data'):
    """
    Processes a stock's CSV file with 5-second intervals and proper filling.
    """
    stock_name = os.path.splitext(os.path.basename(file_path))[0].split('__')[-1]
    print(f"\nProcessing stock: {stock_name}")

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            print(f"Warning: {file_path} is empty. Skipping.")
            return
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    required_columns = {'price', 'timestamp'}
    if not required_columns.issubset(df.columns):
        print(f"Error: Missing required columns in {file_path}. Skipping.")
        return

    try:
        # Convert timestamps to datetime
        df['datetime'] = pd.to_datetime(date_str + ' ' + df['timestamp'].astype(str).str[:15])

        # Sort by datetime
        df = df.sort_values('datetime')

        # Set datetime as index
        df.set_index('datetime', inplace=True)

        # Create complete time range from global start to end
        full_range = pd.date_range(start=global_start_datetime,
                                   end=global_end_datetime,
                                   freq=freq)

        # Resample to 5-second intervals
        resampled_df = df.resample(freq).agg({
            'price': 'last'
        })

        # Reindex to include all intervals
        resampled_df = resampled_df.reindex(full_range)

        # Forward fill, then backward fill to handle gaps
        resampled_df = resampled_df.ffill().bfill()

        # Reset index and rename columns
        resampled_df = resampled_df.reset_index().rename(columns={
            'index': 'timestamp',
            'price': 'close'
        })

        # Ensure output directory exists
        os.makedirs(output_directory, exist_ok=True)

        # Save processed data
        output_file = os.path.join(output_directory, f'resampled_5S_data__{stock_name}.csv')
        resampled_df.to_csv(output_file, index=False)
        print(f"Processed data saved to {output_file}")

        # Print statistics
        print(f"Original records: {len(df)}")
        print(f"Resampled records: {len(resampled_df)}")
        print(f"Time range: {resampled_df['timestamp'].min()} to {resampled_df['timestamp'].max()}")

    except Exception as e:
        print(f"Error processing {stock_name}: {e}")

def process_period(period_path, date_str, output_base_dir='processed_data'):
    """
    Process all files for a specific period.
    """
    # Extract period name from path
    period_name = os.path.basename(os.path.normpath(period_path))
    print(f"\nProcessing {period_name}")

    # Create output directory for this period
    output_directory = os.path.join(output_base_dir, period_name)
    os.makedirs(output_directory, exist_ok=True)

    # Process each stock (A, B, C, D, E)
    stocks = ['A', 'B', 'C', 'D', 'E']
    csv_files = []

    for stock in stocks:
        stock_path = os.path.join(period_path, stock, f'trade_data__{stock}.csv')
        if os.path.exists(stock_path):
            csv_files.append(stock_path)
        else:
            print(f"Warning: File not found for stock {stock} in {period_path}")

    if not csv_files:
        print(f"No CSV files found in {period_path}")
        return

    try:
        global_start_datetime, global_end_datetime = determine_global_time_range(csv_files, date_str)
        print(f"Global time range for {period_name}: {global_start_datetime} to {global_end_datetime}")

        for file in csv_files:
            read_and_process_stock(
                file_path=file,
                date_str=date_str,
                global_start_datetime=global_start_datetime,
                global_end_datetime=global_end_datetime,
                freq='5S',
                output_directory=output_directory
            )

    except Exception as e:
        print(f"Error processing {period_name}: {e}")

def main():
    """
    Main function to process all periods.
    """
    base_dir = 'trainingdata'
    date_str = '2025-01-25'  # Adjust as needed

    # Find all period directories
    period_dirs = []
    for item in os.listdir(base_dir):
        if item.startswith('Period'):
            period_path = os.path.join(base_dir, item, item)  # Matches your folder structure
            if os.path.isdir(period_path):
                period_dirs.append(period_path)

    if not period_dirs:
        print("No period directories found")
        return

    # Process each period
    for period_dir in sorted(period_dirs):
        process_period(period_dir, date_str)

    print("\nAll periods processed successfully.")

if __name__ == "__main__":
    main()

# Created/Modified files during execution:
# For each period<N>, creates:
# - processed_data/period<N>/resampled_5S_data__A.csv
# - processed_data/period<N>/resampled_5S_data__B.csv
# - processed_data/period<N>/resampled_5S_data__C.csv
# - processed_data/period<N>/resampled_5S_data__D.csv
# - processed_data/period<N>/resampled_5S_data__E.csv