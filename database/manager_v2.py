import os
import json
from typing import List, Optional, Dict, Any, Union
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, joinedload
from contextlib import contextmanager
from datetime import datetime

from .models_v2 import Base, ExamV2, QuestionV2, SubmissionV2, SubmissionItemV2, GradingV2

class DatabaseManagerV2:
    def __init__(self, database_url: str = None):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables and handle migrations"""
        Base.metadata.create_all(bind=self.engine)
        
        # Handle grading table migration for new fields
        try:
            with self.get_session() as session:
                # Check if new columns exist, add them if not
                result = session.execute(text("PRAGMA table_info(v2_gradings)"))
                columns = [row[1] for row in result.fetchall()]
                
                missing_columns = []
                expected_columns = {
                    'question_id': 'INTEGER',
                    'confidence': 'FLOAT',
                    'partial_credit': 'BOOLEAN DEFAULT 0',
                    'clarify_notes': 'TEXT'
                }
                
                # Check for topic column in exams table
                result_exams = session.execute(text("PRAGMA table_info(v2_exams)"))
                exam_columns = [row[1] for row in result_exams.fetchall()]
                
                if 'topic' not in exam_columns:
                    session.execute(text("ALTER TABLE v2_exams ADD COLUMN topic VARCHAR(100"))
                    session.commit()
                
                # Handle migration from subject to topic (if subject column exists)
                if 'subject' in exam_columns and 'topic' not in exam_columns:
                    session.execute(text("ALTER TABLE v2_exams RENAME COLUMN subject TO topic"))
                    session.commit()
                
                # Check for multiple images columns in questions table
                result_questions = session.execute(text("PRAGMA table_info(v2_questions)"))
                question_columns = [row[1] for row in result_questions.fetchall()]
                
                if 'question_image_paths' not in question_columns:
                    session.execute(text("ALTER TABLE v2_questions ADD COLUMN question_image_paths TEXT"))
                    session.commit()
                
                if 'has_multiple_images' not in question_columns:
                    session.execute(text("ALTER TABLE v2_questions ADD COLUMN has_multiple_images BOOLEAN DEFAULT 0"))
                    session.commit()
                
                # Check for multiple images columns in submission_items table
                result_submission_items = session.execute(text("PRAGMA table_info(v2_submission_items)"))
                submission_item_columns = [row[1] for row in result_submission_items.fetchall()]
                
                if 'answer_image_paths' not in submission_item_columns:
                    session.execute(text("ALTER TABLE v2_submission_items ADD COLUMN answer_image_paths TEXT"))
                    session.commit()
                
                if 'has_multiple_images' not in submission_item_columns:
                    session.execute(text("ALTER TABLE v2_submission_items ADD COLUMN has_multiple_images BOOLEAN DEFAULT 0"))
                    session.commit()
                
                # Migrate source_page_index from INTEGER to TEXT (JSON array support)
                # Check current data type of source_page_index column
                result_source_page_type = session.execute(text(
                    "SELECT type FROM pragma_table_info('v2_submission_items') WHERE name = 'source_page_index'"
                ))
                source_page_type_row = result_source_page_type.fetchone()
                
                if source_page_type_row and source_page_type_row[0] == 'INTEGER':
                    # Migrate existing integer values to string format
                    session.execute(text(
                        "UPDATE v2_submission_items SET source_page_index = CAST(source_page_index AS TEXT)"
                    ))
                    session.commit()
                
                for col_name, col_type in expected_columns.items():
                    if col_name not in columns:
                        missing_columns.append(f"ALTER TABLE v2_gradings ADD COLUMN {col_name} {col_type}")
                
                # Execute missing column additions
                for alter_statement in missing_columns:
                    session.execute(text(alter_statement))
                    session.commit()
                    
        except Exception as e:
            print(f"Warning: Database migration failed: {e}")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # Helper methods for source_page_index handling
    @staticmethod
    def encode_source_page_indices(indices: Union[int, List[int]]) -> str:
        """Convert source page index(es) to string format for storage"""
        if isinstance(indices, int):
            return str(indices)
        elif isinstance(indices, list):
            return json.dumps(indices)
        else:
            return '0'  # fallback
    
    @staticmethod
    def decode_source_page_indices(indices_str: str) -> List[int]:
        """Convert stored string format back to list of integers"""
        try:
            # Try parsing as JSON array first
            if indices_str.startswith('['):
                return json.loads(indices_str)
            else:
                # Single integer stored as string
                return [int(indices_str)]
        except (json.JSONDecodeError, ValueError):
            return [0]  # fallback
    
    # ============ EXAM OPERATIONS ============
    
    def create_exam(self, title: str, topic: str, grade_level: str, original_image_paths: List[str] = None) -> int:
        """Create a new exam and return its ID"""
        with self.get_session() as session:
            exam = ExamV2(
                name=title,  # Map title parameter to name column
                topic=topic,
                grade_level=grade_level,
                original_image_paths=json.dumps(original_image_paths or [])
            )
            session.add(exam)
            session.commit()
            return exam.id
    
    def get_exam_by_id(self, exam_id: int) -> Optional[ExamV2]:
        """Get exam by ID with its questions eagerly loaded."""
        with self.get_session() as session:
            # SỬ DỤNG EAGER LOADING ĐỂ TẢI LUÔN CÁC CÂU HỎI
            return (
                session.query(ExamV2)
                .options(joinedload(ExamV2.questions)) # Tải các câu hỏi liên quan
                .filter(ExamV2.id == exam_id)
                .first()
            )
    
    def list_exams(self) -> List[Dict[str, Any]]:
        """List all exams with basic info"""
        with self.get_session() as session:
            exams = session.query(ExamV2).order_by(ExamV2.id.desc()).all()
            return [
                {
                    "id": exam.id,
                    "name": exam.name,
                    "topic": getattr(exam, 'topic'), 
                    "grade_level": exam.grade_level,
                    "created_at": exam.created_at,
                    "question_count": len(exam.questions)
                }
                for exam in exams
            ]
    
    # ============ QUESTION OPERATIONS ============
    
    def create_question(self, exam_id: int, question_image_path: str, order_index: int, 
                       part_label: str = "", question_image_paths: List[str] = None,
                       has_multiple_images: bool = False) -> int:
        """Create a new question and return its ID"""
        with self.get_session() as session:
            question = QuestionV2(
                exam_id=exam_id,
                question_image_path=question_image_path,
                question_image_paths=json.dumps(question_image_paths or []),
                has_multiple_images=has_multiple_images,
                order_index=order_index,
                part_label=part_label
            )
            session.add(question)
            session.commit()
            return question.id
    
    def update_question_images(self, question_id: int, new_image_paths: List[str]) -> bool:
        """Update question with additional images"""
        with self.get_session() as session:
            question = session.query(QuestionV2).filter(QuestionV2.id == question_id).first()
            if not question:
                return False
            
            existing_paths = json.loads(question.question_image_paths or '[]')
            all_paths = existing_paths + new_image_paths
            
            question.question_image_paths = json.dumps(all_paths)
            question.has_multiple_images = len(all_paths) > 1
            
            session.commit()
            return True
    
    def get_questions_by_exam(self, exam_id: int) -> List[QuestionV2]:
        """Get all questions for an exam, ordered by order_index and part_label"""
        with self.get_session() as session:
            return (session.query(QuestionV2)
                   .filter(QuestionV2.exam_id == exam_id)
                   .order_by(QuestionV2.order_index, QuestionV2.part_label)
                   .all())
    
    def find_question_by_label(self, exam_id: int, order_index: int, part_label: str) -> Optional[QuestionV2]:
        """Find existing question by exam_id, order_index and part_label"""
        with self.get_session() as session:
            return (session.query(QuestionV2)
                   .filter(QuestionV2.exam_id == exam_id)
                   .filter(QuestionV2.order_index == order_index)
                   .filter(QuestionV2.part_label == part_label)
                   .first())
    
    def get_question_by_id(self, question_id: int) -> Optional[QuestionV2]:
        """Get question by ID"""
        with self.get_session() as session:
            return session.query(QuestionV2).filter(QuestionV2.id == question_id).first()
    
    def get_related_question_parts(self, exam_id: int, order_index: int, base_part_label: str) -> List[QuestionV2]:
        """Get all parts of a multi-part question"""
        with self.get_session() as session:
            # Find questions with similar part labels (for multi-part questions)
            questions = (session.query(QuestionV2)
                        .filter(QuestionV2.exam_id == exam_id)
                        .filter(QuestionV2.order_index == order_index)
                        .filter(QuestionV2.part_label.like(f"{base_part_label}%"))
                        .order_by(QuestionV2.part_label)
                        .all())
            return questions
    
    def delete_question(self, question_id: int) -> bool:
        """Delete a question and return success status"""
        with self.get_session() as session:
            question = session.query(QuestionV2).filter(QuestionV2.id == question_id).first()
            if not question:
                return False
            
            # Store image paths for cleanup
            image_paths_to_delete = []
            
            # Main question image
            if question.question_image_path:
                image_paths_to_delete.append(question.question_image_path)
            
            # Additional images for multi-image questions
            if hasattr(question, 'has_multiple_images') and question.has_multiple_images:
                try:
                    additional_paths = json.loads(question.question_image_paths or '[]')
                    image_paths_to_delete.extend(additional_paths)
                except:
                    pass
            
            # Get related submission items before deletion to clean up answer images
            submission_items = session.query(SubmissionItemV2).filter(SubmissionItemV2.question_id == question_id).all()
            answer_paths_to_delete = []
            
            for item in submission_items:
                # Main answer image
                if item.answer_image_path:
                    answer_paths_to_delete.append(item.answer_image_path)
                
                # Additional answer images for multi-image answers
                if hasattr(item, 'has_multiple_images') and item.has_multiple_images:
                    try:
                        additional_answer_paths = json.loads(item.answer_image_paths or '[]')
                        answer_paths_to_delete.extend(additional_answer_paths)
                    except:
                        pass
            
            # Delete the question (cascade will handle related submission_items and gradings)
            session.delete(question)
            session.commit()
            
            # Clean up image files
            import os
            all_paths_to_delete = image_paths_to_delete + answer_paths_to_delete
            
            for file_path in all_paths_to_delete:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Warning: Failed to delete image {file_path}: {e}")
            
            return True
    
    # ============ SUBMISSION OPERATIONS ============
    
    def create_submission(self, exam_id: int, student_name: str, 
                         original_image_paths: List[str] = None) -> int:
        """Create a new submission and return its ID"""
        with self.get_session() as session:
            submission = SubmissionV2(
                exam_id=exam_id,
                student_name=student_name,
                original_image_paths=json.dumps(original_image_paths or [])
            )
            session.add(submission)
            session.commit()
            return submission.id
    
    def get_submission_by_id(self, submission_id: int) -> Optional[SubmissionV2]:
        """
        Get submission by ID with ALL related data eagerly loaded using explicit joins
        to prevent any DetachedInstanceError. This is the definitive method.
        """
        with self.get_session() as session:
            return (
                session.query(SubmissionV2)
                .filter(SubmissionV2.id == submission_id)
                .options(
                    # Tải lồng nhau sâu nhất: Submission -> Exam -> Questions của Exam đó
                    joinedload(SubmissionV2.exam).joinedload(ExamV2.questions),
                    
                    # Tải lồng nhau sâu nhất: Submission -> Items -> Question và Grading của Item đó
                    joinedload(SubmissionV2.items)
                    .joinedload(SubmissionItemV2.question),

                    joinedload(SubmissionV2.items)
                    .joinedload(SubmissionItemV2.grading)
                )
                .first()
            )
    
    def list_submissions_by_exam(self, exam_id: int) -> List[Dict[str, Any]]:
        """List all submissions for an exam"""
        with self.get_session() as session:
            submissions = (session.query(SubmissionV2)
                          .filter(SubmissionV2.exam_id == exam_id)
                          .order_by(SubmissionV2.id.desc())
                          .all())
            return [
                {
                    "id": sub.id,
                    "student_name": sub.student_name,
                    "created_at": sub.created_at,
                    "item_count": len(sub.items)
                }
                for sub in submissions
            ]
    
    def get_all_submissions(self) -> List[SubmissionV2]:
        """Get all submissions"""
        with self.get_session() as session:
            return (
                session.query(SubmissionV2)
                .options(
                    joinedload(SubmissionV2.exam),
                    joinedload(SubmissionV2.items).joinedload(SubmissionItemV2.question)
                )
                .order_by(SubmissionV2.id.desc())
                .all()
            )
    
    # ============ SUBMISSION ITEM OPERATIONS ============
    
    def create_submission_item(self, submission_id: int, question_id: int, 
                              answer_image_path: str, source_page_indices: Union[int, List[int]], # --- UPDATED ---
                              answer_image_paths: List[str] = None,
                              has_multiple_images: bool = False) -> int:
        """Create a new submission item and return its ID"""
        with self.get_session() as session:
            existing_item = (session.query(SubmissionItemV2)
                           .filter(SubmissionItemV2.submission_id == submission_id)
                           .filter(SubmissionItemV2.question_id == question_id)
                           .first())
            
            if existing_item:
                existing_item.answer_image_path = answer_image_path
                existing_item.answer_image_paths = json.dumps(answer_image_paths or [])
                existing_item.has_multiple_images = has_multiple_images
                existing_item.source_page_index = self.encode_source_page_indices(source_page_indices)
                session.commit()
                return existing_item.id
            else:
                item = SubmissionItemV2(
                    submission_id=submission_id,
                    question_id=question_id,
                    source_page_index=self.encode_source_page_indices(source_page_indices), # --- UPDATED ---
                    answer_image_path=answer_image_path,
                    answer_image_paths=json.dumps(answer_image_paths or []),
                    has_multiple_images=has_multiple_images
                )
                session.add(item)
                session.commit()
                return item.id
    
    def update_submission_item_images(self, submission_id: int, question_id: int, new_image_paths: List[str]) -> bool:
        """Add new images to existing submission item"""
        with self.get_session() as session:
            item = (session.query(SubmissionItemV2)
                   .filter(SubmissionItemV2.submission_id == submission_id)
                   .filter(SubmissionItemV2.question_id == question_id)
                   .first())
            
            if not item:
                return False
            
            existing_paths = json.loads(item.answer_image_paths or '[]')
            all_paths = existing_paths + new_image_paths
            
            item.answer_image_paths = json.dumps(all_paths)
            item.has_multiple_images = len(all_paths) > 1
            
            session.commit()
            return True
    
    def find_submission_item(self, submission_id: int, question_id: int) -> Optional[SubmissionItemV2]:
        """Find existing submission item by submission_id and question_id"""
        with self.get_session() as session:
            return (session.query(SubmissionItemV2)
                   .filter(SubmissionItemV2.submission_id == submission_id)
                   .filter(SubmissionItemV2.question_id == question_id)
                   .first())
    
    def get_submission_items(self, submission_id: int) -> List[SubmissionItemV2]:
        """Get all submission items for a submission with grading and question relationships"""
        with self.get_session() as session:
            return (session.query(SubmissionItemV2)
                   .options(joinedload(SubmissionItemV2.grading))
                   .options(joinedload(SubmissionItemV2.question))
                   .filter(SubmissionItemV2.submission_id == submission_id)
                   .all())
    
    def get_submission_item_by_id(self, item_id: int) -> Optional[SubmissionItemV2]:
        """Get submission item by ID"""
        with self.get_session() as session:
            return session.query(SubmissionItemV2).filter(SubmissionItemV2.id == item_id).first()
    
    # ============ GRADING OPERATIONS ============
    
    def create_or_update_grading(self, submission_item_id: int, is_correct: bool, 
                                error_description: str = None, teacher_notes: str = None) -> int:
        """Create or update grading result"""
        with self.get_session() as session:
            grading = (session.query(GradingV2)
                      .filter(GradingV2.submission_item_id == submission_item_id)
                      .first())
            
            if grading:
                # Update existing
                grading.is_correct = is_correct
                grading.error_description = error_description
                grading.teacher_notes = teacher_notes
                grading.graded_at = datetime.now().replace(microsecond=0)
            else:
                # Create new
                grading = GradingV2(
                    submission_item_id=submission_item_id,
                    is_correct=is_correct,
                    error_description=error_description,
                    teacher_notes=teacher_notes
                )
                session.add(grading)
            
            session.commit()
            return grading.id
    
    def get_gradings_by_submission(self, submission_id: int) -> list[GradingV2]:
        """Get all grading results for a submission, with related items eagerly loaded."""
        with self.get_session() as session:
            return (
                session.query(GradingV2)
                .join(SubmissionItemV2) # Cần join để có thể filter theo submission_id
                .options(
                    # Tải lồng nhau: Grading -> SubmissionItem -> Question
                    joinedload(GradingV2.submission_item).joinedload(SubmissionItemV2.question)
                )
                .filter(SubmissionItemV2.submission_id == submission_id)
                .all()
            )
    
    def get_submission_grading_summary(self, submission_id: int) -> Dict[str, Any]:
        """Get grading summary for a submission"""
        with self.get_session() as session:
            items = (session.query(SubmissionItemV2)
                    .filter(SubmissionItemV2.submission_id == submission_id)
                    .all())
            
            total_questions = len(items)
            graded_count = 0
            correct_count = 0
            
            results = []
            
            for item in items:
                grading = item.grading
                if grading:
                    graded_count += 1
                    if grading.is_correct:
                        correct_count += 1
                    
                    results.append({
                        "question_id": item.question_id,
                        "question": item.question,
                        "is_correct": grading.is_correct,
                        "error_description": grading.error_description,
                        "teacher_notes": grading.teacher_notes
                    })
                else:
                    results.append({
                        "question_id": item.question_id,
                        "question": item.question,
                        "is_correct": None,
                        "error_description": None,
                        "teacher_notes": None
                    })
            
            return {
                "total_questions": total_questions,
                "graded_count": graded_count,
                "correct_count": correct_count,
                "accuracy": correct_count / graded_count if graded_count > 0 else 0,
                "results": results
            }
    
    def create_grading(self, submission_item_id: int, question_id: int, is_correct: bool,
                       confidence: float = None, error_description: str = None,
                       error_phrases: List[str] = None, partial_credit: bool = False,
                       clarify_notes: str = None) -> int:
        """Create new grading result with AI data (or update if exists)"""
        with self.get_session() as session:
            # Check if grading already exists for this submission_item_id
            existing_grading = (session.query(GradingV2)
                              .filter(GradingV2.submission_item_id == submission_item_id)
                              .first())
            
            if existing_grading:
                # Update existing grading
                existing_grading.is_correct = is_correct
                existing_grading.confidence = confidence
                existing_grading.error_description = error_description
                existing_grading.error_phrases = json.dumps(error_phrases or [], ensure_ascii=False)
                existing_grading.partial_credit = partial_credit
                existing_grading.clarify_notes = clarify_notes
                existing_grading.graded_at = datetime.now().replace(microsecond=0)
                session.commit()
                return existing_grading.id
            else:
                # Create new grading
                grading = GradingV2(
                    submission_item_id=submission_item_id,
                    question_id=question_id,
                    is_correct=is_correct,
                    confidence=confidence,
                    error_description=error_description,
                    error_phrases=json.dumps(error_phrases or [], ensure_ascii=False),
                    partial_credit=partial_credit,
                    clarify_notes=clarify_notes
                )
                session.add(grading)
                session.commit()
                return grading.id
    
    def get_gradings_by_submission(self, submission_id: int) -> list[GradingV2]:
        """Get all grading results for a submission"""
        with self.get_session() as session:
            return (session.query(GradingV2)
                   .join(SubmissionItemV2)
                   .filter(SubmissionItemV2.submission_id == submission_id)
                   .all())
    
    def update_grading(self, grading_id: int, is_correct: bool = None,
                      confidence: float = None, error_description: str = None,
                      error_phrases: List[str] = None, partial_credit: bool = None,
                      teacher_notes: str = None, clarify_notes: str = None) -> bool:
        """Update existing grading result"""
        with self.get_session() as session:
            grading = session.query(GradingV2).filter(GradingV2.id == grading_id).first()
            if not grading:
                return False
            
            if is_correct is not None:
                grading.is_correct = is_correct
            if confidence is not None:
                grading.confidence = confidence
            if error_description is not None:
                grading.error_description = error_description
            if error_phrases is not None:
                grading.error_phrases = json.dumps(error_phrases, ensure_ascii=False)
            if partial_credit is not None:
                grading.partial_credit = partial_credit
            if teacher_notes is not None:
                grading.teacher_notes = teacher_notes
            if clarify_notes is not None:
                grading.clarify_notes = clarify_notes
            
            grading.graded_at = datetime.now().replace(microsecond=0)
            
            session.commit()
            return True
    
    def delete_grading(self, grading_id: int) -> bool:
        """Delete a grading result"""
        with self.get_session() as session:
            grading = session.query(GradingV2).filter(GradingV2.id == grading_id).first()
            if grading:
                session.delete(grading)
                session.commit()
                return True
            return False

# Global instance
from core.config import DATABASE_URL
db_manager = DatabaseManagerV2(DATABASE_URL)