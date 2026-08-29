CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    topic TEXT,
    proficiency TEXT, -- One of: beginner, intermediate, advanced (NULL = auto-infer)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    feedback TEXT, -- Will store the JSON string of mistakes/corrections or NULL
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
