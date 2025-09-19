# database/models_v2.py
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
    name = Column(String(255), nullable=False)
    topic = Column(String(100), nullable=False) 
    grade_level = Column(String(16), nullable=False)
    original_image_paths = Column(String, nullable=True)   
    created_at = Column(DateTime, default=datetime_now_seconds)

    questions = relationship("QuestionV2", back_populates="exam", cascade="all, delete-orphan")
    submissions = relationship("SubmissionV2", back_populates="exam", cascade="all, delete-orphan")
    
    @property
    def title(self):
        return self.name

class QuestionV2(Base):
    __tablename__ = "v2_questions"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("v2_exams.id"), nullable=False)
    
    question_image_path = Column(String(512), nullable=False)   
    question_image_paths = Column(String, nullable=True)
    has_multiple_images = Column(Boolean, default=False)
    
    order_index = Column(Integer, nullable=False)
    part_label = Column(String(32))

    exam = relationship("ExamV2", back_populates="questions")
    submission_items = relationship("SubmissionItemV2", back_populates="question", cascade="all, delete-orphan")
    gradings = relationship("GradingV2", back_populates="question", cascade="all, delete-orphan")

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
    
    # --- CỘT MỚI ĐƯỢC THÊM VÀO ---
    # Can store either single integer (backward compatibility) or JSON array for multi-page answers
    source_page_index = Column(String, nullable=False, default='0')

    answer_image_path = Column(String(512), nullable=False)   
    answer_image_paths = Column(String, nullable=True)
    has_multiple_images = Column(Boolean, default=False)
    
    grading = relationship("GradingV2", back_populates="submission_item", uselist=False, cascade="all, delete-orphan")
    submission = relationship("SubmissionV2", back_populates="items")
    question = relationship("QuestionV2", back_populates="submission_items")
    
class GradingV2(Base):
    __tablename__ = "v2_gradings"
    id = Column(Integer, primary_key=True)
    submission_item_id = Column(Integer, ForeignKey("v2_submission_items.id"), nullable=False, unique=True)
    question_id = Column(Integer, ForeignKey("v2_questions.id"), nullable=False)

    is_correct = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=True)

    error_description = Column(String, nullable=True)
    error_phrases = Column(String, nullable=True)
    partial_credit = Column(Boolean, default=False)

    teacher_notes = Column(String, nullable=True)
    clarify_notes = Column(String, nullable=True)  # Teacher clarification for re-grading

    graded_at = Column(DateTime, default=datetime_now_seconds)

    submission_item = relationship("SubmissionItemV2", back_populates="grading")
    question = relationship("QuestionV2", back_populates="gradings")