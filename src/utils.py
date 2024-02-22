"""
utils.py
    This script contains supporting functions.
"""

from datetime import datetime, timedelta


def add_one_day(date_str: str) -> str:
    """
    This function adds one day to a given date.

    Args:
        data_str: string that contains the date in the format 'yyyy-mm-dd'.

    Returns:
        result_str: string that contains the date in the format 'yyyy-mm-dd', one day
            after.
    """

    # Convert the input string to a datetime object
    date_object = datetime.strptime(date_str, "%Y-%m-%d")

    # Calculate the next day
    next_day = date_object + timedelta(days=1)

    # Check if the day rolled over to the next month
    if next_day.month != date_object.month:
        # Set the day to the first day of the next month
        next_day = datetime(next_day.year, next_day.month, 1)

    # Format the result back to 'yyyy-mm-dd'
    result_str = next_day.strftime("%Y-%m-%d")

    return result_str
