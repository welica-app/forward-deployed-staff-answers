# Staff answers

This is a small screen where support staff at a meal delivery company type a question and get an answer from an AI model. Your job is to connect it to the company's handbook, so that every answer comes from the handbook's rules and shows where it came from. Each short piece of the handbook is called a passage. Each passage has an ID: a short label, such as `HB-01`, that names that one passage.

### The files

| File | What it holds |
|---|---|
| `index.html` | The staff screen: a question form, a list of sample questions and an area for the reply. |
| `screen.js` | Loads the sample questions, sends the form and shows the reply's status, answer and source IDs. It can show the statuses `draft`, `answer` and `fallback`. |
| `serve.py` | A small web server that runs only on your own computer, which is why it is called local. It is built only with Python's standard library. It serves the screen and the sample questions, checks each question sent to it and sets which model is used. |
| `staff_answer.py` | The feature's entry point, `staff_answer(question, model)`. The starting version gives the model the staff question and an empty list of passages and returns its reply unchecked, with the status `draft`. |
| `handbook.py` | Loads the handbook and has `search_passages(question, passages, limit=3)`. It ranks the passages by how many different words they share with the question, and sorts passages with the same count by ID. The starting version of the feature does not call it. |
| `handbook.json` | The company's made-up handbook: six approved passages, one archived passage, and `shift lead` as the person to ask. |
| `model.py` | The recorded model, and an optional connection to OpenAI's API, which is the way a program sends requests to OpenAI's models. Both have the same function, `draft(question, passages)`, and both return `answer` and `sourceIds`. |
| `questions.json` | The six sample questions, made up for this project, with case IDs `Q1` to `Q6`. |
| `recorded_replies.json` | Saved model replies for the six cases. Some depend on which passages the model was given, and some are unsupported on purpose. |
| `case_scores.csv` | A blank score sheet with one row for each case. Only `case_id` is filled in. The other columns are for what you expected, what you saw, scores for evidence and for handling, and notes. Leave this file blank, because a starter test checks that it is. Copy it to `case_scores_before.csv` and `case_scores_after.csv`, and fill in the copies. |
| `test_starter.py` | Eight starter tests. They check the data files, the search, both models and the local web routes. |
| `.gitignore` | Tells Git to ignore Python cache files, `.env` files and macOS system files. |

The screen talks to the server through the server's API: a small set of addresses that a program can send requests to. Each address is called a route, and the server has two API routes. `GET /api/questions` sends back the six cases. `POST /api/answer` takes the question as a JSON object, a common text format for data, with the field `question`. It sends back `status`, `answer` and `sources`. The model's `sourceIds` is called `sources` in this reply.

### How to start

You need Python 3 and a web browser. You do not need any Python packages or Node.

1. Download these files and unzip them, or clone the repository with Git.
2. Open a terminal in the folder that holds `serve.py`. Run every command from that folder.
3. Run the tests. All eight should pass:
   ```sh
   python3 -B -m unittest -v
   ```
4. Start the screen with recorded replies. You need no key for this, and it costs nothing. Use this run for all your scores:
   ```sh
   python3 -B serve.py
   ```
5. Open http://127.0.0.1:8000/. Tap a sample question to put it in the question box, then press `Ask`. Do this for all six.
6. Press Ctrl+C in the terminal to stop.
7. This step is optional, and you can skip it. It lets you try a real model in place of the recorded replies. The starter sends these requests to OpenAI, so you need your own OpenAI key and a model that supports Structured Outputs in the Responses API. Each question you send can cost you money. Whatever you type in the question box is sent to OpenAI, so in this mode use only the starter's made-up questions and handbook. Do not use it for your scores. Set `STAFF_ANSWERS_API_KEY` to your key and `STAFF_ANSWERS_MODEL` to the name of the model, then run the command below. A request goes to OpenAI only when you send a question. If either variable is missing, the command stops with an error.
   ```sh
   python3 -B serve.py --model api
   ```
