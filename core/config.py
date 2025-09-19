import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==================== APP CONFIGURATION ====================
APP_TITLE = "Trợ lý Chấm bài"
APP_ICON = "📚"
LAYOUT = "wide"

# ==================== MODEL CONFIGURATION ====================
# Vision grading model - using GPT-5 Mini for image pairs (no temperature needed)
VISION_GRADING_MODEL = "gpt-5-mini"

# ==================== API CONFIGURATION ====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ==================== DATABASE CONFIGURATION ====================
# SQLite local file path from environment or default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/teacher_assistant_v2.db")

# ==================== FILE STORAGE CONFIGURATION ====================
# Local storage paths
STATIC_DIR = "static"
IMAGES_DIR = os.path.join(STATIC_DIR, "images")
EXAMS_DIR = os.path.join(IMAGES_DIR, "exams")
QUESTIONS_DIR = os.path.join(IMAGES_DIR, "questions")
ANSWERS_DIR = os.path.join(IMAGES_DIR, "answers")
SUBMISSIONS_DIR = os.path.join(IMAGES_DIR, "submissions")

# Create directories if they don't exist
for directory in ["data", STATIC_DIR, IMAGES_DIR, EXAMS_DIR, QUESTIONS_DIR, ANSWERS_DIR, SUBMISSIONS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ==================== IMAGE SETTINGS ====================
# Supported image formats
SUPPORTED_IMAGE_FORMATS = ["png", "jpg", "jpeg"]
MAX_IMAGE_SIZE_MB = 50

# ==================== CROPPING SETTINGS ====================
CROP_BOX_COLOR = "#0066CC"  # Blue color for crop box
CROP_REALTIME_UPDATE = True