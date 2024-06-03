import unittest
from datetime import datetime, timedelta
from ast_transform.timelang import get_timestamp_from_code

class TestDateParser(unittest.TestCase):

    def setUp(self):
        # Fixed current time for consistent testing
        self.current_time = datetime(2023, 3, 14, 12, 0, 0)
        print(self.current_time)
   
    def test_one_hour_ago(self):
        result = get_timestamp_from_code("1 hour ago", current_time=self.current_time)
        expected = (self.current_time - timedelta(hours=1)).isoformat()
        self.assertEqual(result, expected)
    
    def test_one_day_from_now(self):
        result = get_timestamp_from_code("1 day from now", current_time=self.current_time)
        expected = (self.current_time + timedelta(days=1)).isoformat()
        self.assertEqual(result, expected)
    
    def test_specific_time(self):
        result = get_timestamp_from_code("March 15 2PM", current_time=self.current_time)
        expected = datetime(2023, 3, 15, 14, 0, 0).isoformat()
        self.assertEqual(result, expected)
    
    def test_specific_time_plus_one_day(self):
        result = get_timestamp_from_code("March 15 2PM plus 1 day end", current_time=self.current_time)
        expected = (datetime(2023, 3, 15, 14, 0, 0) + timedelta(days=1))
    
    def test_complex_date_code(self):
        result = get_timestamp_from_code("previous tuesday following April minus 1 year at 5PM end", current_time=self.current_time)
        expected = (datetime(2022, 4, 5, 17, 0, 0)).isoformat()
        self.assertEqual(result, expected)
    
    def setUp(self):
        # Fixed current time for consistent testing
        self.current_time = datetime(2023, 3, 14, 12, 0, 0)
    
    def test_one_hour_ago(self):
        result = get_timestamp_from_code("minus 1 hour", current_time=self.current_time)
        expected = (self.current_time - timedelta(hours=1)).isoformat()
        self.assertEqual(result, expected)
    
    def test_one_day_from_now(self):
        result = get_timestamp_from_code("plus 1 day", current_time=self.current_time)
        expected = (self.current_time + timedelta(days=1)).isoformat()
        self.assertEqual(result, expected)
    
    def test_specific_time(self):
        result = get_timestamp_from_code("March 15 2PM", current_time=self.current_time)
        expected = datetime(2023, 3, 15, 14, 0, 0).isoformat()
        self.assertEqual(result, expected)
    
    def test_specific_time_plus_one_day(self):
        result = get_timestamp_from_code("March 15 2PM plus 1 day end", current_time=self.current_time)
        expected = (datetime(2023, 3, 15, 14, 0, 0) + timedelta(days=1)).isoformat()
        self.assertEqual(result, expected)
    
    def test_complex_date_code(self):
        result = get_timestamp_from_code("previous Tuesday following April minus 1 year at 5PM end", current_time=self.current_time)
        expected = (datetime(2022, 4, 7, 17, 0, 0)).isoformat()
        self.assertEqual(result, expected)
    
    def test_month_plus_one_month(self):
        result = get_timestamp_from_code("April plus 1 month end", current_time=self.current_time)
        expected = datetime(2023, 5, 31, 23, 59, 59, 999999).isoformat()
        self.assertEqual(result, expected)
    
    def test_year_date_month_plus_one_month(self):
        result = get_timestamp_from_code("February 13 2015 plus 1 month", current_time=self.current_time)
        expected = datetime(2015, 3, 13).isoformat()
        self.assertEqual(result, expected)
    
    def test_year_date_time_month_plus_one_month(self):
        result = get_timestamp_from_code("February 13 2015 15:19 plus 1 month", current_time=self.current_time)
        expected = datetime(2015, 3, 13,15, 19).isoformat()
        self.assertEqual(result, expected)
    
    def test_month_minus_one_year(self):
        result = get_timestamp_from_code("April end minus 1 year", current_time=self.current_time)
        expected = datetime(2022, 4, 30, 23, 59,59,999999).isoformat()
        self.assertEqual(result, expected)
    
    def test_previous_monday(self):
        result = get_timestamp_from_code("previous Monday end", current_time=self.current_time)
        expected = datetime(2023, 3, 13, 23, 59,59,999999).isoformat()
        self.assertEqual(result, expected)
    
    def test_following_friday(self):
        result = get_timestamp_from_code("following Friday end", current_time=self.current_time)
        expected = datetime(2023, 3, 17, 23, 59, 59, 999999).isoformat()
        self.assertEqual(result, expected)
    
    def test_at_3pm(self):
        result = get_timestamp_from_code("at 3PM end", current_time=self.current_time)
        expected = datetime(2023, 3, 14, 15, 0, 0).isoformat()
        self.assertEqual(result, expected)
    
    def test_at_3am(self):
        result = get_timestamp_from_code("at 3AM end", current_time=self.current_time)
        expected = datetime(2023, 3, 14, 3, 0, 0).isoformat()
        self.assertEqual(result, expected)
    
    def test_april_5_2pm_plus_3_days(self):
        result = get_timestamp_from_code("April 5 2PM plus 3 days end", current_time=self.current_time)
        expected = datetime(2023, 4, 8, 14, 0, 0).isoformat()
        self.assertEqual(result, expected)
    
    def test_january_1_minus_1_year(self):
        result = get_timestamp_from_code("January 1 minus 1 year end", current_time=self.current_time)
        expected = datetime(2022, 12, 31, 23, 59, 59,999999).isoformat()
        self.assertEqual(result, expected)
    
    def test_previous_thursday_at_4pm_plus_1_week(self):
        result = get_timestamp_from_code("previous Thursday at 4PM plus 1 week end", current_time=self.current_time)
        expected = (datetime(2023, 3, 9, 16, 0, 0) + timedelta(weeks=1)).isoformat()
        self.assertEqual(result, expected)
    
    def test_next_wednesday_at_3pm_minus_2_days(self):
        result = get_timestamp_from_code("next Wednesday at 3PM minus 2 days end", current_time=self.current_time)
        expected = (datetime(2023, 3, 15, 15, 0, 0) - timedelta(days=2)).isoformat()
        self.assertEqual(result, expected)

if __name__ == '__main__':
    
    unittest.main()
