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
        font_size: int = 24
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
            "stroke": None,
            "strokeWidth": 0,
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
            "opacity": 0.85,
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
    def generate_initial_drawing(
        graded_items: List[Dict[str, Any]],
        current_page_index: int
    ) -> Dict[str, Any]:
        """
        Generates the full initial drawing JSON for a specific page.
        Annotations will be stacked on the left side initially.
        Uses caching to prevent regenerating identical drawings.
        """
        # Create cache key from input data
        cache_data = {
            'items': [(item.get('question_label'), item.get('is_correct'), item.get('source_page_index')) 
                     for item in graded_items],
            'page_index': current_page_index
        }
        cache_key = hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()
        
        # Return cached result if available
        if cache_key in CanvasHelper._drawing_cache:
            return CanvasHelper._drawing_cache[cache_key]
        objects = []
        current_top = 10 

        items_for_this_page = [
            item for item in graded_items if item.get('source_page_index') == current_page_index
        ]

        for item in items_for_this_page:
            if item['is_correct']:
                annotation = CanvasHelper._create_annotation_object(
                    text="✅ Chính xác",
                    left=10,
                    top=current_top,
                    fill_color="rgba(33, 195, 84, 0.7)"
                )
                objects.append(annotation)
                current_top += 50
            else:
                for phrase in item['error_phrases']:
                    annotation = CanvasHelper._create_annotation_object(
                        text=f"❌ {phrase}",
                        left=10,
                        top=current_top,
                        fill_color="rgba(255, 75, 75, 0.7)"
                    )
                    objects.append(annotation)
                    current_top += 50

        result = {"version": "5.3.0", "objects": objects}
        
        # Cache result for future use
        CanvasHelper._drawing_cache[cache_key] = result
        
        return result