import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from handbook import STARTER, read_data
from model import ApiModel, ModelError, RecordedModel
from staff_answer import staff_answer

HOST = "127.0.0.1"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/screen.js": ("screen.js", "text/javascript; charset=utf-8"),
}


class StaffHandler(BaseHTTPRequestHandler):
    def send_content(self, status, content, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status, value):
        self.send_content(status, json.dumps(value).encode("utf-8"), "application/json")

    def do_GET(self):
        if self.path == "/api/questions":
            self.send_json(200, self.server.questions)
        elif self.path in STATIC_FILES:
            name, content_type = STATIC_FILES[self.path]
            self.send_content(200, (STARTER / name).read_bytes(), content_type)
        else:
            self.send_json(404, {"error": "Page not found."})

    def do_POST(self):
        if self.path != "/api/answer":
            self.send_json(404, {"error": "Page not found."})
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"error": "Send the question as JSON."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                raise ValueError
            body = json.loads(self.rfile.read(length))
            question = body["question"].strip()
        except (ValueError, KeyError, TypeError, AttributeError):
            self.send_json(400, {"error": "Enter a staff question."})
            return

        if not question or len(question) > 1000:
            self.send_json(400, {"error": "Enter a question of 1 to 1,000 characters."})
            return
        try:
            answer = staff_answer(question, self.server.model)
        except ModelError as error:
            self.send_json(502, {"error": str(error)})
            return
        self.send_json(200, answer)


def make_server(port, model):
    questions = read_data("questions.json")
    server = ThreadingHTTPServer((HOST, port), StaffHandler)
    server.questions = questions
    server.model = model
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", choices=("recorded", "api"), default="recorded")
    args = parser.parse_args()

    if args.model == "api":
        api_key = os.environ.get("STAFF_ANSWERS_API_KEY", "").strip()
        model_name = os.environ.get("STAFF_ANSWERS_MODEL", "").strip()
        if not api_key or not model_name:
            parser.error("API mode needs STAFF_ANSWERS_API_KEY and STAFF_ANSWERS_MODEL.")
        model = ApiModel(api_key, model_name)
    else:
        model = RecordedModel()

    try:
        with make_server(args.port, model) as server:
            port = server.server_address[1]
            print(f"Staff answers at http://{HOST}:{port}/ ({args.model} mode)", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError, OverflowError) as error:
        parser.exit(1, f"Cannot start the local server: {error}\n")


if __name__ == "__main__":
    main()
