# components/image_cropper.py
import streamlit as st
from PIL import Image
from streamlit_cropper import st_cropper
from typing import Dict, Any

class ImageCropperComponent:
    """
    A reusable UI component for the image cropping interface.
    This component wraps the streamlit_cropper library and manages its state.
    """

    @staticmethod
    def render(image: Image.Image, key: str) -> Dict[str, Any]:
        """
        Renders the image cropping interface and returns the cropped image.

        Args:
            image: The PIL Image to be cropped.
            key: A unique key for the cropper widget.

        Returns:
            A dictionary containing the cropped image object.
        """
        st.markdown("Drag the box to select an area.")
        
        # The streamlit_cropper widget
        cropped_img = st_cropper(
            image,
            realtime_update=True,
            box_color="#0066CC",
            aspect_ratio=None,  # Allow freeform cropping
            return_type="image",
            key=key
        )

        result = {
            "cropped_image": cropped_img
        }

        if cropped_img:
            st.markdown("**Cropped Preview:**")
            st.image(cropped_img)
            st.caption(f"Crop dimensions: {cropped_img.width} x {cropped_img.height} pixels")
        
        return result
