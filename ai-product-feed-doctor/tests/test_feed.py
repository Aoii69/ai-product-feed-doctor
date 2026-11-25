import csv
from pathlib import Path
import unittest

from feed import export_feed, read_feed, validate_feed


class FeedTests(unittest.TestCase):
    def test_all_rules_and_duplicate_rows(self):
        sample = Path(__file__).resolve().parents[1] / "samples" / "feed-with-errors.csv"
        feed = read_feed(sample.read_bytes())
        issues = validate_feed(feed)
        self.assertEqual(list(zip(issues["CSV row"], issues["Issue"])), [
            (3, "Missing product name"),
            (4, "Missing SKU"),
            (5, "Duplicate SKU"),
            (5, "Invalid price"),
            (5, "Invalid stock quantity"),
            (6, "Duplicate SKU"),
            (6, "Invalid stock quantity"),
            (7, "Invalid price"),
        ])
        self.assertTrue(all(issues["Explanation"]))
        self.assertEqual(feed.iloc[0]["sku"], "001")

    def test_edge_cases_and_record_row_numbers(self):
        feed = read_feed(b"sku,name,price,stock\n001,\"Multi\nline\",2.5,0\n001 ,Item,NaN,1.0\n")
        issues = validate_feed(feed)
        self.assertEqual(issues["CSV row"].tolist(), [2, 3, 3, 3])
        self.assertEqual(feed.iloc[0]["name"], "Multi\nline")

    def test_csv_errors(self):
        for data, error in [
            (b"", ValueError),
            (b"sku,name,price\n", ValueError),
            (b"sku,name,price,stock,stock\n", ValueError),
            (b"sku,name,price,stock\n1,Item,2\n", ValueError),
            (b'sku,name,price,stock\n1,"unclosed', csv.Error),
            (b"\xff", UnicodeDecodeError),
        ]:
            with self.subTest(data=data), self.assertRaises(error):
                read_feed(data)

    def test_reviewed_export_round_trip(self):
        original = read_feed(b"sku,name,price,stock,tag\n007,,12.00,,NA\n")
        draft = original.copy()
        draft.loc[0, ["name", "stock"]] = ["Cup, blue", "0"]
        self.assertTrue(validate_feed(draft).empty)
        self.assertEqual(original.loc[0, "name"], "")
        self.assertTrue(read_feed(export_feed(draft)).equals(draft))

    def test_blank_extra_columns_are_flagged_until_corrected(self):
        feed = read_feed(
            b"origin,sku,name,price,stock,category\n"
            b",001,Mug,4.50,0,Kitchen\n"
            b"   ,002,Pen,2.50,5,\n"
            b"Japan,003,Cup,9.00,2,Kitchen\n"
        )
        issues = validate_feed(feed)
        self.assertEqual(list(issues.iloc[:, :3].itertuples(index=False, name=None)), [
            (2, "origin", "Missing value"),
            (3, "origin", "Missing value"),
            (3, "category", "Missing value"),
        ])
        self.assertEqual(feed["origin"].tolist(), ["", "   ", "Japan"])
        feed.loc[[0, 1], "origin"] = ["Portugal", "Germany"]
        feed.loc[1, "category"] = "Office"
        self.assertTrue(validate_feed(feed).empty)

    def test_only_selected_extra_columns_are_required(self):
        feed = read_feed(b"sku,name,price,stock,origin,secondary_color\n001,Mug,invalid,0,   ,\n")
        issues = validate_feed(feed, ["origin"])
        self.assertEqual(issues["Column"].tolist(), ["price", "origin"])
        self.assertEqual(validate_feed(feed, [])["Column"].tolist(), ["price"])

    def test_header_only(self):
        feed = read_feed(b"sku,name,price,stock\n")
        self.assertTrue(validate_feed(feed).empty)
        self.assertTrue(read_feed(export_feed(feed)).equals(feed))


if __name__ == "__main__":
    unittest.main()
