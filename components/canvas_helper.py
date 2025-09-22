# components/canvas_helper.py
import streamlit as st
import hashlib
import json
from typing import List, Dict, Any

class CanvasHelper:
    """
    Helper class to generate initial drawing JSON for streamlit-drawable-canvas.
    """
    _drawing_cache = {}  # Cache to prevent regenerating identical drawings

    @staticmethod
    def _create_annotation_object(
        text: str,
        left: int,
        top: int,
        fill_color: str,
        font_size: int = 24,
        text_color: str = "#000000"
    ) -> Dict[str, Any]:
        """Creates a single textbox object for the canvas."""
        return {
            "type": "textbox",
            "version": "5.3.0",
            "originX": "left",
            "originY": "top",
            "left": left,
            "top": top,
            "width": len(text) * font_size * 0.6,
            "height": font_size + 10,
            "fill": fill_color,
            "stroke": fill_color,
            "strokeWidth": 2,
            "strokeDashArray": None,
            "strokeLineCap": "butt",
            "strokeDashOffset": 0,
            "strokeLineJoin": "miter",
            "strokeUniform": False,
            "strokeMiterLimit": 4,
            "scaleX": 1,
            "scaleY": 1,
            "angle": 0,
            "flipX": False,
            "flipY": False,
            "opacity": 1.0,
            "shadow": None,
            "visible": True,
            "backgroundColor": "",
            "fillRule": "nonzero",
            "paintFirst": "fill",
            "globalCompositeOperation": "source-over",
            "skewX": 0,
            "skewY": 0,
            "text": text,
            "fontSize": font_size,
            "fontWeight": "bold",
            "fontFamily": "Arial",
            "fontStyle": "normal",
            "lineHeight": 1.16,
            "underline": False,
            "overline": False,
            "linethrough": False,
            "textAlign": "center",
            "textBackgroundColor": "",
            "charSpacing": 0,
            "path": None,
            "styles": [],
            "minWidth": 20,
            "splitByGrapheme": False
        }

    @staticmethod
    def _create_circle_object(
        left: int,
        top: int,
        radius: int,
        stroke_color: str = "#ff0000",
        stroke_width: int = 2,
        fill_color: str = "transparent"
    ) -> Dict[str, Any]:
        """Creates a circle object for the canvas."""
        return {
            "type": "circle",
            "version": "5.3.0",
            "originX": "left",
            "originY": "top",
            "left": left,
            "top": top,
            "width": radius * 2,
            "height": radius * 2,
            "fill": fill_color,
            "stroke": stroke_color,
            "strokeWidth": stroke_width,
            "strokeDashArray": None,
            "strokeLineCap": "butt",
            "strokeDashOffset": 0,
            "strokeLineJoin": "miter",
            "strokeUniform": False,
            "strokeMiterLimit": 4,
            "scaleX": 1,
            "scaleY": 1,
            "angle": 0,
            "flipX": False,
            "flipY": False,
            "opacity": 1,
            "shadow": None,
            "visible": True,
            "backgroundColor": "",
            "fillRule": "nonzero",
            "paintFirst": "fill",
            "globalCompositeOperation": "source-over",
            "skewX": 0,
            "skewY": 0,
            "radius": radius,
            "startAngle": 0,
            "endAngle": 6.283185307179586
        }

    @staticmethod
    def generate_initial_drawing(
        graded_items: List[Dict[str, Any]],
        current_page_index: int,
        circle_count: int = 0
    ) -> Dict[str, Any]:
        """
        Generates the full initial drawing JSON for a specific page.
        Annotations will be stacked on the left side initially.
        Uses caching to prevent regenerating identical drawings.
        """
        # Create cache key from input data
        cache_data = {
            'items': [(item.get('question_label'), item.get('is_correct'), 
                      item.get('source_page_indices', [item.get('source_page_index', 0)])) 
                     for item in graded_items],
            'page_index': current_page_index,
            'circle_count': circle_count
        }
        cache_key = hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()
        
        # Return cached result if available
        if cache_key in CanvasHelper._drawing_cache:
            return CanvasHelper._drawing_cache[cache_key]
        objects = []
        current_top = 10 

        # Filter items for current page (supports multi-page items)
        items_for_this_page = []
        for item in graded_items:
            source_page_indices = item.get('source_page_indices', [item.get('source_page_index', 0)])
            if current_page_index in source_page_indices:
                items_for_this_page.append(item)

        # Debug: Print what items we're processing
        print(f"DEBUG: Processing {len(items_for_this_page)} items for page {current_page_index}")
        for item in items_for_this_page:
            print(f"  - {item.get('question_label', 'Unknown')}: correct={item.get('is_correct', False)}")
            print(f"    critical_errors: {item.get('critical_errors', 'None')}")
            print(f"    part_errors: {item.get('part_errors', 'None')}")
            print(f"    error_phrases: {item.get('error_phrases', [])}")

        for item in items_for_this_page:
            if item['is_correct']:
                annotation = CanvasHelper._create_annotation_object(
                    text="✅ Chính xác",
                    left=10,
                    top=current_top,
                    fill_color="#00ff00",
                    text_color="#00ff00"
                )
                objects.append(annotation)
                current_top += 50
            else:
                # Parse critical and part errors from the grading data (same as results page)
                critical_errors = []
                part_errors = []
                
                if item.get('critical_errors'):
                    try:
                        critical_errors = json.loads(item['critical_errors'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                if item.get('part_errors'):
                    try:
                        part_errors = json.loads(item['part_errors'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Display critical errors (red boxes)
                if critical_errors:
                    for error in critical_errors:
                        description = error.get('description', 'Critical Error')
                        annotation = CanvasHelper._create_annotation_object(
                            text=f"🔴 {description}",
                            left=10,
                            top=current_top,
                            fill_color="#ff0000",
                            text_color="#ff0000"
                        )
                        objects.append(annotation)
                        current_top += 50
                        
                        # Add phrases from this error
                        if error.get('phrases'):
                            for phrase in error['phrases']:
                                annotation = CanvasHelper._create_annotation_object(
                                    text=f"❌ {phrase}",
                                    left=30,  # Indent slightly
                                    top=current_top,
                                    fill_color="#ff0000",
                                    text_color="#ff0000"
                                )
                                objects.append(annotation)
                                current_top += 40
                
                # Display part errors (yellow boxes)
                if part_errors:
                    for error in part_errors:
                        description = error.get('description', 'Part Error')
                        annotation = CanvasHelper._create_annotation_object(
                            text=f"🟡 {description}",
                            left=10,
                            top=current_top,
                            fill_color="#ffff00",
                            text_color="#ffff00"
                        )
                        objects.append(annotation)
                        current_top += 50
                        
                        # Add phrases from this error
                        if error.get('phrases'):
                            for phrase in error['phrases']:
                                annotation = CanvasHelper._create_annotation_object(
                                    text=f"⚠️ {phrase}",
                                    left=30,  # Indent slightly
                                    top=current_top,
                                    fill_color="#ffaa00",
                                    text_color="#ffaa00"
                                )
                                objects.append(annotation)
                                current_top += 40
                
                # Fallback to legacy error display if no new format available
                if not critical_errors and not part_errors:
                    # Use legacy error_phrases
                    error_phrases = item.get('error_phrases', [])
                    if error_phrases and len(error_phrases) > 0:
                        for phrase in error_phrases:
                            annotation = CanvasHelper._create_annotation_object(
                                text=f"❌ {phrase}",
                                left=10,
                                top=current_top,
                                fill_color="#ff0000",
                                text_color="#ff0000"
                            )
                            objects.append(annotation)
                            current_top += 50
                    else:
                        # Generic fallback
                        annotation = CanvasHelper._create_annotation_object(
                            text="❌ Có lỗi",
                            left=10,
                            top=current_top,
                            fill_color="#ff0000",
                            text_color="#ff0000"
                        )
                        objects.append(annotation)
                        current_top += 50

        # Add circles based on circle_count (ONLY THIS LOGIC)
        circle_positions = [
            (100, 100), (200, 150), (300, 100), (400, 150), (500, 100),
            (150, 250), (250, 300), (350, 250), (450, 300), (550, 250)
        ]
        
        # Add circles up to the specified count
        for i in range(min(circle_count, len(circle_positions))):
            x, y = circle_positions[i]
            circle = CanvasHelper._create_circle_object(
                left=x,
                top=y,
                radius=30,
                stroke_color="#ff0000",
                stroke_width=2
            )
            objects.append(circle)
        
        # If we need more circles than predefined positions, add them randomly
        if circle_count > len(circle_positions):
            import random
            for i in range(len(circle_positions), circle_count):
                circle = CanvasHelper._create_circle_object(
                    left=random.randint(50, 600),
                    top=random.randint(50, 400),
                    radius=30,
                    stroke_color="#ff0000",
                    stroke_width=2
                )
                objects.append(circle)
        
        return {"version": "5.3.0", "objects": objects}

        result = {"version": "5.3.0", "objects": objects}
        
        # Cache result for future use
        CanvasHelper._drawing_cache[cache_key] = result
        
        return result