# Teacher Assistant v2.0

**Image-Centric Exam Grading System**

## 🎯 Overview

Teacher Assistant v2.0 is a complete redesign that eliminates OCR entirely, working directly with image pairs for maximum accuracy in mathematical content grading.

## 🏗️ Project Structure

```
teacher-assistant-2/
├── app/                    # Streamlit application modules
├── core/                   # Core configuration and utilities
│   ├── config.py          # Application configuration
├── database/               # Database models and management
│   ├── models_v2.py       # SQLAlchemy v2.0 schema
│   ├── manager_v2.py      # Database CRUD operations
├── static/                 # Static file storage
│   └── images/
│       ├── questions/     # Cropped question images
│       └── answers/       # Cropped answer images
├── scripts/               # Utility scripts
├── app.py                 # Main Streamlit application
├── test_cropper.py        # Streamlit-cropper integration test
└── requirements.txt       # Python dependencies
```

## ✅ Week 1 Completed Tasks

- [x] **Project Setup**: Complete directory structure created
- [x] **Dependencies**: Requirements.txt with streamlit, sqlalchemy, streamlit-cropper, pillow
- [x] **Database Schema v2.0**: Image-centric models (no text storage)
- [x] **Database Manager**: Full CRUD operations for all entities
- [x] **Cropper Integration**: Test app validates streamlit-cropper functionality
- [x] **Main App Shell**: Navigation structure and placeholder pages

## ✅ Week 2 Completed Tasks

- [x] **Exam Creation UI**: Complete form with image upload, validation, and preview
- [x] **Exam Digitization UI**: Full cropping interface with question labeling
- [x] **Image Saving Logic**: Utility functions for handling uploaded and cropped images
- [x] **Database Integration**: Exam and question creation with image path storage
- [x] **Navigation System**: Session-based page routing with seamless transitions
- [x] **Testing Framework**: Component test script to verify functionality
- [x] **Multi-Page Questions**: Complete support for questions spanning multiple pages

## ✅ Week 3 Completed Tasks

- [x] **AI Vision Playground**: Interactive development environment for testing grading
- [x] **Vision Grading Prompt**: Optimized prompt engineering for mathematical accuracy
- [x] **GPT-5 Mini Integration**: Complete image-pair grading with OpenAI vision model  
- [x] **Production Grading Service**: Robust GradingServiceV2 module with error handling
- [x] **Comprehensive Testing**: Automated validation with real exam image data
- [x] **Performance Benchmarking**: Speed and accuracy metrics for production readiness

## 🚀 How to Run

### 1. Install Dependencies
```bash
cd teacher-assistant-2
pip install -r requirements.txt
```

### 2. Set OpenAI API Key
```bash
# Edit .env file and add your API key:
OPENAI_API_KEY=your_api_key_here
```

### 3. Run Application
```bash
streamlit run app.py
```

### 4. Optional: Test Vision AI (Advanced)
```bash
python scripts/vision_playground.py          # Interactive AI testing
python scripts/validate_grading_service.py   # Production validation
```

**Complete Workflow Available:**
- ✅ Create Exam (upload exam images, enter metadata)
- ✅ Digitize Questions (crop individual questions with labels)
- ✅ Multi-page question support (1a-part1, 1a-part2, etc.)
- ✅ Vision AI grading system (ready for integration)
- 📋 View existing exams and questions
- 🔄 Navigate between pages seamlessly

## 📊 Database Schema v2.0

**Core Philosophy**: Store image paths instead of extracted text

- `v2_exams` - Exam metadata + original image paths
- `v2_questions` - Individual questions as cropped images
- `v2_submissions` - Student submissions + original images  
- `v2_submission_items` - Answer crops linked to questions
- `v2_gradings` - Simple boolean results + error descriptions

## 🗓️ Development Roadmap

### Phase 1: Foundation ✅ (Weeks 1-2 Complete)
- [x] Project structure and database
- [x] Streamlit-cropper integration
- [x] Exam creation and digitization UI
- [x] Complete image-based workflow for questions

### Phase 2: AI Core ✅ (Week 3 Complete, Week 4 Pending)
- [x] Vision AI playground development
- [x] GPT-5 Mini integration for image pair grading
- [x] Production-ready GradingServiceV2 module
- [ ] Answer mapping UI (student submissions)

### Phase 3: End-to-End (Week 5)
- [ ] Batch grading workflow
- [ ] Results display and teacher overrides

### Phase 4: Production Ready (Week 6)
- [ ] Performance optimization
- [ ] Cloud deployment preparation

## 🔧 Key Technologies

- **Frontend**: Streamlit + streamlit-cropper
- **Backend**: Python + SQLAlchemy
- **Database**: SQLite (dev) → PostgreSQL (prod)
- **AI**: OpenAI GPT-5 Mini vision capabilities
- **Storage**: Local files (dev) → Cloud storage (prod)

## 🎯 Next Steps

1. **Week 2**: Build exam creation and question digitization UI
2. **Week 3**: Develop vision AI grading playground
3. **Week 4**: Implement answer mapping workflow
4. **Week 5**: Complete end-to-end integration
5. **Week 6**: Optimize and prepare for deployment