def rewrite_query(query):
    rules = {
        "main point": "core philosophy summary",
        "book ka": "according to the book",
        "resume": "professional experience domain skills"
    }

    for k, v in rules.items():
        if k in query.lower():
            query = query.lower().replace(k, v)

    return query
