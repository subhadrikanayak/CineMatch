from ml.data import slug

MOODS = {
    "happy": {"label": "Happy", "genres": ["Comedy", "Family", "Adventure"],
              "keywords": "fun laugh joy friendship celebration cheerful"},
    "sad": {"label": "Sad", "genres": ["Drama", "Romance"],
            "keywords": "loss grief tragedy heartbreak death emotional separation"},
    "romantic": {"label": "Romantic", "genres": ["Romance", "Rom-Com", "Drama"],
                 "keywords": "love romance relationship wedding couple marriage"},
    "thrilling": {"label": "Thrilling", "genres": ["Thriller", "Action", "Crime", "Mystery"],
                  "keywords": "suspense chase murder investigation revenge gangster"},
    "motivational": {"label": "Motivational", "genres": ["Drama", "Family"],
                     "keywords": "inspiration struggle underdog sports dream success determination biography"},
    "relaxed": {"label": "Relaxed", "genres": ["Comedy", "Family", "Romance", "Animation"],
                "keywords": "village family journey gentle everyday life"},
    "mind-bending": {"label": "Mind-bending", "genres": ["Sci-Fi", "Mystery", "Thriller"],
                     "keywords": "twist psychological mystery time dream conspiracy secret"},
    "feel-good": {"label": "Feel-good", "genres": ["Comedy", "Family", "Drama", "Rom-Com"],
                  "keywords": "friendship family hope heartwarming reunion community"},
}


def normalize_mood(name: str) -> str:
    return name.lower().strip().replace(" ", "-")


def mood_seed(mood: dict) -> str:
    return " ".join([f"gen_{slug(g)}" for g in mood["genres"]] * 3) + " " + mood["keywords"]