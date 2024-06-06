import re
from datetime import datetime, timedelta
import calendar
import pytz
import calendar
from datetime import datetime, timedelta
import traceback

def parse_specific_date(tokens, reference_date):
    pattern = re.compile(r'(\b\w+ \d{1,2}(?: \d{4})?\b)')
    match = pattern.match(' '.join(tokens))
    if match:
        date_str = match.group(0)
        try:
            if len(date_str.split()) == 3:
                parsed_date = datetime.strptime(date_str, '%B %d %Y')
            else:
                parsed_date = datetime.strptime(date_str, '%B %d')
                parsed_date = parsed_date.replace(year=reference_date.year)
            start_of_day = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = parsed_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            return parsed_date, len(date_str.split()), (start_of_day, end_of_day)
        except ValueError:
            return None, 0, None
    return None, 0, None

def parse_date_time(tokens, reference_date):
    pattern = re.compile(r'(\b\w+ \d{1,2}(?: \d{4})?) (\d{1,2}(:\d{2})?(am|pm)?)\b')
    match = pattern.match(' '.join(tokens))
    if match:
        date_str, time_str = match.groups()[0], match.groups()[1]
        try:
            if len(date_str.split()) == 3:
                parsed_date = datetime.strptime(date_str, '%B %d %Y')
            else:
                parsed_date = datetime.strptime(date_str, '%B %d')
                parsed_date = parsed_date.replace(year=reference_date.year)
            if 'am' in time_str or 'pm' in time_str:
                parsed_time = datetime.strptime(time_str, '%I:%M%p' if ':' in time_str else '%I%p').time()
            else:
                parsed_time = datetime.strptime(time_str, '%H:%M' if ':' in time_str else '%H').time()
            parsed_date = parsed_date.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)
            return parsed_date, len(date_str.split()) + 1, (parsed_date, parsed_date)
        except ValueError:
            return None, 0, None
    return None, 0, None

def parse_relative_date(tokens, reference_date):
    if tokens[0] in ['yesterday', 'today', 'tomorrow']:
        if tokens[0] == 'yesterday':
            parsed_date = reference_date - timedelta(days=1)
        elif tokens[0] == 'today':
            parsed_date = reference_date
        elif tokens[0] == 'tomorrow':
            parsed_date = reference_date + timedelta(days=1)
        start_of_day = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = parsed_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed_date, 1, (start_of_day, end_of_day)
    return None, 0, None

def parse_period(tokens, reference_date):
    if tokens[0] == 'last':
        if tokens[1] == 'week':
            start_of_week = reference_date - timedelta(days=reference_date.weekday() + 7)
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
            return start_of_week, 2, (start_of_week, end_of_week)
        elif tokens[1] == 'month':
            start_of_month = (reference_date.replace(day=1) - timedelta(days=1)).replace(day=1)
            start_of_month = start_of_month.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_month = (start_of_month.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            return start_of_month, 2, (start_of_month, end_of_month)
    elif re.match(r'\d{4}', tokens[0]):
        year = int(tokens[0])
        start_of_year = datetime(year, 1, 1, 0,0,0,0)
        end_of_year = datetime(year, 12, 31, 23, 59, 59, 999999)
        return start_of_year, 1, (start_of_year, end_of_year)
    return None, 0, None

day_names=[da.lower() for da in calendar.day_name]
def parse_day_of_week_adjustment(tokens, reference_date):
    pattern = re.compile(r'\b(previous|following)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b')
    match = pattern.match(' '.join(tokens))
    if match:
        direction, day_name = match.groups()
        target_day = day_names.index(day_name)
        current_day = reference_date.weekday()

        if direction == 'previous':
            days_diff = (current_day - target_day + 7) % 7 or 7
            adjusted_date = reference_date - timedelta(days=days_diff)
        elif direction == 'following':
            days_diff = (target_day - current_day + 7) % 7 or 7
            adjusted_date = reference_date + timedelta(days=days_diff)
        else:
            if current_day <= target_day:
                days_diff = target_day - current_day
            else:
                days_diff = 7 - (current_day - target_day)
            adjusted_date = reference_date + timedelta(days=days_diff)
        
        start_of_day = adjusted_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = adjusted_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return adjusted_date, 2 if direction else 1, (start_of_day, end_of_day)
    return None, 0, None

month_names=[mo.lower() for mo in calendar.month_name]
import calendar

def parse_month_adjustment(tokens, reference_date):
    pattern = re.compile(r'\b(previous|following)?\s*(january|february|march|april|may|june|july|august|september|october|november|december)\b')
    match = pattern.match(' '.join(tokens))
    if match:
        direction, month_name = match.groups()
        target_month = month_names.index(month_name)
        current_month = reference_date.month

        if direction == 'previous':
            if current_month > target_month:
                adjusted_date = reference_date.replace(month=target_month)
            else:
                adjusted_date = reference_date.replace(year=reference_date.year - 1, month=target_month)
        elif direction == 'following':
            if current_month < target_month:
                adjusted_date = reference_date.replace(month=target_month)
            else:
                adjusted_date = reference_date.replace(year=reference_date.year + 1, month=target_month)
        else:
            adjusted_date = reference_date.replace(month=target_month)
        
        start_of_month = adjusted_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(start_of_month.year, start_of_month.month)[1]
        end_of_month = start_of_month.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
        return adjusted_date, 2 if direction else 1, (start_of_month, end_of_month)
    return None, 0, None

def time_span_adjustment(tokens_consumed, reference_date, unit, quantity):
    if unit in ['hours', 'hour']:
        delta = timedelta(hours=quantity)
        adjusted_date = reference_date + delta
        return adjusted_date, tokens_consumed, (adjusted_date, adjusted_date)
    elif unit in ['minutes', 'minute']:
        delta = timedelta(minutes=quantity)
        adjusted_date = reference_date + delta
        return adjusted_date, tokens_consumed, (adjusted_date, adjusted_date)
    elif unit in ['days', 'day']:
        delta = timedelta(days=quantity)
        adjusted_date = reference_date + delta
        start_of_day = adjusted_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = adjusted_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return adjusted_date, tokens_consumed, (start_of_day, end_of_day)
    elif unit in ['weeks', 'week']:
        delta = timedelta(weeks=quantity)
        adjusted_date = reference_date + delta
        start_of_week = adjusted_date - timedelta(days=reference_date.weekday() + 7)
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        return adjusted_date, tokens_consumed, (start_of_week, end_of_week)
    elif unit in ['months', 'month']:
        month = reference_date.month - 1 + int(quantity)
        year = reference_date.year + month // 12
        month = month % 12 + 1
        adjusted_date = reference_date.replace(year=year, month=month)
        start_of_month = adjusted_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(adjusted_date.year, adjusted_date.month)[1]
        end_of_month = adjusted_date.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
        return adjusted_date, tokens_consumed, (start_of_month, end_of_month)
    elif unit in ['quarters', 'quarter']:
        current_month = reference_date.month
        current_quarter_start_month = ((current_month - 1) // 3) * 3 + 1
        new_quarter_start_month = current_quarter_start_month + int(quantity * 3)
        year = reference_date.year + (new_quarter_start_month - 1) // 12
        new_quarter_start_month = (new_quarter_start_month - 1) % 12 + 1
        adjusted_date = reference_date.replace(year=year, month=new_quarter_start_month, day=1)
        start_of_quarter = adjusted_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_quarter_month = (new_quarter_start_month + 2) % 12 + 1
        end_of_quarter_year = year if new_quarter_start_month + 2 <= 12 else year + 1
        end_of_quarter = datetime(end_of_quarter_year, end_of_quarter_month, 1) - timedelta(seconds=1)
        return adjusted_date, tokens_consumed, (start_of_quarter, end_of_quarter)
    elif unit in ['years', 'year']:
        adjusted_date = reference_date.replace(year=reference_date.year + int(quantity))
        start_of_year = adjusted_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_year = adjusted_date.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        return adjusted_date, tokens_consumed, (start_of_year, end_of_year)
    
def parse_time_span_adjustment(tokens, reference_date):
    pattern = re.compile(r'\b(previous|following)?\s*(hour|hours|minute|minutes|day|days|week|weeks|month|months|quarter|quarters|year|years)\b')
    match = pattern.match(' '.join(tokens))
    if match:
        direction, unit = match.groups()
        quantity = 1
        if direction == 'previous':
            quantity = -quantity
        return time_span_adjustment(2, reference_date, unit, quantity)   
    return None, 0, None

 
def parse_relative_time_shift(tokens, reference_date):
    pattern = re.compile(
        r'\b(plus|minus)\s+(\d+(\.\d+)?)\s+(hour|hours|minute|minutes|day|days|week|weeks|month|months|quarter|quarters|year|years)\b|\b(\d+(\.\d+)?)\s+(hour|hours|minute|minutes|day|days|week|weeks|month|months|quarter|quarters|year|years)\b|\b(hour|hours|minute|minutes|day|days|week|weeks|month|months|quarter|quarters|year|years)\b'
    )
    match = pattern.match(' '.join(tokens))
    if match:
        groups = match.groups()
        if groups[0] in ['plus', 'minus']:
            operator, quantity, unit = groups[0], groups[1], groups[3]
        elif len(groups)>4 and groups[4] is not None:
            operator, quantity, unit = 'plus', groups[4], groups[6]
        elif len(groups)>9:
            operator, quantity, unit = 'plus', 0, groups[9]
        else:
             return None, 0, None

        quantity = float(quantity) if quantity else 0
        if operator == 'minus':
            quantity = -quantity

        tokens_consumed = 3 if operator in ['plus', 'minus'] and quantity else 1

        return time_span_adjustment(tokens_consumed, reference_date, unit, quantity)   

    return None, 0, None

def parse_specific_time(tokens, reference_date):
    pattern = re.compile(r'\bat (\d{1,2}(:\d{2})?(am|pm)?)\b')
    match = pattern.match(' '.join(tokens))
    if match:
        time_str = match.group(1)
        if 'am' in time_str or 'pm' in time_str:
            parsed_time = datetime.strptime(time_str, '%I:%M%p' if ':' in time_str else '%I%p').time()
        else:
            parsed_time = datetime.strptime(time_str, '%H:%M' if ':' in time_str else '%H').time()
        adjusted_date = reference_date.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)
        return adjusted_date, 2 if ':' not in time_str else 3, (adjusted_date, adjusted_date)
    return None, 0, None

def parse_context_change(tokens, reference_date, time_range):
    if tokens[0] in ['start', 'end']:
        if tokens[0] == 'start':
            return time_range[0], 1, time_range
        elif tokens[0] == 'end':
            return time_range[1], 1, time_range
    return None, 0, time_range

def parse_date_code(date_code, current_time=None):
    if current_time is None:
        current_time = datetime.now()

    tokens = date_code.lower().strip().split()
    reference_date = current_time
    i = 0
    time_range = (current_time.replace(hour=0, minute=0, second=0, microsecond=0),
                  current_time.replace(hour=23, minute=59, second=59, microsecond=999999))

    initial_parsers = [parse_date_time, parse_specific_date, parse_relative_date, parse_period]
    adjustment_parsers = [parse_day_of_week_adjustment, parse_month_adjustment, parse_time_span_adjustment, parse_relative_time_shift, parse_specific_time, parse_context_change]

    # First pass: Use initial parsers
    for parser in initial_parsers:
        parsed_date, tokens_consumed, range_tuple = parser(tokens[i:], reference_date)
        if parsed_date:
            # print(f"{i} {parser.__name__}: {parsed_date}")
            reference_date = parsed_date
            time_range = range_tuple
            i += tokens_consumed
            break

    # Subsequent passes: Use adjustment and context parsers
    while i < len(tokens):
        for parser in adjustment_parsers:
            if parser == parse_context_change:
                parsed_date, tokens_consumed, _ = parser(tokens[i:], reference_date, time_range)
            else:
                parsed_date, tokens_consumed, range_tuple = parser(tokens[i:], reference_date)

            if parsed_date:
                # print(f"{i} {parser.__name__}: {parsed_date}")
                reference_date = parsed_date
                time_range = range_tuple
                i += tokens_consumed
                break
        else:
            # print(f"{i} skipped")
            i += 1  # If no parser matched, move to the next token

    return reference_date

def convFromUtc(utc_time, zone):
    time_zone = pytz.timezone(zone)  # Replace with your time zone
    local_time = utc_time.astimezone(time_zone)
    return local_time

def convToUtc(current_time, zone):
    time_zone = pytz.timezone(zone)
    if current_time.tzinfo is None:
        # Naive datetime
        localized_time = time_zone.localize(current_time)
    else:
        # Aware datetime
        localized_time = current_time.astimezone(time_zone)
    utc_time = localized_time.astimezone(pytz.utc)
    return utc_time

def get_timestamp_from_code(date_code, current_time=None):
    # print(date_code)
    timestamp = parse_date_code(date_code, current_time)
    return timestamp.isoformat().replace('+00:00', 'Z')

# Example usage
# print(parse_date_code("March 15 plus 3 hours", current_time=datetime(2023, 3, 14)))
