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
    def _scale_bbox_to_canvas(bbox_coords: Dict, original_dims: Dict, canvas_width: int) -> Dict:
        """Scale bounding box coordinates from original image to canvas size."""
        if not bbox_coords or not original_dims:
            return None

        try:
            # Calculate scale factor based on width (maintain aspect ratio)
            scale_factor = canvas_width / original_dims['width']

            return {
                'left': int(bbox_coords['left'] * scale_factor),
                'top': int(bbox_coords['top'] * scale_factor),
                'width': int(bbox_coords['width'] * scale_factor),
                'height': int(bbox_coords['height'] * scale_factor)
            }
        except (KeyError, TypeError, ZeroDivisionError):
            return None

    @staticmethod
    def _wrap_text(text: str, max_width_chars: int = 20) -> str:
        """Wrap text to prevent exceeding 60% of image width with better alignment."""
        if len(text) <= max_width_chars:
            return text

        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            # Check if adding this word would exceed the limit
            test_line = current_line + (" " if current_line else "") + word
            if len(test_line) <= max_width_chars:
                current_line = test_line
            else:
                # If current line has content, save it and start new line
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Word is too long, need to break it
                    if len(word) > max_width_chars:
                        # Break long word
                        lines.append(word[:max_width_chars-1] + "-")
                        current_line = word[max_width_chars-1:]
                    else:
                        current_line = word

        if current_line:
            lines.append(current_line)

        return "\n".join(lines)

    @staticmethod
    def _create_annotation_object(
        text: str,
        left: int,
        top: int,
        fill_color: str,
        font_size: int = 20,
        text_color: str = "#000000",
        image_width: int = 700
    ) -> Dict[str, Any]:
        """Creates a single textbox object for the canvas with improved text wrapping."""
        # Calculate max characters based on 60% of image width
        max_width_chars = int((image_width * 0.6) / (font_size * 0.6))
        wrapped_text = CanvasHelper._wrap_text(text, max_width_chars)

        # Calculate height based on number of lines
        line_count = wrapped_text.count('\n') + 1
        text_height = font_size * line_count * 1.2

        return {
            "type": "textbox",
            "version": "5.3.0",
            "originX": "left",
            "originY": "top",
            "left": left,
            "top": top,
            "width": min(len(text) * font_size * 0.6, image_width * 0.6),
            "height": text_height,
            "fill": fill_color,
            "stroke": fill_color,
            "strokeWidth": 1,  # Reduced stroke width
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
            "text": wrapped_text,
            "fontSize": font_size,
            "fontWeight": "normal",  # Changed from "bold" to "normal"
            "fontFamily": "Arial",
            "fontStyle": "normal",
            "lineHeight": 1.2,  # Slightly increased for better readability
            "underline": False,
            "overline": False,
            "linethrough": False,
            "textAlign": "left",  # Left alignment
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
        circle_count: int = 0,
        image_width: int = 700
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
            # Try to get bbox positioning for this item
            bbox_coords = None
            original_dims = None

            if item.get('bbox_coordinates') and item.get('original_dimensions'):
                try:
                    bbox_coords = json.loads(item['bbox_coordinates'])
                    original_dims = json.loads(item['original_dimensions'])
                except (json.JSONDecodeError, TypeError):
                    pass

            # Scale bbox to canvas if available
            scaled_bbox = CanvasHelper._scale_bbox_to_canvas(bbox_coords, original_dims, image_width)

            # Determine positioning: use bbox if available, fallback to left-side stacking
            if scaled_bbox:
                phrase_left = scaled_bbox['left']
                phrase_top = scaled_bbox['top']
            else:
                phrase_left = 10  # Fallback to left side
                phrase_top = current_top
                current_top += 60  # Only increment for fallback positioning

            if item['is_correct']:
                annotation = CanvasHelper._create_annotation_object(
                    text="✅ Chính xác",
                    left=phrase_left,
                    top=phrase_top,
                    fill_color="#00ff00",
                    text_color="#00ff00",
                    image_width=image_width
                )
                objects.append(annotation)
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
                
                # Display critical error phrases only (no descriptions)
                phrase_offset = 0  # Vertical offset for multiple phrases in same bbox
                if critical_errors:
                    for error in critical_errors:
                        # Only show phrases, skip description
                        if error.get('phrases'):
                            for phrase in error['phrases']:
                                # Calculate position: use bbox if available, fallback to left stacking
                                if scaled_bbox:
                                    error_left = phrase_left
                                    error_top = phrase_top + phrase_offset
                                else:
                                    error_left = 10
                                    error_top = current_top

                                annotation = CanvasHelper._create_annotation_object(
                                    text=f"❌ {phrase}",
                                    left=error_left,
                                    top=error_top,
                                    fill_color="#ff0000",
                                    text_color="#ff0000",
                                    image_width=image_width
                                )
                                objects.append(annotation)

                                if scaled_bbox:
                                    phrase_offset += 25  # Stack within bbox
                                else:
                                    current_top += 50  # Stack on left side
                
                # Display part error phrases only (no descriptions)
                if part_errors:
                    for error in part_errors:
                        # Only show phrases, skip description
                        if error.get('phrases'):
                            for phrase in error['phrases']:
                                # Calculate position: use bbox if available, fallback to left stacking
                                if scaled_bbox:
                                    error_left = phrase_left
                                    error_top = phrase_top + phrase_offset
                                else:
                                    error_left = 10
                                    error_top = current_top

                                annotation = CanvasHelper._create_annotation_object(
                                    text=f"⚠️ {phrase}",
                                    left=error_left,
                                    top=error_top,
                                    fill_color="#ffaa00",
                                    text_color="#ffaa00",
                                    image_width=image_width
                                )
                                objects.append(annotation)

                                if scaled_bbox:
                                    phrase_offset += 25  # Stack within bbox
                                else:
                                    current_top += 50  # Stack on left side
                
                # Fallback to legacy error display if no new format available
                if not critical_errors and not part_errors:
                    # Use legacy error_phrases
                    error_phrases = item.get('error_phrases', [])
                    if error_phrases and len(error_phrases) > 0:
                        for phrase in error_phrases:
                            # Calculate position: use bbox if available, fallback to left stacking
                            if scaled_bbox:
                                error_left = phrase_left
                                error_top = phrase_top + phrase_offset
                            else:
                                error_left = 10
                                error_top = current_top

                            annotation = CanvasHelper._create_annotation_object(
                                text=f"❌ {phrase}",
                                left=error_left,
                                top=error_top,
                                fill_color="#ff0000",
                                text_color="#ff0000",
                                image_width=image_width
                            )
                            objects.append(annotation)

                            if scaled_bbox:
                                phrase_offset += 25  # Stack within bbox
                            else:
                                current_top += 60  # Stack on left side
                    else:
                        # Generic fallback
                        if scaled_bbox:
                            error_left = phrase_left
                            error_top = phrase_top
                        else:
                            error_left = 10
                            error_top = current_top

                        annotation = CanvasHelper._create_annotation_object(
                            text="❌ Có lỗi",
                            left=error_left,
                            top=error_top,
                            fill_color="#ff0000",
                            text_color="#ff0000",
                            image_width=image_width
                        )
                        objects.append(annotation)
                        current_top += 60

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