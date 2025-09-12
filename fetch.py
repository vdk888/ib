import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
from config import TRADING_SYMBOLS, DEFAULT_INTERVAL, default_interval_yahoo, default_backtest_interval, INDICATOR_LONG_TERM_FREQ_MULTIPLIER # Added multiplier import
import logging
import pytz
import json
import numpy as np # Add numpy import
logger = logging.getLogger(__name__)

def fetch_historical_data(symbol: str, interval: str = default_interval_yahoo, days: int = default_backtest_interval, use_cache: bool = True) -> pd.DataFrame:
    """
    Fetch historical data from Yahoo Finance, handling intraday limits via chunking.
    The data will always start from January 1st of the year that is years_back years ago,
    where years_back is determined by the days parameter.

    Args:
        symbol: Stock symbol
        interval: Data interval ('1m', '5m', '15m', '30m', '60m', '1h', '1d')
        days: Number of days of historical data to fetch (default: 3). This is used to determine
              how many years back to go (days / 365, rounded up).
        use_cache: Whether to use cached data if available (default: True).

    Returns:
        DataFrame with OHLCV data, or empty DataFrame on failure.
    """
    # Check if TRADING_SYMBOLS is empty or symbol doesn't exist
    if not TRADING_SYMBOLS:
        logger.error("TRADING_SYMBOLS is empty. Cannot fetch data. Stock list may need to be refreshed.")
        return pd.DataFrame()
    
    if symbol not in TRADING_SYMBOLS:
        logger.error(f"Symbol {symbol} not found in TRADING_SYMBOLS. Available symbols: {list(TRADING_SYMBOLS.keys())[:5]}...")
        return pd.DataFrame()
    # Calculate how many years back to go based on the days parameter
    years_back = max(1, (days + 364) // 365)  # Round up to nearest year
    current_year = datetime.now().year
    start_year = current_year - years_back
    jan_1st = datetime(start_year, 1, 1, tzinfo=pytz.UTC)
    
    # Calculate the actual number of days from Jan 1st to now
    days_since_jan1 = (datetime.now(pytz.UTC) - jan_1st).days + 1  # +1 to be inclusive
    
    # Use the calculated days for the actual data fetch
    effective_days = min(days, days_since_jan1)  # In case Jan 1st is less than requested days
    # Get the correct Yahoo Finance symbol
    yf_symbol = TRADING_SYMBOLS[symbol]['yfinance']
    ticker = yf.Ticker(yf_symbol)

    # Calculate start and end dates deterministically
    current_utc_datetime = datetime.now(pytz.UTC)
    # Set end_dt to the beginning of the current UTC day (e.g., if today is 2025-05-13 10:00 UTC, end_dt becomes 2025-05-13 00:00:00 UTC).
    # For yfinance, if interval is daily, an 'end' date of '2025-05-13' (meaning 2025-05-13 00:00:00 UTC)
    # will fetch data up to, but not including, 2025-05-13. So it includes all of 2025-05-12.
    # This makes the "latest full day" of data consistent if run any time on the same UTC day.
    end_dt = current_utc_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Use the January 1st date we calculated earlier as the start date
    start_dt = jan_1st
    
    # Log the actual date range being used
    logger.info(f"Fetching data from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} "
               f"(effective days: {effective_days}, original days: {days}, years_back: {years_back})")

    # Debug logging
    logger.debug(f"Attempting to fetch {interval} data for {symbol} ({yf_symbol})")
    logger.debug(f"Effective Date range for yfinance: Start={start_dt}, End={end_dt}")
    logger.debug(f"Requested days: {days}")

    # --- Fetching Logic with Chunking for Intraday Data ---
    df = pd.DataFrame()
    max_chunk_days = 60 # Fetch intraday data in chunks of max 60 days
    # yfinance uses '1h' not '60m'
    valid_intraday_intervals = ['1m', '2m', '5m', '15m', '30m', '1h']
    is_intraday = interval in valid_intraday_intervals

    if is_intraday and days > max_chunk_days:
        logger.info(f"Fetching {days} days of intraday data for {yf_symbol} in {max_chunk_days}-day chunks...")
        all_chunks = []
        current_start_chunk = start_dt # Use deterministic start_dt
        while current_start_chunk < end_dt: # Use deterministic end_dt
            chunk_end_dt = min(current_start_chunk + timedelta(days=max_chunk_days), end_dt) # Use deterministic end_dt
            # Ensure start is before end for the API call
            if current_start_chunk >= chunk_end_dt:
                logger.debug(f"Skipping chunk fetch because start ({current_start_chunk}) >= end ({chunk_end_dt})")
                break # Exit loop if start date has passed end date

            logger.info(f"Fetching chunk for {yf_symbol}: Start={current_start_chunk.strftime('%Y-%m-%d')}, End={chunk_end_dt.strftime('%Y-%m-%d')}, Interval={interval}")
            try:
                # Pass datetime objects directly to yfinance for potentially better precision with intraday
                chunk_df = ticker.history(start=current_start_chunk, end=chunk_end_dt, interval=interval)
                if not chunk_df.empty:
                    all_chunks.append(chunk_df)
                    logger.info(f"Fetched chunk with {len(chunk_df)} rows for {yf_symbol}. Date range: {chunk_df.index.min()} to {chunk_df.index.max()}")
            except Exception as chunk_e:
                logger.error(f"Error fetching chunk for {yf_symbol} ({current_start_chunk} to {chunk_end_dt}): {chunk_e}")
            # Ensure loop progresses even if a chunk fails
            current_start_chunk = chunk_end_dt # If chunk_end_dt is exclusive, this correctly sets start for next chunk

        if all_chunks:
            try:
                df = pd.concat(all_chunks)
                # Ensure timezone consistency before removing duplicates
                if df.index.tz is None:
                    df.index = df.index.tz_localize('UTC')
                else:
                    df.index = df.index.tz_convert('UTC')
                df = df[~df.index.duplicated(keep='first')] # Remove potential overlaps
                df.sort_index(inplace=True)
                logger.info(f"Concatenated {len(all_chunks)} chunks for {yf_symbol}, total rows: {len(df)}")
            except Exception as concat_err:
                 logger.error(f"Error concatenating chunks for {yf_symbol}: {concat_err}")
                 df = pd.DataFrame() # Return empty if concat fails
        else:
            logger.error(f"Failed to fetch any intraday chunks for {yf_symbol}")
            # df remains empty

    else:
        # Fetch non-intraday data or shorter intraday periods directly (with retry)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}: Fetching yfinance history for {yf_symbol}, Interval: {interval}, Start: {start_dt}, End: {end_dt}")
                df_attempt = ticker.history(start=start_dt, end=end_dt, interval=interval) # Use deterministic start_dt and end_dt
                logger.info(f"Attempt {attempt + 1}: yfinance returned {len(df_attempt)} rows for {yf_symbol}")
                if not df_attempt.empty:
                    df = df_attempt # Assign to df only on success
                    logger.debug(f"Successfully fetched data on attempt {attempt + 1}")
                    break # Exit loop on success
                else:
                    logger.warning(f"Attempt {attempt + 1}: yfinance returned empty DataFrame for {yf_symbol}")
                    if attempt == max_retries - 1: # Log final failure only
                         logger.error(f"Failed to fetch data for {symbol} ({yf_symbol}) after {max_retries} attempts.")
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch data for {symbol} ({yf_symbol}) after {max_retries} attempts: {str(e)}")
                    # Don't raise error, just return empty df
                    # raise e
            # No need for explicit continue, loop proceeds

    # Check if data is still empty after all attempts/chunking
    if df.empty:
        logger.error(f"No data retrieved for {symbol} ({yf_symbol}) with interval {interval} for {days} days.")
        return pd.DataFrame() # Return empty DataFrame

    # Clean and format the data
    try:
        df.columns = [col.lower() for col in df.columns]
        # Ensure required columns exist before selecting
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns for {symbol}: {missing_cols}. Available: {df.columns.tolist()}")
            return pd.DataFrame() # Return empty if essential columns are missing
        df = df[required_cols]
    except Exception as format_err:
        logger.error(f"Error formatting columns for {symbol}: {format_err}")
        return pd.DataFrame()

    # Ensure index is timezone-aware UTC
    try:
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
    except Exception as tz_err:
        logger.error(f"Error setting timezone for {symbol}: {tz_err}")
        return pd.DataFrame()

    # Add logging for data quality
    logger.info(f"Successfully processed {len(df)} base bars of {interval} data for {symbol} ({yf_symbol})")
    if not df.empty:
        logger.info(f"Base data date range: {df.index.min()} to {df.index.max()}")

    # --- Calculate Rolling Weekly Data ---
    if not df.empty:
        try:
            logger.info(f"Calculating rolling weekly data for {symbol} with multiplier {INDICATOR_LONG_TERM_FREQ_MULTIPLIER}...")
            weekly_df = _calculate_rolling_weekly_data(df, INDICATOR_LONG_TERM_FREQ_MULTIPLIER)
            if not weekly_df.empty:
                # Merge weekly data back into the main dataframe
                df = df.join(weekly_df)
                logger.info(f"Successfully calculated and merged rolling weekly data. Total columns: {df.columns.tolist()}")
            else:
                logger.warning(f"Rolling weekly data calculation returned empty for {symbol}. Proceeding without weekly columns.")
        except Exception as weekly_calc_err:
            logger.error(f"Error calculating rolling weekly data for {symbol}: {weekly_calc_err}", exc_info=True)
            # Proceed without weekly columns if calculation fails

    # --- Caching ---
    return df

# --- Helper Function for Rolling Weekly Data ---
def _calculate_rolling_weekly_data(daily_df: pd.DataFrame, multiplier: int) -> pd.DataFrame:
    """
    Calculates rolling weekly OHLCV data based on a multiplier of daily periods.

    Args:
        daily_df: DataFrame with daily OHLCV data, indexed by timestamp.
        multiplier: The number of daily periods in one weekly period.

    Returns:
        DataFrame with weekly_open, weekly_high, weekly_low, weekly_close, weekly_volume columns,
        indexed the same as daily_df. Returns empty DataFrame if input is unsuitable.
    """
    if daily_df.empty or not isinstance(daily_df.index, pd.DatetimeIndex):
        logger.warning("Cannot calculate rolling weekly data: daily_df is empty or index is not DatetimeIndex.")
        return pd.DataFrame()

    if multiplier <= 1:
        logger.warning(f"Multiplier ({multiplier}) must be greater than 1 for rolling weekly calculation.")
        return pd.DataFrame() # Or maybe return specific columns filled with daily data? Returning empty for now.

    if len(daily_df) < multiplier:
        logger.warning(f"Not enough daily data ({len(daily_df)}) to form a full weekly bar with multiplier {multiplier}.")
        # We can still calculate partial bars, so proceed.

    # Ensure data is sorted by time (should already be, but double-check)
    daily_df = daily_df.sort_index()

    # Create a grouping key for each weekly period
    group_key = np.arange(len(daily_df)) // multiplier

    # Calculate weekly columns using groupby and transform/expanding
    weekly_data = pd.DataFrame(index=daily_df.index)

    # Weekly Open: The first open price in each group
    weekly_data['weekly_open'] = daily_df.groupby(group_key)['open'].transform('first')

    # Weekly High: The expanding maximum high within each group
    weekly_data['weekly_high'] = daily_df.groupby(group_key)['high'].expanding().max().droplevel(0)

    # Weekly Low: The expanding minimum low within each group
    weekly_data['weekly_low'] = daily_df.groupby(group_key)['low'].expanding().min().droplevel(0)

    # Weekly Close: The close price of the *current* daily bar
    weekly_data['weekly_close'] = daily_df['close'] # It updates with each daily bar

    # Weekly Volume: The expanding sum of volume within each group
    weekly_data['weekly_volume'] = daily_df.groupby(group_key)['volume'].expanding().sum().droplevel(0)

    # Handle potential NaNs introduced by grouping/expanding, especially at the start
    # Forward fill might be appropriate for open, but others depend on the first bar's value
    # Let's fill NaNs resulting from expanding() on the first element of a group with the value itself
    for col in ['weekly_high', 'weekly_low', 'weekly_volume']:
         weekly_data[col] = weekly_data[col].fillna(daily_df[col.split('_')[1]]) # Fill NaN weekly_high with daily high etc.
    # weekly_open should be fine with transform('first')

    logger.info(f"Calculated rolling weekly columns: {weekly_data.columns.tolist()}")
    return weekly_data


def get_latest_data(symbol: str, interval: str = default_interval_yahoo, limit: Optional[int] = None, days: int = default_backtest_interval, use_cache: bool = True) -> pd.DataFrame:
    """
    Get the most recent data points

    Args:
        symbol: Stock symbol
        interval: Data interval
        limit: Number of data points to return (default: None = all available data)
        days: Number of days of historical data to fetch (default: 3)
        use_cache: Whether to use cached data if available (default: True)

    Returns:
        DataFrame with the most recent data points
    """
    try:
        # Check if TRADING_SYMBOLS is empty or symbol doesn't exist
        if not TRADING_SYMBOLS:
            logger.error("TRADING_SYMBOLS is empty. Cannot fetch data. Stock list may need to be refreshed.")
            return pd.DataFrame()
        
        if symbol not in TRADING_SYMBOLS:
            logger.error(f"Symbol {symbol} not found in TRADING_SYMBOLS. Available symbols: {list(TRADING_SYMBOLS.keys())[:5]}...")
            return pd.DataFrame()
        # Fetch data for the specified number of days using the passed interval
        logger.info(f"get_latest_data: Fetching {days} days of {interval} data for {symbol}")
        df = fetch_historical_data(symbol, interval, days=days, use_cache=use_cache)

        if df.empty:
            logger.warning(f"fetch_historical_data returned empty DataFrame for {symbol}")
            return df

        # Filter for market hours (only if not a 24/7 market)
        market_hours = TRADING_SYMBOLS[symbol]['market_hours']
        if not (market_hours['start'] == '00:00' and market_hours['end'] == '23:59'):
            logger.debug(f"Filtering {symbol} data for market hours: {market_hours}")
            # Ensure index is timezone-aware UTC before converting
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            else:
                df.index = df.index.tz_convert('UTC')

            market_tz = market_hours['timezone']
            try:
                df.index = df.index.tz_convert(market_tz)
                start_time = datetime.strptime(market_hours['start'], '%H:%M').time()
                end_time = datetime.strptime(market_hours['end'], '%H:%M').time()

                # Apply market hours filter
                df = df[
                    (df.index.time >= start_time) &
                    (df.index.time <= end_time) &
                    (df.index.weekday < 5)  # Monday = 0, Friday = 4
                ]
                logger.debug(f"Applied market hours filter. Rows remaining: {len(df)}")
                # Convert back to UTC after filtering if needed, or keep in market tz?
                # Let's keep it consistent and convert back to UTC
                df.index = df.index.tz_convert('UTC')

            except Exception as tz_filter_err:
                logger.error(f"Error applying market hours filter for {symbol}: {tz_filter_err}")
                # Decide whether to return unfiltered data or empty
                # Returning unfiltered might be safer if filter fails unexpectedly
                # return pd.DataFrame()

        # Apply limit if specified
        if limit is not None:
            df_final = df.tail(limit)
            logger.info(f"get_latest_data: Returning {len(df_final)} rows for {symbol} after applying limit {limit}.")
            return df_final

        logger.info(f"get_latest_data: Returning {len(df)} rows for {symbol} (no limit applied).")
        return df

    except Exception as e:
        logger.error(f"Error in get_latest_data for {symbol}: {str(e)}", exc_info=True)
        # Return empty DataFrame on error instead of raising
        return pd.DataFrame()
        # raise

def is_market_open(symbol: str = 'SPY') -> bool:
    """Check if market is currently open for the given symbol"""
    try:
        # Check if TRADING_SYMBOLS is empty or symbol doesn't exist
        if not TRADING_SYMBOLS:
            logger.error("TRADING_SYMBOLS is empty. Cannot check market hours. Stock list may need to be refreshed.")
            return False
        
        if symbol not in TRADING_SYMBOLS:
            # Try to use the first available symbol as fallback
            if TRADING_SYMBOLS:
                fallback_symbol = next(iter(TRADING_SYMBOLS))
                logger.warning(f"Symbol {symbol} not found in TRADING_SYMBOLS. Using {fallback_symbol} as fallback for market hours.")
                symbol = fallback_symbol
            else:
                logger.error("No symbols available for market hours check.")
                return False
        
        market_hours = TRADING_SYMBOLS[symbol]['market_hours']
        now = datetime.now(pytz.UTC)

        # For 24/7 markets
        if market_hours['start'] == '00:00' and market_hours['end'] == '23:59':
            return True

        # Convert current time to market timezone
        market_tz = market_hours['timezone']
        market_time = now.astimezone(pytz.timezone(market_tz))

        # Check if it's a weekday
        if market_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Parse market hours
        start_time = datetime.strptime(market_hours['start'], '%H:%M').time()
        end_time = datetime.strptime(market_hours['end'], '%H:%M').time()
        current_time = market_time.time()

        return start_time <= current_time <= end_time

    except Exception as e:
        logger.error(f"Error checking market hours for {symbol}: {str(e)}")
        return False

# --- Test Unit ---
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("--- Running fetch.py Test Unit ---")

    # Check if TRADING_SYMBOLS is available for testing
    if not TRADING_SYMBOLS:
        logger.error("TRADING_SYMBOLS is empty. Cannot run test. Stock list may need to be refreshed.")
        logger.info("--- Test Unit Finished (Skipped due to empty TRADING_SYMBOLS) ---")
        exit(0)
    
    # Use the first available symbol for testing
    test_symbol = next(iter(TRADING_SYMBOLS))
    test_interval = '1h'
    test_days = 2 # Fetch enough data for a few weekly periods

    logger.info(f"Fetching data for {test_symbol}, Interval: {test_interval}, Days: {test_days} (Cache Disabled)")
    # Disable cache for testing to ensure calculation runs
    test_df = fetch_historical_data(symbol=test_symbol, interval=test_interval, days=test_days)

    if not test_df.empty:
        logger.info(f"Successfully fetched data. Shape: {test_df.shape}")
        logger.info(f"Columns: {test_df.columns.tolist()}")
        logger.info("Displaying last 10 rows with daily and weekly data:")
        # Select relevant columns for display clarity
        display_cols = ['open', 'high', 'low', 'close', 'volume',
                        'weekly_open', 'weekly_high', 'weekly_low', 'weekly_close', 'weekly_volume']
        # Ensure weekly columns exist before trying to select them
        cols_to_show = [col for col in display_cols if col in test_df.columns]
        print(test_df[cols_to_show].tail(10).to_string()) # Use to_string for better console output
    else:
        logger.error("Failed to fetch data for testing.")

    logger.info("--- Test Unit Finished ---")
