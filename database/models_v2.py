# models_v2.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

def datetime_now_seconds():
    """Return current datetime truncated to seconds (no microseconds)"""
    return datetime.now().replace(microsecond=0)

class ExamV2(Base):
    __tablename__ = "v2_exams"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)  # Keep original name column for compatibility
    topic = Column(String(100), nullable=False) 
    grade_level = Column(String(16), nullable=False)
    # Store original exam image paths as JSON array if multiple pages
    original_image_paths = Column(String, nullable=True)   
    created_at = Column(DateTime, default=datetime_now_seconds)

    questions = relationship("QuestionV2", back_populates="exam", cascade="all, delete-orphan")
    submissions = relationship("SubmissionV2", back_populates="exam", cascade="all, delete-orphan")
    
    @property
    def title(self):
        """Compatibility property for title access"""
        return self.name

class QuestionV2(Base):
    __tablename__ = "v2_questions"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("v2_exams.id"), nullable=False)
    
    # Store single image path (for backward compatibility) or multiple images as JSON
    question_image_path = Column(String(512), nullable=False)   
    question_image_paths = Column(String, nullable=True)  # JSON array for multiple images
    has_multiple_images = Column(Boolean, default=False)  # Flag to indicate if question has multiple images
    
    order_index = Column(Integer, nullable=False)     # Major question number (e.g. 1, 2, 3)
    part_label = Column(String(32))                   # Sub-question label (e.g. "a", "b", "1.a")

    exam = relationship("ExamV2", back_populates="questions")
    submission_items = relationship("SubmissionItemV2", back_populates="question", cascade="all, delete-orphan")

class SubmissionV2(Base):
    __tablename__ = "v2_submissions"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("v2_exams.id"), nullable=False)
    student_name = Column(String(255), nullable=False)
    original_image_paths = Column(String, nullable=True)   
    created_at = Column(DateTime, default=datetime_now_seconds)

    exam = relationship("ExamV2", back_populates="submissions")
    items = relationship("SubmissionItemV2", back_populates="submission", cascade="all, delete-orphan")

class SubmissionItemV2(Base):
    __tablename__ = "v2_submission_items"
    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("v2_submissions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("v2_questions.id"), nullable=False)
    
    # Store single image path (for backward compatibility) or multiple images as JSON
    answer_image_path = Column(String(512), nullable=False)   
    answer_image_paths = Column(String, nullable=True)  # JSON array for multiple images
    has_multiple_images = Column(Boolean, default=False)  # Flag to indicate if answer has multiple images
    
    # Relationship to grading result
    grading = relationship("GradingV2", back_populates="submission_item", uselist=False, cascade="all, delete-orphan")
    submission = relationship("SubmissionV2", back_populates="items")
    question = relationship("QuestionV2", back_populates="submission_items")
    
class GradingV2(Base):
    __tablename__ = "v2_gradings"
    id = Column(Integer, primary_key=True)
    submission_item_id = Column(Integer, ForeignKey("v2_submission_items.id"), nullable=False, unique=True)
    question_id = Column(Integer, ForeignKey("v2_questions.id"), nullable=False)  # For easier queries
    
    # Core grading result
    is_correct = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=True)  # AI confidence score (0.0-1.0)
    
    # AI analysis
    error_description = Column(String, nullable=True)   # Concise error analysis from AI
    error_phrases = Column(String, nullable=True)       # JSON array of specific error phrases
    partial_credit = Column(Boolean, default=False)     # Whether partial credit given
    
    # Allow teacher to add notes or override
    teacher_notes = Column(String, nullable=True)   
    
    graded_at = Column(DateTime, default=datetime_now_seconds)

    submission_item = relationship("SubmissionItemV2", back_populates="grading")