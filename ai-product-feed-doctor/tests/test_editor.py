from io import BytesIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from feed import read_feed


class EditorTests(TestCase):
    def test_filtered_edit_is_retained_and_export_keeps_all_rows(self):
        sample = (
            b"sku,name,price,stock,origin\n"
            b"001,Mug,4.50,0,Japan\n"
            b"002,Pen,invalid,5,\n"
            b"003,Cup,9.00,2,Portugal\n"
        )
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=20)
        with patch("streamlit.file_uploader", return_value=BytesIO(sample)), patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            app.run()
            self.assertFalse(app.exception)
            self.assertFalse(app.checkbox(key="issues_only").value)
            self.assertEqual(app.dataframe[2].value.index.tolist(), [2, 3, 4])

            app.checkbox(key="approve_export").check().run()
            app.button(key="approve_csv").click().run()
            self.assertEqual(len(app.get("download_button")), 1)

            app.checkbox(key="issues_only").check().run()
            self.assertEqual(app.dataframe[2].value.index.tolist(), [3])
            self.assertEqual(len(app.get("download_button")), 1)

            # The editor reports a position within the visible rows.
            app.session_state["feed_editor_0_True"] = {
                "edited_rows": {0: {"origin": "Germany", "price": "2.50"}},
                "added_rows": [],
                "deleted_rows": [],
            }
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.info[0].value, "No rows with issues in the current draft.")
            self.assertFalse(app.checkbox(key="approve_export").value)
            self.assertFalse(app.get("download_button"))

            app.checkbox(key="issues_only").uncheck().run()
            self.assertEqual(app.dataframe[2].value.index.tolist(), [2, 3, 4])
            self.assertEqual(app.dataframe[2].value["origin"].tolist(), ["Japan", "Germany", "Portugal"])
            app.checkbox(key="approve_export").check().run()
            app.button(key="approve_csv").click().run()
            self.assertEqual(len(app.get("download_button")), 1)

            reviewed = read_feed(app.session_state["approved_csv"])
            self.assertEqual(reviewed["sku"].tolist(), ["001", "002", "003"])
            self.assertEqual(reviewed["origin"].tolist(), ["Japan", "Germany", "Portugal"])

    def test_undo_restores_deleted_stock_across_views(self):
        sample = b"sku,name,price,stock\n001,Mug,4.50,12\n"
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=20)
        with patch("streamlit.file_uploader", return_value=BytesIO(sample)):
            app.run()
            self.assertFalse(app.multiselect)
            self.assertTrue(app.button(key="undo_edit").proto.disabled)
            app.session_state["feed_editor_0_False"] = {
                "edited_rows": {0: {"stock": "15"}},
                "added_rows": [],
                "deleted_rows": [],
            }
            app.run()
            app.session_state["feed_editor_1_False"] = {
                "edited_rows": {0: {"stock": None}},
                "added_rows": [],
                "deleted_rows": [],
            }
            app.run()
            self.assertEqual(app.session_state["draft"].loc[2, "stock"], "")
            app.checkbox(key="issues_only").check().run()
            app.checkbox(key="approve_export").check().run()
            app.button(key="approve_csv").click().run()
            self.assertEqual(len(app.get("download_button")), 1)

            app.button(key="undo_edit").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["draft"].loc[2, "stock"], "15")
            self.assertEqual(app.info[0].value, "No rows with issues in the current draft.")
            self.assertTrue(app.button(key="undo_edit").proto.disabled)
            self.assertFalse(app.checkbox(key="approve_export").value)
            self.assertFalse(app.get("download_button"))

    def test_required_column_selection_updates_issues_and_keeps_draft(self):
        sample = (
            b"sku,name,price,stock,origin,secondary_color\n"
            b"001,Mug,4.50,0,,Blue\n"
            b"002,Pen,2.50,5,Germany,\n"
            b"003,Cup,invalid,2,Portugal,Red\n"
        )
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=20)
        with patch("streamlit.file_uploader", return_value=BytesIO(sample)), patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            app.run()
            self.assertEqual(app.multiselect[0].value, ["origin", "secondary_color"])
            self.assertEqual(str(app.metric[2].value), "3")
            app.session_state["feed_editor_0_False"] = {
                "edited_rows": {0: {"origin": "Japan"}},
                "added_rows": [],
                "deleted_rows": [],
            }
            app.run()
            app.checkbox(key="issues_only").check().run()
            self.assertEqual(app.dataframe[2].value.index.tolist(), [3, 4])
            app.checkbox(key="approve_export").check().run()
            app.button(key="approve_csv").click().run()
            self.assertTrue(app.get("download_button"))

            app.multiselect[0].unselect("secondary_color").run()
            self.assertFalse(app.exception)
            self.assertEqual(str(app.metric[2].value), "2")
            self.assertEqual(app.dataframe[1].value["Column"].tolist(), ["origin", "price"])
            self.assertEqual(app.dataframe[2].value.index.tolist(), [4])
            self.assertEqual(app.session_state["draft"].loc[2, "origin"], "Japan")
            self.assertFalse(app.button(key="undo_edit").proto.disabled)
            self.assertFalse(app.checkbox(key="approve_export").value)
            self.assertFalse(app.get("download_button"))

            app.multiselect[0].unselect("origin").run()
            self.assertEqual(app.dataframe[1].value["Column"].tolist(), ["price"])
            app.checkbox(key="approve_export").check().run()
            app.button(key="approve_csv").click().run()
            reviewed = read_feed(app.session_state["approved_csv"])
            self.assertEqual(reviewed["origin"].tolist(), ["Japan", "Germany", "Portugal"])
            self.assertEqual(reviewed["secondary_color"].tolist(), ["Blue", "", "Red"])

            app.button(key="undo_edit").click().run()
            self.assertEqual(app.session_state["draft"].loc[2, "origin"], "")
            self.assertEqual(app.dataframe[2].value.index.tolist(), [4])
