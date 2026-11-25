def staff_answer(question, model):
    # The starter sends no handbook passages and exposes the unchecked draft.
    draft = model.draft(question, passages=[])
    return {
        "status": "draft",
        "answer": draft["answer"],
        "sources": draft["sourceIds"],
    }
