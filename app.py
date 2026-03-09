# =============================================================================
#  app.py  –  ML-Based Resume Analyzer
#  Backend: Python + Flask + scikit-learn
# =============================================================================
#
#  How it works:
#    1. User uploads a resume (PDF / DOCX / TXT) through the web page
#    2. Flask receives the file and extracts plain text from it
#    3. The ML engine analyses the text against the chosen job domain
#    4. Results (score, matched skills, suggestions, etc.) are sent back
#       as JSON and displayed on the page
#
#  Run:
#    pip install -r requirements.txt
#    python app.py
#    Open → http://127.0.0.1:5000
# =============================================================================

import re
import io
import math
import json
import sqlite3
import hashlib
import os
from datetime import datetime
from collections import Counter
from functools import wraps
from flask import (Flask, request, jsonify, send_from_directory,
                   session, redirect, url_for)

# --- Optional ML libraries (graceful fallback if not installed) ---------------

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


# =============================================================================
#  DOMAIN SKILL DATASETS
#  Each domain has a list of skills that are expected for that job role.
# =============================================================================

DOMAIN_SKILLS = {
    "Data Science": [
        "Python", "R", "SQL", "Pandas", "NumPy", "Matplotlib",
        "Scikit-learn", "TensorFlow", "Tableau", "Power BI",
        "Statistics", "Machine Learning", "Data Visualization", "Excel", "Spark"
    ],
    "Web Development": [
        "HTML", "CSS", "JavaScript", "React", "Node.js", "Express",
        "MongoDB", "TypeScript", "REST API", "Git",
        "Docker", "Tailwind CSS", "Vue.js", "GraphQL", "Next.js"
    ],
    "AI/ML": [
        "Python", "TensorFlow", "PyTorch", "Scikit-learn", "NLP",
        "Computer Vision", "Deep Learning", "Keras", "OpenCV", "Transformers",
        "BERT", "LangChain", "MLflow", "Hugging Face", "CUDA"
    ],
    "DevOps": [
        "Docker", "Kubernetes", "CI/CD", "Jenkins", "AWS",
        "Azure", "GCP", "Terraform", "Ansible", "Linux",
        "Shell Scripting", "Git", "Prometheus", "Grafana", "Nginx"
    ],
    "Cybersecurity": [
        "Network Security", "Penetration Testing", "SIEM", "Firewalls",
        "Cryptography", "Ethical Hacking", "Kali Linux", "Wireshark", "Python",
        "Risk Assessment", "SOC", "OWASP", "Metasploit", "Incident Response", "Compliance"
    ],
    "Mobile Development": [
        "Swift", "Kotlin", "React Native", "Flutter", "iOS",
        "Android", "Dart", "Firebase", "REST API", "Git",
        "Xcode", "Android Studio", "SQLite", "Push Notifications", "Jetpack Compose"
    ],
    "Cloud Computing": [
        "AWS", "Azure", "GCP", "Terraform", "Kubernetes",
        "Docker", "Serverless", "Lambda", "S3", "IAM",
        "CloudFormation", "CDN", "Load Balancing", "VPC", "Cost Optimization"
    ],
    "Software Engineering": [
        "Java", "C++", "Python", "Design Patterns", "OOP",
        "Data Structures", "Algorithms", "Git", "Agile", "Scrum",
        "Unit Testing", "REST API", "Microservices", "SOLID Principles", "System Design"
    ],
    "UI/UX Design": [
        "Figma", "Adobe XD", "Wireframing", "Prototyping", "User Research",
        "Usability Testing", "Design Systems", "HTML", "CSS", "Accessibility",
        "Information Architecture", "Color Theory", "Typography", "Zeplin", "Motion Design"
    ],
    "Big Data Engineering": [
        "Apache Spark", "Hadoop", "Kafka", "Hive", "Flink",
        "Airflow", "Python", "Scala", "Data Pipelines", "ETL",
        "Data Lake", "Databricks", "Snowflake", "Data Warehousing", "dbt"
    ],
    "NLP": [
        "Python", "NLTK", "spaCy", "Transformers", "BERT",
        "GPT", "Tokenization", "Text Classification", "NER", "Sentiment Analysis",
        "Word2Vec", "LangChain", "Hugging Face", "RAG", "Fine-tuning"
    ],
    "QA & Testing": [
        "Manual Testing", "Selenium", "Cypress", "Jest", "JUnit",
        "TestNG", "API Testing", "Postman", "Performance Testing", "JMeter",
        "Test Planning", "Bug Tracking", "JIRA", "Automation", "BDD/TDD"
    ]
}


# =============================================================================
#  SYNONYM MAP
#  Many people write "k8s" instead of "Kubernetes", "js" instead of
#  "JavaScript", etc. This map helps us catch those variations.
# =============================================================================

SYNONYMS = {
    "JavaScript":       ["js", "nodejs", "node", "es6", "ecmascript"],
    "TypeScript":       ["ts"],
    "Python":           ["py", "python3"],
    "Machine Learning": ["ml", "supervised learning"],
    "Deep Learning":    ["neural network", "ann", "cnn", "rnn", "lstm"],
    "Docker":           ["containerization", "container"],
    "Kubernetes":       ["k8s", "container orchestration"],
    "CI/CD":            ["continuous integration", "continuous delivery", "github actions"],
    "SQL":              ["mysql", "postgresql", "postgres", "sqlite", "oracle"],
    "AWS":              ["amazon web services", "ec2", "lambda"],
    "Azure":            ["microsoft azure"],
    "GCP":              ["google cloud", "bigquery"],
    "Git":              ["github", "gitlab", "bitbucket", "version control"],
    "TensorFlow":       ["tf"],
    "PyTorch":          ["torch"],
    "NLP":              ["natural language processing", "text mining"],
    "Computer Vision":  ["image recognition", "object detection"],
    "REST API":         ["restful", "rest", "api", "web api"],
    "React":            ["reactjs", "react.js"],
    "Scikit-learn":     ["sklearn"],
    "Apache Spark":     ["spark", "pyspark"],
    "Vue.js":           ["vuejs", "vue", "nuxt"]
}

# Common English words that carry no useful signal for skill matching
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "do", "does", "did", "will", "would", "could", "should",
    "i", "my", "we", "our", "you", "your", "they", "their", "it", "its",
    "this", "that", "as", "if", "about", "each", "also", "while", "when",
    "where", "not", "no", "so", "just", "then", "than"
}


# =============================================================================
#  COMPANY RECOMMENDATIONS
#  Each company has a minimum score threshold. If the candidate's score
#  meets that threshold, the company is shown as a match.
# =============================================================================

COMPANIES = {
    "Data Science": [
        {"name": "Google",   "logo": "G", "color": "#4285F4", "role": "Data Scientist",  "min": 70,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Data+Scientist+Google",
         "indeed":   "https://indeed.com/q-data-scientist-google.html",
         "careers":  "https://careers.google.com"},
        {"name": "Meta",     "logo": "M", "color": "#0866FF", "role": "Data Scientist",  "min": 65,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Data+Scientist+Meta",
         "indeed":   "https://indeed.com/q-data-scientist-meta.html",
         "careers":  "https://metacareers.com"},
        {"name": "Spotify",  "logo": "S", "color": "#1DB954", "role": "ML Engineer",     "min": 50,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Data+Scientist+Spotify",
         "indeed":   "https://indeed.com/q-data-scientist-spotify.html",
         "careers":  "https://lifeatspotify.com"}
    ],
    "Web Development": [
        {"name": "Shopify",  "logo": "S", "color": "#96BF48", "role": "Frontend Engineer","min": 50,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Frontend+Shopify",
         "indeed":   "https://indeed.com/q-frontend-shopify.html",
         "careers":  "https://shopify.com/careers"},
        {"name": "Stripe",   "logo": "S", "color": "#635BFF", "role": "Frontend Engineer","min": 62,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Frontend+Stripe",
         "indeed":   "https://indeed.com/q-frontend-stripe.html",
         "careers":  "https://stripe.com/jobs"},
        {"name": "Vercel",   "logo": "V", "color": "#7928CA", "role": "Full Stack Eng",   "min": 55,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Frontend+Vercel",
         "indeed":   "https://indeed.com/q-fullstack-vercel.html",
         "careers":  "https://vercel.com/careers"}
    ],
    "AI/ML": [
        {"name": "OpenAI",      "logo": "O", "color": "#00A67E", "role": "ML Engineer",      "min": 76,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=ML+Engineer+OpenAI",
         "indeed":   "https://indeed.com/q-ml-engineer-openai.html",
         "careers":  "https://openai.com/careers"},
        {"name": "Anthropic",   "logo": "A", "color": "#C76B39", "role": "Research Scientist","min": 80,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Research+Scientist+Anthropic",
         "indeed":   "https://indeed.com/q-research-scientist-anthropic.html",
         "careers":  "https://anthropic.com/careers"},
        {"name": "Hugging Face","logo": "H", "color": "#F5A623", "role": "ML Engineer",      "min": 58,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=ML+Engineer+HuggingFace",
         "indeed":   "https://indeed.com/q-ml-engineer-huggingface.html",
         "careers":  "https://apply.workable.com/huggingface"}
    ],
    "DevOps": [
        {"name": "HashiCorp", "logo": "H", "color": "#7B42BC", "role": "DevOps Engineer", "min": 54,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=DevOps+HashiCorp",
         "indeed":   "https://indeed.com/q-devops-hashicorp.html",
         "careers":  "https://hashicorp.com/careers"},
        {"name": "Datadog",   "logo": "D", "color": "#632CA6", "role": "SRE",             "min": 56,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=SRE+Datadog",
         "indeed":   "https://indeed.com/q-sre-datadog.html",
         "careers":  "https://datadoghq.com/careers"},
        {"name": "GitLab",    "logo": "G", "color": "#FC6D26", "role": "DevOps Engineer", "min": 48,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=DevOps+GitLab",
         "indeed":   "https://indeed.com/q-devops-gitlab.html",
         "careers":  "https://about.gitlab.com/jobs"}
    ],
    "Cybersecurity": [
        {"name": "CrowdStrike","logo": "C", "color": "#E41E2B", "role": "Security Engineer","min": 56,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Security+Engineer+CrowdStrike",
         "indeed":   "https://indeed.com/q-security-crowdstrike.html",
         "careers":  "https://crowdstrike.com/careers"},
        {"name": "Palo Alto", "logo": "P", "color": "#00B4E0", "role": "Security Analyst", "min": 50,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Security+Analyst+PaloAlto",
         "indeed":   "https://indeed.com/q-security-paloalto.html",
         "careers":  "https://paloaltonetworks.com/company/careers"},
        {"name": "Okta",      "logo": "O", "color": "#00297A", "role": "Security Engineer","min": 48,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Security+Engineer+Okta",
         "indeed":   "https://indeed.com/q-security-okta.html",
         "careers":  "https://okta.com/company/careers"}
    ],
    "Mobile Development": [
        {"name": "Uber",      "logo": "U", "color": "#000000", "role": "iOS/Android Eng", "min": 56,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Mobile+Engineer+Uber",
         "indeed":   "https://indeed.com/q-mobile-engineer-uber.html",
         "careers":  "https://uber.com/careers"},
        {"name": "Duolingo",  "logo": "D", "color": "#58CC02", "role": "iOS Developer",   "min": 48,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Mobile+Developer+Duolingo",
         "indeed":   "https://indeed.com/q-mobile-duolingo.html",
         "careers":  "https://careers.duolingo.com"},
        {"name": "Discord",   "logo": "D", "color": "#5865F2", "role": "Mobile Engineer", "min": 52,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Mobile+Engineer+Discord",
         "indeed":   "https://indeed.com/q-mobile-discord.html",
         "careers":  "https://discord.com/careers"}
    ],
    "Cloud Computing": [
        {"name": "AWS",       "logo": "A", "color": "#FF9900", "role": "Cloud Architect",  "min": 62,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Cloud+Engineer+AWS",
         "indeed":   "https://indeed.com/q-cloud-engineer-amazon.html",
         "careers":  "https://aws.amazon.com/careers"},
        {"name": "Microsoft", "logo": "M", "color": "#0078D4", "role": "Cloud Engineer",   "min": 58,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Cloud+Engineer+Microsoft",
         "indeed":   "https://indeed.com/q-cloud-engineer-microsoft.html",
         "careers":  "https://careers.microsoft.com"},
        {"name": "Snowflake", "logo": "S", "color": "#29B5E8", "role": "Cloud Data Eng",   "min": 55,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Cloud+Engineer+Snowflake",
         "indeed":   "https://indeed.com/q-cloud-snowflake.html",
         "careers":  "https://careers.snowflake.com"}
    ],
    "Software Engineering": [
        {"name": "Microsoft", "logo": "M", "color": "#0078D4", "role": "Software Engineer","min": 60,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Software+Engineer+Microsoft",
         "indeed":   "https://indeed.com/q-software-engineer-microsoft.html",
         "careers":  "https://careers.microsoft.com"},
        {"name": "Amazon",    "logo": "A", "color": "#FF9900", "role": "SDE",              "min": 62,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Software+Engineer+Amazon",
         "indeed":   "https://indeed.com/q-software-engineer-amazon.html",
         "careers":  "https://amazon.jobs"},
        {"name": "Palantir",  "logo": "P", "color": "#6366f1", "role": "Software Engineer","min": 70,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Software+Engineer+Palantir",
         "indeed":   "https://indeed.com/q-software-engineer-palantir.html",
         "careers":  "https://palantir.com/careers"}
    ],
    "UI/UX Design": [
        {"name": "Figma",  "logo": "F", "color": "#A259FF", "role": "Product Designer",  "min": 52,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Product+Designer+Figma",
         "indeed":   "https://indeed.com/q-product-designer-figma.html",
         "careers":  "https://figma.com/careers"},
        {"name": "Canva",  "logo": "C", "color": "#00C4CC", "role": "UX Designer",       "min": 48,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=UX+Designer+Canva",
         "indeed":   "https://indeed.com/q-ux-designer-canva.html",
         "careers":  "https://canva.com/careers"},
        {"name": "Notion", "logo": "N", "color": "#818cf8", "role": "Product Designer",  "min": 50,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Product+Designer+Notion",
         "indeed":   "https://indeed.com/q-product-designer-notion.html",
         "careers":  "https://notion.so/careers"}
    ],
    "Big Data Engineering": [
        {"name": "Databricks","logo": "D", "color": "#FF3621", "role": "Data Engineer",  "min": 58,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Data+Engineer+Databricks",
         "indeed":   "https://indeed.com/q-data-engineer-databricks.html",
         "careers":  "https://databricks.com/company/careers"},
        {"name": "Snowflake", "logo": "S", "color": "#29B5E8", "role": "Data Engineer",  "min": 52,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Data+Engineer+Snowflake",
         "indeed":   "https://indeed.com/q-data-engineer-snowflake.html",
         "careers":  "https://careers.snowflake.com"},
        {"name": "Confluent", "logo": "C", "color": "#0088CC", "role": "Kafka Engineer", "min": 55,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=Data+Engineer+Confluent",
         "indeed":   "https://indeed.com/q-data-engineer-confluent.html",
         "careers":  "https://confluent.io/careers"}
    ],
    "NLP": [
        {"name": "OpenAI",    "logo": "O", "color": "#00A67E", "role": "NLP Engineer",     "min": 76,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=NLP+Engineer+OpenAI",
         "indeed":   "https://indeed.com/q-nlp-engineer-openai.html",
         "careers":  "https://openai.com/careers"},
        {"name": "Cohere",    "logo": "C", "color": "#39594D", "role": "NLP Engineer",     "min": 62,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=NLP+Engineer+Cohere",
         "indeed":   "https://indeed.com/q-nlp-engineer-cohere.html",
         "careers":  "https://cohere.com/careers"},
        {"name": "Grammarly", "logo": "G", "color": "#15C39A", "role": "ML/NLP Engineer",  "min": 56,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=NLP+Engineer+Grammarly",
         "indeed":   "https://indeed.com/q-nlp-engineer-grammarly.html",
         "careers":  "https://grammarly.com/jobs"}
    ],
    "QA & Testing": [
        {"name": "Atlassian",    "logo": "A", "color": "#0052CC", "role": "QA Engineer", "min": 50,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=QA+Engineer+Atlassian",
         "indeed":   "https://indeed.com/q-qa-engineer-atlassian.html",
         "careers":  "https://atlassian.com/company/careers"},
        {"name": "BrowserStack","logo": "B", "color": "#F26522", "role": "SDET",         "min": 46,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=SDET+BrowserStack",
         "indeed":   "https://indeed.com/q-sdet-browserstack.html",
         "careers":  "https://browserstack.com/careers"},
        {"name": "Sauce Labs",  "logo": "S", "color": "#E2231A", "role": "QA Engineer",  "min": 42,
         "linkedin": "https://linkedin.com/jobs/search/?keywords=QA+Engineer+SauceLabs",
         "indeed":   "https://indeed.com/q-qa-sauce-labs.html",
         "careers":  "https://saucelabs.com/company/careers"}
    ]
}


# =============================================================================
#  TEXT EXTRACTION
#  Converts the uploaded resume file into plain text so the ML engine
#  can process it.
# =============================================================================

def extract_text_from_file(file_bytes, filename):
    """
    Reads a resume file (PDF, DOCX, or TXT) and returns the plain text.
    Returns an empty string if extraction fails.
    """
    extension = filename.rsplit(".", 1)[-1].lower()

    # Plain text file — just decode it
    if extension == "txt":
        return file_bytes.decode("utf-8", errors="ignore")

    # PDF file — use pdfplumber to extract text page by page
    if extension == "pdf":
        if not PDF_AVAILABLE:
            return ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages)

    # Word document — use python-docx to read paragraphs
    if extension == "docx":
        if not DOCX_AVAILABLE:
            return ""
        doc = DocxDocument(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs]
        return "\n".join(paragraphs)

    return ""


# =============================================================================
#  ML HELPER FUNCTIONS
# =============================================================================

def tokenize_text(text):
    """
    Splits text into individual word tokens.
    Removes punctuation, converts to lowercase, and filters stop words.
    """
    # Remove everything except letters, numbers, spaces, # and .
    clean = re.sub(r"[^a-z0-9\s#.]", " ", text.lower())
    tokens = [word for word in clean.split()
              if len(word) > 1 and word not in STOP_WORDS]
    return tokens


def expand_with_synonyms(text):
    """
    Appends canonical skill names when synonyms are detected.
    For example, if the resume contains 'k8s', we append 'Kubernetes'
    so the ML matching step can find it.
    """
    lower_text = text.lower()
    extras = []

    for canonical_name, aliases in SYNONYMS.items():
        for alias in aliases:
            pattern = r"\b" + re.escape(alias.lower()) + r"\b"
            if re.search(pattern, lower_text):
                extras.append(canonical_name.lower())
                break  # no need to check other aliases for this skill

    return text + " " + " ".join(extras)


def jaccard_similarity(set_a, set_b):
    """
    Computes Jaccard similarity between two token sets.
    Formula: |A ∩ B| / |A ∪ B|
    Returns a value between 0.0 (no overlap) and 1.0 (identical sets).
    """
    if not set_a and not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union


def tfidf_cosine_similarity(resume_text, skill_text):
    """
    Computes TF-IDF cosine similarity between the resume and a skill phrase.
    This is the core ML step — it weighs rare but important terms higher.
    Falls back to 0.0 if scikit-learn is not installed.
    """
    if not SKLEARN_AVAILABLE:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        matrix = vectorizer.fit_transform([resume_text, skill_text])
        score = cosine_similarity(matrix[0], matrix[1])
        return float(score[0][0])
    except Exception:
        return 0.0


def manual_cosine_similarity(tokens_a, tokens_b, idf_weights):
    """
    Fallback cosine similarity calculation using plain Python math.
    Used when scikit-learn is not available.
    """
    def tf(tokens):
        total = len(tokens) or 1
        freq = Counter(tokens)
        return {word: count / total for word, count in freq.items()}

    def tfidf_vector(tokens):
        tf_scores = tf(tokens)
        return {word: tf_scores[word] * idf_weights.get(word, 1.0)
                for word in tokens}

    vec_a = tfidf_vector(tokens_a)
    vec_b = tfidf_vector(tokens_b)

    # Dot product
    common = set(vec_a) & set(vec_b)
    dot_product = sum(vec_a[w] * vec_b[w] for w in common)

    # Magnitudes
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot_product / (mag_a * mag_b)


def does_skill_match(skill, resume_text):
    """
    Checks whether a skill appears in the resume text.
    Uses strict whole-word matching only — no loose character overlap.

    Method 1: Whole-word regex search using word boundaries.
              e.g. "Python" will NOT match "Pythonista".
    Method 2: N-gram window match for multi-word skills
              e.g. "Machine Learning" is checked as a two-word phrase.

    The old character-overlap method was removed because it caused false
    positives — single characters like 'a', 's', 'e' exist in almost
    every resume, making every skill appear to match.
    """
    skill_lower = skill.lower()
    text_lower  = resume_text.lower()

    # Method 1 — whole-word boundary regex
    pattern = r"\b" + re.escape(skill_lower) + r"\b"
    if re.search(pattern, text_lower):
        return True

    # Method 2 — exact n-gram window match
    skill_words  = skill_lower.split()
    resume_words = text_lower.split()
    n = len(skill_words)
    for i in range(len(resume_words) - n + 1):
        window = " ".join(resume_words[i:i + n])
        if window == skill_lower:
            return True

    return False


def classify_experience_level(text):
    """
    Guesses the candidate's experience level based on keywords in the resume.
    Scores are accumulated:
      - Senior keywords score 3 points each
      - Mid-level keywords score 2 points each
      - Junior keywords score 1 point each
      - Year mentions also contribute to the score
    """
    lower = text.lower()
    scores = {"senior": 0, "mid": 0, "junior": 0}

    senior_keywords = ["senior", "lead", "principal", "architect",
                       "director", "head", "vp", "chief", "staff", "expert"]
    mid_keywords    = ["engineer", "developer", "analyst", "specialist", "manager"]
    junior_keywords = ["junior", "intern", "fresher", "trainee",
                       "entry", "graduate", "student"]

    for kw in senior_keywords:
        if kw in lower:
            scores["senior"] += 3

    for kw in mid_keywords:
        if kw in lower:
            scores["mid"] += 2

    for kw in junior_keywords:
        if kw in lower:
            scores["junior"] += 1

    # Check for year mentions like "5 years", "3+ years"
    year_matches = re.findall(r"(\d+)\s*\+?\s*years?", lower)
    for year_str in year_matches:
        years = int(year_str)
        if years >= 6:
            scores["senior"] += 2
        elif years >= 3:
            scores["mid"] += 2
        else:
            scores["junior"] += 2

    # Return the category with the highest score
    top_category = max(scores, key=scores.get)

    if scores[top_category] == 0:
        return "Mid-Level"

    label_map = {"senior": "Senior", "mid": "Mid-Level", "junior": "Junior"}
    return label_map[top_category]


def extract_tech_keywords(text):
    """
    Finds common technology keywords in the resume text.
    Used to give a small bonus to the overall score.
    """
    tech_pattern = (
        r"\b(python|java|javascript|typescript|react|angular|vue|node|express|"
        r"django|flask|spring|sql|mongodb|postgresql|redis|docker|kubernetes|"
        r"aws|azure|gcp|git|linux|bash|html|css|graphql|tensorflow|pytorch|"
        r"keras|scikit|pandas|numpy|matplotlib|spark|hadoop|kafka|airflow|"
        r"tableau|scala|swift|kotlin|flutter|firebase|selenium|jest|postman|"
        r"nlp|bert|gpt|machine learning|deep learning|devops|terraform|"
        r"figma|jira|agile)\b"
    )
    found = re.findall(tech_pattern, text.lower())
    return list(set(found))


# =============================================================================
#  MAIN ML ANALYSIS FUNCTION
# =============================================================================

def analyse_resume(resume_text, domain):
    """
    The main ML analysis pipeline.

    Steps:
      1. Expand synonyms in the resume text
      2. Tokenize the resume
      3. For each skill in the target domain:
           a. Check for fuzzy/substring match
           b. Compute Jaccard similarity
           c. Compute TF-IDF cosine similarity
           d. Combine into an ensemble score
      4. Classify experience level
      5. Compute the final score
      6. Generate a summary and improvement suggestions
    """

    required_skills = DOMAIN_SKILLS.get(domain, [])
    expanded_text   = expand_with_synonyms(resume_text or "")
    resume_tokens   = tokenize_text(expanded_text)

    # Pre-compute IDF weights for the manual fallback
    all_docs = [resume_tokens]
    for skill in required_skills:
        all_docs.append(tokenize_text(skill))

    idf_weights = {}
    num_docs = len(all_docs)
    all_terms = set(token for doc in all_docs for token in doc)
    for term in all_terms:
        doc_freq = sum(1 for doc in all_docs if term in doc)
        idf_weights[term] = math.log((num_docs + 1) / (doc_freq + 1)) + 1

    # Analyse each skill
    matched_skills  = []
    missing_skills  = []
    skill_details   = []

    for skill in required_skills:
        skill_tokens = tokenize_text(skill)

        # (a) Fuzzy/substring match
        is_fuzzy_match = does_skill_match(skill, expanded_text)

        # (b) Jaccard similarity
        jaccard_score = jaccard_similarity(
            set(skill_tokens),
            set(resume_tokens)
        )

        # (c) TF-IDF cosine similarity
        if SKLEARN_AVAILABLE:
            cosine_score = tfidf_cosine_similarity(
                expanded_text[:2000], skill
            )
        else:
            cosine_score = manual_cosine_similarity(
                resume_tokens, skill_tokens, idf_weights
            )

        # (d) Ensemble score — weighted combination
        #     Fuzzy match carries the most weight (50%)
        #     because it directly checks if the word is present
        ensemble_score = (
            0.50 * int(is_fuzzy_match) +
            0.25 * jaccard_score +
            0.25 * cosine_score
        )

        # A skill is "matched" only if:
        #   - the fuzzy (word-boundary) match found the skill  AND
        #   - the ensemble score is at least 0.25
        # This prevents false positives where the skill word happens to
        # appear in an unrelated context.
        is_matched = bool(is_fuzzy_match and ensemble_score >= 0.25)

        if is_matched:
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)

        skill_details.append({
            "skill":    skill,
            "matched":  is_matched,
            "fuzzy":    round(int(is_fuzzy_match) * 100, 1),
            "jaccard":  round(jaccard_score * 100, 1),
            "cosine":   round(cosine_score * 100, 1),
            "ensemble": round(ensemble_score * 100, 1)
        })

    # Compute final score
    if required_skills:
        base_score = round((len(matched_skills) / len(required_skills)) * 100)
    else:
        base_score = 0

    # Extract general tech keywords found anywhere in the resume
    found_keywords = extract_tech_keywords(resume_text or "")

    # Apply a small penalty if the resume text is very short (likely empty or corrupt)
    word_count = len((resume_text or "").split())
    if word_count < 30:
        base_score = max(5, base_score - 20)

    # No bonus — the score should purely reflect skill coverage
    # Clamp to [5, 95] so scores feel realistic
    final_score = min(95, max(5, base_score))

    # Classify experience level
    experience_level = classify_experience_level(resume_text or "")

    # Generate a readable summary
    top_skills   = ", ".join(matched_skills[:4]) or "general technical skills"
    skill_gaps   = " and ".join(missing_skills[:2]) or "advanced tooling"

    if final_score >= 70:
        summary = (
            f"Strong {domain} profile with solid expertise in {top_skills}. "
            f"Your resume is well-aligned with industry expectations and "
            f"you are ready to apply for competitive roles."
        )
    elif final_score >= 45:
        summary = (
            f"Developing {domain} candidate with a good foundation in {top_skills}. "
            f"Filling the gaps in {skill_gaps} will make your profile "
            f"significantly more competitive in the job market."
        )
    else:
        summary = (
            f"Early-stage {domain} candidate with exposure to {top_skills}. "
            f"Building practical projects around {skill_gaps} "
            f"and gaining hands-on experience is the best next step."
        )

    # Generate actionable improvement suggestions
    suggestions = []

    if missing_skills:
        top_missing = ", ".join(missing_skills[:3])
        suggestions.append(
            f"Add {top_missing} to your skills section — "
            f"these are high-demand keywords for {domain} roles."
        )

    if final_score < 50:
        suggestions.append(
            "Your score is below 50%. Build 2-3 domain-specific projects "
            "and list them on GitHub with clear descriptions."
        )
    elif final_score < 70:
        suggestions.append(
            "Consider earning a relevant certification (e.g. AWS, Google, Coursera) "
            "and add measurable achievements to each role."
        )
    else:
        suggestions.append(
            "Great score! Contribute to open-source projects and write "
            "technical articles to stand out further."
        )

    suggestions.append(
        "Mirror the exact keywords from job descriptions — ATS systems "
        "rank candidates based on keyword match percentage."
    )

    if experience_level == "Junior":
        suggestions.append(
            "Include GitHub links, academic projects, and any internship "
            "experience to demonstrate hands-on work."
        )

    return {
        "domain":           domain,
        "resume_score":     final_score,
        "experience_level": experience_level,
        "summary":          summary,
        "matched_skills":   matched_skills,
        "missing_skills":   missing_skills,
        "extracted_skills": found_keywords[:20],
        "suggestions":      suggestions[:4],
        "skill_details":    skill_details
    }


# =============================================================================
#  DATABASE SETUP  (SQLite — built into Python, no extra install needed)
# =============================================================================

DATABASE = "resumeml.db"


def get_db():
    """Opens a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row   # lets us access columns by name
    return conn


def init_db():
    """
    Creates the database tables if they do not already exist.
    Called once when the server starts.

    Tables:
      users   — stores registered user accounts
      resumes — stores every resume uploaded by each user
    """
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    NOT NULL UNIQUE,
            email      TEXT    NOT NULL UNIQUE,
            password   TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)

    # Resumes table — each row is one uploaded resume analysis
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            filename       TEXT    NOT NULL,
            domain         TEXT    NOT NULL,
            score          INTEGER NOT NULL,
            experience     TEXT    NOT NULL,
            matched_skills TEXT    NOT NULL,
            missing_skills TEXT    NOT NULL,
            summary        TEXT    NOT NULL,
            resume_text    TEXT    NOT NULL,
            uploaded_at    TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password):
    """Hashes a password using SHA-256 for safe storage."""
    return hashlib.sha256(password.encode()).hexdigest()


# =============================================================================
#  FLASK APPLICATION
# =============================================================================

app = Flask(__name__, static_folder="static", template_folder=".")
app.secret_key = "resumeml_secret_key_2024"   # used to sign session cookies


# --- Login required decorator ------------------------------------------------

def login_required(f):
    """
    Decorator that redirects to the login page if the user is not logged in.
    Use @login_required on any route that needs authentication.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


# =============================================================================
#  PAGE ROUTES  (serve HTML files)
# =============================================================================

@app.route("/")
def home():
    """Redirect root to login if not logged in, else serve the main app."""
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(".", "index.html")


@app.route("/login")
def login_page():
    """Serve the login page."""
    if "user_id" in session:
        return redirect("/")
    return send_from_directory(".", "login.html")


@app.route("/register")
def register_page():
    """Serve the register page."""
    if "user_id" in session:
        return redirect("/")
    return send_from_directory(".", "register.html")


@app.route("/history")
@login_required
def history_page():
    """Serve the resume history page."""
    return send_from_directory(".", "history.html")


# =============================================================================
#  AUTH API ROUTES
# =============================================================================

@app.route("/api/register", methods=["POST"])
def api_register():
    """
    Registers a new user account.
    Expects JSON: { username, email, password }
    """
    data     = request.get_json()
    username = (data.get("username") or "").strip()
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()

    # Basic validation
    if not username or not email or not password:
        return jsonify({"error": "All fields are required."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if "@" not in email:
        return jsonify({"error": "Please enter a valid email address."}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
            (username, email, hash_password(password), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return jsonify({"message": "Account created successfully!"}), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists."}), 409

    finally:
        conn.close()


@app.route("/api/login", methods=["POST"])
def api_login():
    """
    Logs in an existing user.
    Expects JSON: { email, password }
    Sets a server-side session on success.
    """
    data     = request.get_json()
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (email, hash_password(password))
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Incorrect email or password."}), 401

    # Store user info in the session
    session["user_id"]  = user["id"]
    session["username"] = user["username"]
    session["email"]    = user["email"]

    return jsonify({"message": "Login successful!", "username": user["username"]}), 200


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Clears the session and logs the user out."""
    session.clear()
    return jsonify({"message": "Logged out."}), 200


@app.route("/api/me")
def api_me():
    """Returns the currently logged-in user's info."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in."}), 401
    return jsonify({
        "user_id":  session["user_id"],
        "username": session["username"],
        "email":    session["email"]
    })


# =============================================================================
#  RESUME HISTORY API
# =============================================================================

@app.route("/api/history")
@login_required
def api_history():
    """Returns all resumes uploaded by the logged-in user."""
    conn    = get_db()
    resumes = conn.execute(
        "SELECT id, filename, domain, score, experience, matched_skills, "
        "missing_skills, summary, uploaded_at FROM resumes "
        "WHERE user_id = ? ORDER BY uploaded_at DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    result = []
    for r in resumes:
        result.append({
            "id":             r["id"],
            "filename":       r["filename"],
            "domain":         r["domain"],
            "score":          r["score"],
            "experience":     r["experience"],
            "matched_skills": json.loads(r["matched_skills"]),
            "missing_skills": json.loads(r["missing_skills"]),
            "summary":        r["summary"],
            "uploaded_at":    r["uploaded_at"]
        })

    return jsonify(result)


@app.route("/api/history/<int:resume_id>", methods=["DELETE"])
@login_required
def api_delete_resume(resume_id):
    """Deletes a specific resume from the logged-in user's history."""
    conn = get_db()
    conn.execute(
        "DELETE FROM resumes WHERE id = ? AND user_id = ?",
        (resume_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted successfully."}), 200


# =============================================================================
#  MAIN API ROUTES
# =============================================================================

@app.route("/health")
def health_check():
    """Returns the server status and which ML libraries are available."""
    return jsonify({
        "status":        "running",
        "sklearn":       SKLEARN_AVAILABLE,
        "pdf_support":   PDF_AVAILABLE,
        "docx_support":  DOCX_AVAILABLE,
        "domains":       list(DOMAIN_SKILLS.keys())
    })


@app.route("/domains")
def get_domains():
    """Returns all available domains and their skill lists."""
    return jsonify(DOMAIN_SKILLS)


@app.route("/companies")
def get_companies():
    """Returns all company data so the frontend can use it."""
    return jsonify(COMPANIES)


@app.route("/analyze", methods=["POST"])
@login_required
def analyze_resume():
    """
    Main analysis endpoint.
    Requires login. Saves the result to the database after analysis.
    Expects a multipart form with:
      - file: the resume file (PDF, DOCX, or TXT)
      - domain: the target job domain string
    """

    if "file" not in request.files:
        return jsonify({"error": "No file was uploaded."}), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({"error": "The uploaded file has no name."}), 400

    filename  = uploaded_file.filename
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ("pdf", "docx", "txt"):
        return jsonify({"error": "Only PDF, DOCX, or TXT files are accepted."}), 400

    domain = request.form.get("domain", "Data Science")

    if domain not in DOMAIN_SKILLS:
        return jsonify({"error": f"Unknown domain: {domain}"}), 400

    file_bytes = uploaded_file.read()

    if len(file_bytes) > 5 * 1024 * 1024:
        return jsonify({"error": "File is too large. Maximum allowed size is 5 MB."}), 413

    try:
        resume_text = extract_text_from_file(file_bytes, filename)
        result      = analyse_resume(resume_text, domain)

        result["filename"]  = filename
        result["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save the resume and its analysis result to the database
        conn = get_db()
        conn.execute(
            """INSERT INTO resumes
               (user_id, filename, domain, score, experience,
                matched_skills, missing_skills, summary, resume_text, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session["user_id"],
                filename,
                domain,
                result["resume_score"],
                result["experience_level"],
                json.dumps(result["matched_skills"]),
                json.dumps(result["missing_skills"]),
                result["summary"],
                resume_text[:5000],   # store first 5000 chars to save space
                result["timestamp"]
            )
        )
        conn.commit()
        conn.close()

        return jsonify(result)

    except Exception as error:
        return jsonify({"error": str(error)}), 500


# =============================================================================
#  START THE SERVER
# =============================================================================

if __name__ == "__main__":
    init_db()   # create tables if they don't exist yet
    print("")
    print("=" * 55)
    print("  ML-Based Resume Analyzer & Job Recommendation System")
    print("=" * 55)
    print(f"  scikit-learn : {'Available' if SKLEARN_AVAILABLE else 'Not installed'}")
    print(f"  PDF support  : {'Available' if PDF_AVAILABLE   else 'Not installed'}")
    print(f"  DOCX support : {'Available' if DOCX_AVAILABLE  else 'Not installed'}")
    print(f"  Database     : {DATABASE}")
    print("=" * 55)
    print("  Open in browser: http://127.0.0.1:5000")
    print("=" * 55)
    print("")
    app.run(debug=True, host="0.0.0.0", port=5000)
