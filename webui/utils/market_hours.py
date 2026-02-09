"""
Market hours utilities for validating trading hours and checking if the market is open.
"""

import datetime
import pytz
from typing import List, Tuple, Dict, Any

# US stock market holidays (simplified - in production, use a proper holidays library)
US_MARKET_HOLIDAYS_2024 = [
    "2024-01-01",  # New Year's Day
    "2024-01-15",  # Martin Luther King Jr. Day
    "2024-02-19",  # Presidents' Day
    "2024-03-29",  # Good Friday
    "2024-05-27",  # Memorial Day
    "2024-06-19",  # Juneteenth
    "2024-07-04",  # Independence Day
    "2024-09-02",  # Labor Day
    "2024-11-28",  # Thanksgiving Day
    "2024-12-25",  # Christmas Day
]

US_MARKET_HOLIDAYS_2025 = [
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # Martin Luther King Jr. Day
    "2025-02-17",  # Presidents' Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving Day
    "2025-12-25",  # Christmas Day
]

# Market regular hours (EST/EDT)
MARKET_OPEN_HOUR = 9   # 9:30 AM (use 9 for conservative approach)
MARKET_CLOSE_HOUR = 16  # 4:00 PM

def validate_market_hours(hours_str: str) -> Tuple[bool, List[Tuple[int, int]], str]:
    """
    Validate market hours input string.

    Args:
        hours_str: String like "11", "11:30", or "10:30,14:15" representing times

    Returns:
        Tuple of (is_valid, parsed_times_list as [(hour, minute), ...], error_message)
    """
    if not hours_str or not hours_str.strip():
        return False, [], "Please enter at least one trading time"

    try:
        # Parse comma-separated times
        time_parts = [t.strip() for t in hours_str.split(',') if t.strip()]
        if not time_parts:
            return False, [], "Please enter at least one trading time"

        times = []
        for time_str in time_parts:
            # Parse HH:MM or just HH format
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) != 2:
                    return False, [], f"Invalid time format: {time_str}. Use HH:MM (e.g., 10:30)"
                hour = int(parts[0])
                minute = int(parts[1])
                if minute < 0 or minute > 59:
                    return False, [], f"Invalid minute: {minute}. Must be 0-59"
            else:
                hour = int(time_str)
                minute = 0

            # Validate hour is within market hours
            # Market opens at 9:30 and closes at 16:00
            time_in_minutes = hour * 60 + minute
            market_open_minutes = 9 * 60 + 30  # 9:30 AM
            market_close_minutes = 16 * 60  # 4:00 PM

            if time_in_minutes < market_open_minutes or time_in_minutes > market_close_minutes:
                return False, [], f"{hour}:{minute:02d} is outside market hours (9:30AM-4:00PM EST)"

            times.append((hour, minute))

        # Remove duplicates and sort by time
        times = sorted(list(set(times)), key=lambda x: x[0] * 60 + x[1])
        return True, times, ""

    except ValueError:
        return False, [], "Invalid format. Use HH:MM (e.g., 10:30) or just hour (e.g., 11)"

def is_market_open(target_datetime: datetime.datetime = None) -> Tuple[bool, str]:
    """
    Check if the US stock market is open at the given datetime.

    Args:
        target_datetime: Datetime to check (defaults to current time)

    Returns:
        Tuple of (is_open, reason_if_closed)
    """
    eastern = pytz.timezone('US/Eastern')

    if target_datetime is None:
        # Get current time directly in Eastern timezone
        target_datetime = datetime.datetime.now(eastern)
    elif target_datetime.tzinfo is None:
        # Naive datetime - assume it's already in Eastern time
        target_datetime = eastern.localize(target_datetime)
    else:
        # Has timezone - convert to Eastern
        target_datetime = target_datetime.astimezone(eastern)
    
    # Check if it's a weekend
    if target_datetime.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False, "Market is closed on weekends"
    
    # Check if it's a holiday
    date_str = target_datetime.strftime("%Y-%m-%d")
    all_holidays = US_MARKET_HOLIDAYS_2024 + US_MARKET_HOLIDAYS_2025
    if date_str in all_holidays:
        return False, f"Market is closed for holiday on {date_str}"
    
    # Check if it's within market hours (9:30 AM - 4:00 PM EST/EDT)
    market_open = target_datetime.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = target_datetime.replace(hour=16, minute=0, second=0, microsecond=0)
    
    if target_datetime < market_open:
        return False, f"Market opens at 9:30 AM EST/EDT (currently {target_datetime.strftime('%I:%M %p %Z')})"
    elif target_datetime > market_close:
        return False, f"Market closed at 4:00 PM EST/EDT (currently {target_datetime.strftime('%I:%M %p %Z')})"
    
    return True, "Market is open"

def get_next_market_datetime(target_time: Tuple[int, int], from_datetime: datetime.datetime = None) -> datetime.datetime:
    """
    Get the next market datetime for the specified time.

    Args:
        target_time: Tuple of (hour, minute) to target (e.g., (11, 30) for 11:30 AM)
        from_datetime: Starting datetime (defaults to current time in Eastern)

    Returns:
        Next datetime when market will be open at the target time
    """
    eastern = pytz.timezone('US/Eastern')
    target_hour, target_minute = target_time

    if from_datetime is None:
        # Get current time in Eastern timezone (not local time!)
        from_datetime = datetime.datetime.now(eastern)
    elif from_datetime.tzinfo is None:
        # If no timezone, assume it's meant to be Eastern
        from_datetime = eastern.localize(from_datetime)
    else:
        # Convert to Eastern
        from_datetime = from_datetime.astimezone(eastern)

    # Start with today at the target time in Eastern time
    target_dt = from_datetime.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

    # If the target time today has already passed, start with tomorrow
    if target_dt <= from_datetime:
        target_dt += datetime.timedelta(days=1)

    # Keep advancing until we find a valid market day
    max_attempts = 10  # Prevent infinite loops
    attempts = 0

    while attempts < max_attempts:
        is_open, reason = is_market_open(target_dt)
        if is_open:
            return target_dt

        # Move to next day
        target_dt += datetime.timedelta(days=1)
        attempts += 1

    # Fallback - return the target datetime even if we couldn't validate
    return target_dt

def get_local_timezone_info() -> Dict[str, Any]:
    """
    Get information about the user's local timezone relative to EST/EDT.

    Returns:
        Dictionary with timezone information including offset from Eastern time
    """
    eastern = pytz.timezone('US/Eastern')
    local_tz = datetime.datetime.now().astimezone().tzinfo

    # Get current time in both timezones
    now = datetime.datetime.now()
    now_eastern = datetime.datetime.now(eastern)
    now_local = datetime.datetime.now().astimezone()

    # Calculate offset in hours
    eastern_offset = now_eastern.utcoffset().total_seconds() / 3600
    local_offset = now_local.utcoffset().total_seconds() / 3600
    offset_from_eastern = local_offset - eastern_offset

    return {
        "local_tz_name": now_local.strftime("%Z"),
        "eastern_tz_name": now_eastern.strftime("%Z"),
        "offset_hours": offset_from_eastern,
        "offset_str": f"{'+' if offset_from_eastern >= 0 else ''}{int(offset_from_eastern)}h"
    }


def convert_est_hour_to_local(est_hour: int) -> Dict[str, Any]:
    """
    Convert an EST/EDT hour to local time.

    Args:
        est_hour: Hour in EST/EDT (0-23)

    Returns:
        Dictionary with local hour info
    """
    eastern = pytz.timezone('US/Eastern')

    # Create a datetime for today at the given EST hour
    now = datetime.datetime.now(eastern)
    est_datetime = now.replace(hour=est_hour, minute=0, second=0, microsecond=0)

    # Convert to local time
    local_datetime = est_datetime.astimezone()
    local_hour = local_datetime.hour

    # Check if day changed
    day_diff = (local_datetime.date() - est_datetime.date()).days
    day_indicator = ""
    if day_diff == 1:
        day_indicator = " (+1 day)"
    elif day_diff == -1:
        day_indicator = " (-1 day)"

    # Format the hour
    if local_hour == 0:
        local_formatted = "12:00 AM"
    elif local_hour < 12:
        local_formatted = f"{local_hour}:00 AM"
    elif local_hour == 12:
        local_formatted = "12:00 PM"
    else:
        local_formatted = f"{local_hour-12}:00 PM"

    return {
        "est_hour": est_hour,
        "local_hour": local_hour,
        "local_formatted": local_formatted + day_indicator,
        "local_tz": local_datetime.strftime("%Z"),
        "day_changed": day_diff != 0
    }


def get_market_hours_with_local_times(hours: List[int]) -> List[Dict[str, Any]]:
    """
    Get market hours with their local time equivalents.

    Args:
        hours: List of EST/EDT hours

    Returns:
        List of dictionaries with EST and local time info
    """
    result = []
    for hour in sorted(hours):
        # Format EST hour
        if hour == 0:
            est_formatted = "12:00 AM"
        elif hour < 12:
            est_formatted = f"{hour}:00 AM"
        elif hour == 12:
            est_formatted = "12:00 PM"
        else:
            est_formatted = f"{hour-12}:00 PM"

        local_info = convert_est_hour_to_local(hour)

        result.append({
            "est_hour": hour,
            "est_formatted": est_formatted,
            "local_hour": local_info["local_hour"],
            "local_formatted": local_info["local_formatted"],
            "local_tz": local_info["local_tz"]
        })

    return result


def format_time(hour: int, minute: int) -> str:
    """Format hour and minute as readable time string."""
    if hour == 0:
        return f"12:{minute:02d} AM"
    elif hour < 12:
        return f"{hour}:{minute:02d} AM"
    elif hour == 12:
        return f"12:{minute:02d} PM"
    else:
        return f"{hour-12}:{minute:02d} PM"


def format_market_hours_info(times: List[Tuple[int, int]]) -> Dict[str, Any]:
    """
    Format market hours information for display.

    Args:
        times: List of (hour, minute) tuples (e.g., [(11, 0), (13, 30)])

    Returns:
        Dictionary with formatted information
    """
    if not times:
        return {"error": "No times provided"}

    # Sort by time
    sorted_times = sorted(times, key=lambda x: x[0] * 60 + x[1])

    # Format times for display
    formatted_times = []
    for hour, minute in sorted_times:
        formatted_times.append(format_time(hour, minute))

    times_str = " and ".join(formatted_times)

    # Calculate next execution times
    next_executions = []
    for i, (hour, minute) in enumerate(sorted_times):
        next_dt = get_next_market_datetime((hour, minute))
        next_executions.append({
            "time": (hour, minute),
            "formatted_time": formatted_times[i],
            "next_datetime": next_dt,
            "next_formatted": next_dt.strftime("%A, %B %d at %I:%M %p %Z")
        })

    return {
        "times": sorted_times,
        "formatted_times": times_str,
        "next_executions": next_executions,
        "market_timezone": "US/Eastern"
    } 