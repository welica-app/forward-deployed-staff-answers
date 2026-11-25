import csv
import io
import json
import threading
import unittest
from http.client import HTTPConnection
from urllib.error import URLError

from handbook import STARTER, load_handbook, read_data, search_passages
from model import ApiModel, ModelError, RecordedModel
from serve import HOST, make_server


class DataAndHelpersTest(unittest.TestCase):
    def test_case_files_have_matching_ids_and_blank_scores(self):
        questions = read_data("questions.json")
        question_ids = [case["id"] for case in questions]
        with (STARTER / "case_scores.csv").open(encoding="utf-8", newline="") as file:
            scores = list(csv.DictReader(file))

        self.assertEqual(len(question_ids), 6)
        self.assertEqual(len(set(question_ids)), 6)
        self.assertEqual(set(read_data("recorded_replies.json")), set(question_ids))
        self.assertEqual([row["case_id"] for row in scores], question_ids)
        for row in scores:
            self.assertTrue(all(not value for key, value in row.items() if key != "case_id"))

    def test_search_ranks_supplied_passages_and_can_find_no_match(self):
        passages = load_handbook()["passages"]
        question = read_data("questions.json")[0]["question"]
        ids = [passage["id"] for passage in search_passages(question, passages, limit=2)]
        self.assertEqual(ids, ["ARCH-01", "HB-01"])
        self.assertEqual(search_passages("Bicycles", passages), [])

    def test_recorded_model_changes_draft_when_relevant_passage_is_supplied(self):
        question = read_data("questions.json")[0]["question"]
        passage = load_handbook()["passages"][0]
        model = RecordedModel()

        before = model.draft(question, [])
        self.assertEqual(before, model.draft(question, []))
        self.assertEqual(before["sourceIds"], ["ARCH-01"])
        self.assertIn("8 minutes", before["answer"])
        with_passage = model.draft(question, [passage])
        self.assertEqual(with_passage["sourceIds"], ["HB-01"])
        self.assertIn("12 minutes", with_passage["answer"])


class ApiFixtureTest(unittest.TestCase):
    def test_api_adapter_translates_request_and_response(self):
        question = "Which dispatch desk handles a change?"
        passages = [{"id": "fixture-1", "text": "Use the room on the left."}]
        expected = {"answer": "Use the room on the left.", "sourceIds": ["fixture-1"]}

        def fixture(request, timeout):
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            self.assertEqual(request.get_header("Authorization"), "Bearer fixture-only-token")
            self.assertEqual(request.get_header("Content-type"), "application/json")
            self.assertEqual(timeout, 20)
            payload = json.loads(request.data)
            self.assertEqual(payload["model"], "fixture-model")
            self.assertFalse(payload["store"])
            self.assertIn("supplied material", payload["instructions"])
            output_format = payload["text"]["format"]
            self.assertEqual(output_format["type"], "json_schema")
            self.assertEqual(output_format["name"], "staff_answer_draft")
            self.assertIs(output_format["strict"], True)
            self.assertEqual(
                output_format["schema"],
                {
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "sourceIds": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["answer", "sourceIds"],
                    "additionalProperties": False,
                },
            )
            self.assertEqual(
                json.loads(payload["input"]),
                {"question": question, "passages": passages},
            )
            body = {
                "status": "completed",
                "output": [
                    {"type": "reasoning", "summary": []},
                    {
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": json.dumps(expected), "annotations": []}
                        ],
                    },
                ],
            }
            return io.BytesIO(json.dumps(body).encode("utf-8"))

        model = ApiModel("fixture-only-token", "fixture-model", opener=fixture)
        self.assertEqual(model.draft(question, passages), expected)

    def test_api_adapter_reports_bad_replies_and_connection_errors(self):
        cases = [
            ("incomplete", {"type": "output_text", "text": '{"answer":"Draft"'}, "did not finish"),
            ("completed", {"type": "refusal", "refusal": "Fixture refusal"}, "declined"),
            (
                "completed",
                {"type": "output_text", "text": '{"answer":"Draft","sourceIds":[2]}'},
                "unreadable",
            ),
            (
                "completed",
                {"type": "output_text", "text": '{"answer":"Draft","sourceIds":[],"extra":true}'},
                "unreadable",
            ),
            ("completed", {"type": "output_text", "text": "This is not JSON."}, "unreadable"),
        ]
        for status, part, message in cases:
            with self.subTest(status=status, part=part):
                result = {
                    "status": status,
                    "output": [{"type": "message", "content": [part]}],
                }
                body = json.dumps(result).encode("utf-8")
                model = ApiModel(
                    "fixture-only-token",
                    "fixture-model",
                    opener=lambda request, timeout: io.BytesIO(body),
                )
                with self.assertRaisesRegex(ModelError, message):
                    model.draft("Any question", [])

        def unavailable(request, timeout):
            raise URLError("Fixture offline")

        unavailable_model = ApiModel("fixture-only-token", "fixture-model", opener=unavailable)
        with self.assertRaisesRegex(ModelError, "unavailable"):
            unavailable_model.draft("Any question", [])


class LocalScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0, RecordedModel())
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def send(self, method, path, value=None):
        connection = HTTPConnection(HOST, self.server.server_address[1], timeout=3)
        try:
            body = json.dumps(value) if value is not None else None
            headers = {"Content-Type": "application/json"} if body is not None else {}
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read().decode("utf-8")
        finally:
            connection.close()

    def test_screen_and_questions_are_served(self):
        status, page = self.send("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("<h1>Staff answers</h1>", page)
        status, script = self.send("GET", "/screen.js")
        self.assertEqual(status, 200)
        self.assertIn('"/api/answer"', script)
        status, questions = self.send("GET", "/api/questions")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(questions), read_data("questions.json"))

    def test_sample_questions_return_a_displayable_reply(self):
        for case in read_data("questions.json"):
            with self.subTest(case=case["id"]):
                status, data = self.send("POST", "/api/answer", {"question": case["question"]})
                self.assertEqual(status, 200)
                reply = json.loads(data)
                self.assertIn(reply["status"], ("draft", "answer", "fallback"))
                self.assertIsInstance(reply["answer"], str)
                self.assertIsInstance(reply["sources"], list)

    def test_blank_question_returns_a_prompt(self):
        status, data = self.send("POST", "/api/answer", {"question": " "})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(data))


if __name__ == "__main__":
    unittest.main()
