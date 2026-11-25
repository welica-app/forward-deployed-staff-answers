import json
from http.client import HTTPException
from urllib.request import Request, urlopen

from handbook import read_data

RESPONSES_URL = "https://api.openai.com/v1/responses"
FORMAT_INSTRUCTION = (
    "Draft a short reply to the staff question using the supplied material. "
    'Return a JSON object with an "answer" string and a "sourceIds" array of strings.'
)
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "sourceIds": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "sourceIds"],
    "additionalProperties": False,
}


class ModelError(Exception):
    pass


def question_key(question):
    return " ".join(question.casefold().split()).rstrip("?.!")


class RecordedModel:
    def __init__(self):
        replies = read_data("recorded_replies.json")
        self.replies = {
            question_key(case["question"]): replies[case["id"]]
            for case in read_data("questions.json")
        }

    def draft(self, question, passages):
        empty_reply = {"answer": "", "sourceIds": []}
        record = self.replies.get(question_key(question))
        if record is None:
            return empty_reply

        required_source = record.get("ifSource")
        supplied_ids = {passage["id"] for passage in passages}
        if required_source and required_source not in supplied_ids:
            return record.get("withoutSource", empty_reply)
        return record["draft"]


class ApiModel:
    def __init__(self, api_key, model_name, opener=urlopen):
        self.api_key = api_key
        self.model_name = model_name
        self.opener = opener

    def draft(self, question, passages):
        payload = {
            "model": self.model_name,
            "instructions": FORMAT_INSTRUCTION,
            "input": json.dumps({"question": question, "passages": passages}, ensure_ascii=False),
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "staff_answer_draft",
                    "strict": True,
                    "schema": REPLY_SCHEMA,
                }
            },
        }
        request = Request(
            RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=20) as response:
                result = json.load(response)
            if result["status"] != "completed":
                raise ModelError("The model service did not finish its reply.")

            content = [
                part
                for item in result["output"]
                if item["type"] == "message"
                for part in item["content"]
            ]
            if any(part["type"] == "refusal" for part in content):
                raise ModelError("The model service declined to answer.")
            reply = json.loads(
                "".join(part["text"] for part in content if part["type"] == "output_text")
            )
        except (OSError, HTTPException):
            raise ModelError("The model service is unavailable.") from None
        except (ValueError, TypeError, KeyError):
            raise ModelError("The model service returned an unreadable reply.") from None

        if (
            not isinstance(reply, dict)
            or reply.keys() != {"answer", "sourceIds"}
            or not isinstance(reply["answer"], str)
            or not isinstance(reply["sourceIds"], list)
            or any(not isinstance(source_id, str) for source_id in reply["sourceIds"])
        ):
            raise ModelError("The model service returned an unreadable reply.")
        return reply
