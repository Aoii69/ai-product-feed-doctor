from io import BytesIO
import json
from unittest import TestCase
from unittest.mock import patch

from ai_help import explain_issues


class AIHelpTests(TestCase):
    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    @patch("ai_help.urlopen")
    def test_missing_key_skips_network(self, urlopen):
        with self.assertRaises(ValueError):
            explain_issues({"Missing SKU": 1})
        urlopen.assert_not_called()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"})
    @patch("ai_help.urlopen")
    def test_only_known_issue_counts_are_sent(self, urlopen):
        response = {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": "Check your catalog."},
        ]}]}
        urlopen.return_value = BytesIO(json.dumps(response).encode())
        self.assertEqual(explain_issues({"Missing SKU": 2, "private SKU value": 1}), "Check your catalog.")
        request = urlopen.call_args.args[0]
        request_body = json.loads(request.data)
        self.assertEqual(json.loads(request_body["input"]), {"Missing SKU": 2})
        self.assertEqual(request_body["model"], "test-model")
        self.assertFalse(request_body["store"])
