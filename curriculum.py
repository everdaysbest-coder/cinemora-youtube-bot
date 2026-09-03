"""
curriculum.py
=============
المنهج التعليمي المرتب لقناة Cinemora — من الحروف إلى القراءة.
كل عنصر في get_curriculum() هو "درس" واحد سيُنتَج له فيديو واحد.

الترتيب: 26 حرف → مفردات مصنّفة بموضوعات → جمل قراءة قصيرة.
بعد انتهاء القائمة بالكامل، يبدأ البوت من جديد (تكرار/مراجعة) تلقائيًا.
"""

# --------------------------------------------------------------------------
# المرحلة 1: الحروف الأبجدية (26 درس)
# --------------------------------------------------------------------------
LETTER_WORDS = {
    "A": "Apple", "B": "Ball", "C": "Cat", "D": "Dog", "E": "Elephant",
    "F": "Fish", "G": "Grapes", "H": "Hat", "I": "Ice cream", "J": "Juice",
    "K": "Kite", "L": "Lion", "M": "Monkey", "N": "Nest", "O": "Orange",
    "P": "Pig", "Q": "Queen", "R": "Rabbit", "S": "Sun", "T": "Tiger",
    "U": "Umbrella", "V": "Van", "W": "Watermelon", "X": "Xylophone",
    "Y": "Yo-yo", "Z": "Zebra",
}

ALPHABET_LESSONS = [
    {
        "stage": "alphabet",
        "letter": letter,
        "word": word,
        "sentence": f"{letter} is for {word}.",
        "overlay_lines": [letter, word],
    }
    for letter, word in LETTER_WORDS.items()
]

# --------------------------------------------------------------------------
# المرحلة 2: مفردات مصنّفة بموضوعات (كلمات ثابتة، ليست عشوائية)
# --------------------------------------------------------------------------
VOCAB_TOPICS = {
    "colors": ["Red", "Blue", "Yellow", "Green", "Orange", "Purple", "Pink", "Black", "White", "Brown"],
    "numbers": ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"],
    "family": ["Mom", "Dad", "Sister", "Brother", "Baby", "Grandma", "Grandpa"],
    "animals": ["Dog", "Cat", "Bird", "Fish", "Horse", "Cow", "Duck", "Sheep"],
    "food": ["Bread", "Milk", "Egg", "Banana", "Cheese", "Rice", "Cookie", "Water"],
    "shapes": ["Circle", "Square", "Triangle", "Star", "Heart"],
    "emotions": ["Happy", "Sad", "Angry", "Tired", "Excited", "Scared"],
    "actions": ["Run", "Jump", "Eat", "Sleep", "Play", "Read", "Sing", "Walk"],
    "body_parts": ["Head", "Hand", "Foot", "Eye", "Ear", "Nose", "Mouth"],
    "vehicles": ["Car", "Bus", "Train", "Plane", "Bike", "Boat"],
    "school": ["Book", "Pencil", "Bag", "Chair", "Desk"],
    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "clothes": ["Shirt", "Shoes", "Hat", "Socks", "Dress"],
    "weather": ["Sunny", "Rainy", "Cloudy", "Windy", "Snowy"],
    "seasons": ["Spring", "Summer", "Autumn", "Winter"],
}

VOCAB_SENTENCE_TEMPLATES = {
    "colors": "This is {word}.",
    "numbers": "I count to {word}.",
    "family": "This is my {word}.",
    "animals": "The {word} is here.",
    "food": "I like {word}.",
    "shapes": "This is a {word}.",
    "emotions": "I feel {word}.",
    "actions": "I can {word}.",
    "body_parts": "This is my {word}.",
    "vehicles": "I see a {word}.",
    "school": "This is my {word}.",
    "days": "Today is {word}.",
    "clothes": "I wear a {word}.",
    "weather": "It is {word} today.",
    "seasons": "I love {word}.",
}

VOCAB_LESSONS = []
for topic, words in VOCAB_TOPICS.items():
    template = VOCAB_SENTENCE_TEMPLATES[topic]
    for word in words:
        VOCAB_LESSONS.append({
            "stage": "vocabulary",
            "topic": topic,
            "word": word,
            "sentence": template.format(word=word.lower() if topic != "days" else word),
            "overlay_lines": [word],
        })

# --------------------------------------------------------------------------
# المرحلة 3: جمل قراءة قصيرة (لتعليم قراءة جملة كاملة وليس كلمة واحدة)
# --------------------------------------------------------------------------
READING_SENTENCES = [
    "I can jump.",
    "The cat is big.",
    "I see a red ball.",
    "She likes milk.",
    "He can run fast.",
    "This is my dog.",
    "The sun is hot.",
    "I have two hands.",
    "We play together.",
    "The bird can fly.",
    "I am happy today.",
    "The car is fast.",
    "She reads a book.",
    "We eat breakfast.",
    "The sky is blue.",
]

READING_LESSONS = [
    {
        "stage": "reading",
        "sentence": sentence,
        "overlay_lines": [sentence],
    }
    for sentence in READING_SENTENCES
]


def get_curriculum():
    """يرجّع المنهج الكامل مرتّبًا: حروف ثم مفردات ثم قراءة."""
    return ALPHABET_LESSONS + VOCAB_LESSONS + READING_LESSONS


def get_lesson(index: int) -> dict:
    """يرجّع الدرس المطابق للفهرس، مع تدوير (loop) تلقائي بعد انتهاء المنهج."""
    curriculum = get_curriculum()
    return curriculum[index % len(curriculum)]


def total_lessons() -> int:
    return len(get_curriculum())
