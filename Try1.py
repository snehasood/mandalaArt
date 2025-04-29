import streamlit as st
import requests
import base64
import io
import os
from PIL import Image, ImageOps
import time
import random
import json
from datetime import datetime
from openai import OpenAI

# Set page configuration - force wide mode to avoid scrolling
st.set_page_config(
    page_title="Mandala Art Generator",
    layout="wide",
    initial_sidebar_state="collapsed"  # Start with collapsed sidebar to maximize space
)

# App styling with grey cloud background, pink text, and improved layout
st.markdown("""
<style>
    /* Grey cloud background */
    .main {
        background-color: #e0e0e0;
        background-image: url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' xmlns='http://www.w3.org/2000/svg'%3E%3Cdefs%3E%3Cpattern id='pattern' width='300' height='300' patternUnits='userSpaceOnUse' patternTransform='rotate(10)'%3E%3Ccircle cx='150' cy='150' r='100' fill='%23d1d1d1' fill-opacity='0.7'/%3E%3Ccircle cx='50' cy='50' r='60' fill='%23c7c7c7' fill-opacity='0.5'/%3E%3Ccircle cx='250' cy='50' r='80' fill='%23b8b8b8' fill-opacity='0.6'/%3E%3Ccircle cx='50' cy='250' r='70' fill='%23c4c4c4' fill-opacity='0.8'/%3E%3Ccircle cx='250' cy='250' r='50' fill='%23cdcdcd' fill-opacity='0.6'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='100%25' height='100%25' fill='url(%23pattern)'/%3E%3C/svg%3E");
        background-attachment: fixed;
        background-size: cover;
    }
    
    /* Increased font size and pink text color */
    body {
        font-size: 18px !important;
        color: #E91E63 !important;
    }
    
    p, div, label, span {
        font-size: 18px !important;
        color: #E91E63 !important;
    }
    
    /* Compact layout with minimal padding */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        max-width: 100%;
    }
    
    /* Reduced spacing for headers */
    h1, h2, h3 {
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
        color: #C2185B;
        font-size: 24px !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
    }
    
    h4 {
        color: #D81B60;
        font-size: 22px !important;
    }
    
    /* Compact form elements with larger font */
    .stTextInput > div > div > input {
        padding: 0.5rem !important;
        font-size: 18px !important;
    }
    
    /* Compact buttons */
    .stButton>button {
        background-color: #FF4081;
        color: white;
        border-radius: 10px;
        padding: 8px 16px !important;
        font-size: 18px;
        border: none;
    }
    
    /* Style containers */
    .glass-container {
        background-color: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(5px);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Make images fit better */
    .stImage > img {
        max-height: 350px !important;
        width: auto !important;
    }
    
    /* Compact rating section */
    .compact-rating button {
        padding: 4px 10px !important;
        margin: 2px !important;
    }
    
    .rating-label {
        font-size: 16px !important;
        margin: 0 !important;
    }
    
    /* Hide unnecessary elements when we need space */
    .element-container:has(iframe[height="0"]) {
        display: none;
    }
    
    /* More compact header */
    header {
        visibility: hidden;
    }
    
    /* Footer adjustment */
    footer {
        visibility: hidden;
    }
    
    /* Reduce margins globally */
    div.block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Caption styling */
    .caption {
        font-size: 16px !important;
        color: #EC407A !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 18px !important;
        color: #D81B60 !important;
    }
    
    /* Checkbox label */
    .stCheckbox label {
        font-size: 18px !important;
        color: #E91E63 !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if 'images' not in st.session_state:
    st.session_state.images = []
if 'ratings' not in st.session_state:
    st.session_state.ratings = {}
if 'image_counter' not in st.session_state:
    st.session_state.image_counter = 0
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "generate"  # Default tab

# Load saved ratings if they exist
def load_ratings():
    try:
        if os.path.exists("ratings.json"):
            with open("ratings.json", "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.error(f"Error loading ratings: {e}")
        return {}

# Save ratings to file
def save_rating(image_id, rating):
    ratings = load_ratings()
    ratings[image_id] = {
        "rating": rating,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open("ratings.json", "w") as f:
            json.dump(ratings, f)
        st.session_state.ratings = ratings
    except Exception as e:
        st.error(f"Error saving rating: {e}")

# Convert image to black and white
def convert_to_bw(image_data):
    try:
        image = Image.open(io.BytesIO(image_data))
        bw_image = ImageOps.grayscale(image)
        bw_image = ImageOps.autocontrast(bw_image, cutoff=2)
        buffer = io.BytesIO()
        bw_image.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as e:
        st.error(f"Error converting to black and white: {e}")
        return image_data  # Return original if conversion fails

# Function to generate mandala art using DALL-E API
def generate_mandala(inspiration_words, api_key, black_and_white=False):
    with st.spinner("Creating your mandala art..."):
        # If API key is provided, use DALL-E
        if api_key:
            try:
                # Initialize the OpenAI client with the API key
                client = OpenAI(api_key=api_key)
                
                # Generate prompt for DALL-E
                base_prompt = f"Create a beautiful, intricate mandala art design inspired by these words: {inspiration_words}. Use symmetrical patterns and sacred geometry. The mandala should be centered, detailed, and have a meditative quality."
                
                # Modify prompt for black and white if requested
                if black_and_white:
                    prompt = base_prompt + " Make it black and white with clear distinct lines perfect for coloring by hand. Create high contrast between the lines and background so it's easy to print and color."
                else:
                    prompt = base_prompt + " Use vibrant colors and beautiful color harmonies that reflect the inspiration words."
                
                # Call DALL-E API using the updated client approach
                response = client.images.generate(
                    model="dall-e-3",  # Use the latest DALL-E model
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    quality="standard",
                    response_format="url"
                )
                
                # Get image URL from response
                image_url = response.data[0].url
                
                # Download the image
                image_response = requests.get(image_url)
                if image_response.status_code != 200:
                    raise Exception(f"Failed to download image: Status code {image_response.status_code}")
                    
                image_data = image_response.content
                
                # Convert to black and white if requested
                if black_and_white:
                    image_data = convert_to_bw(image_data)
                
                # Generate a unique ID for this image
                image_id = f"mandala_{st.session_state.image_counter}"
                st.session_state.image_counter += 1
                
                return {
                    "id": image_id,
                    "image": image_data,
                    "inspiration": inspiration_words,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "demo": False,
                    "bw": black_and_white
                }
                
            except Exception as e:
                st.error(f"Error with DALL-E API: {str(e)}")
                st.error("Please check your API key and try again.")
                return None
        else:
            # If no API key, show error message
            st.error("API key is required to generate mandalas. Please enter your OpenAI API key.")
            return None

# Function to allow image download
def get_image_download_link(img, filename, text, is_bw=False):
    buffered = io.BytesIO(img)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    button_color = "#FF4081" if not is_bw else "#757575"
    text_addon = " (Printable)" if is_bw else ""
    href = f'<a href="data:image/png;base64,{img_str}" download="{filename}" style="text-decoration:none;"><button style="background-color:{button_color};color:white;padding:8px 14px;border:none;border-radius:5px;cursor:pointer;font-size:16px;">{text}{text_addon}</button></a>'
    return href

# Function to handle rating submission
def rate_image(image_id, rating):
    save_rating(image_id, rating)
    st.success(f"Thanks for rating {rating}/5 stars!")

# Rating descriptions (shortened for compact display)
rating_descriptions = {
    1: "I didn't like it",
    2: "It's okay",
    3: "Decent mandala",
    4: "Very nice design",
    5: "Gorgeous! I'm happy!"
}

# Create a single-screen layout - main area divided into input and output
st.markdown("<h2 style='text-align: center; margin-bottom: 10px; font-size: 32px !important;'>🌸 Mandala Art Generator 🌸</h2>", unsafe_allow_html=True)

# Brief introduction at the top
st.markdown("""
<div style="background-color: rgba(255, 255, 255, 0.7); padding: 12px; border-radius: 10px; margin-bottom: 10px; text-align: center;">
  <p style="margin: 0; font-size: 20px !important; color: #E91E63 !important;">Mandalas are sacred symbols of unity and cosmic harmony, used for meditation and mindfulness practice.</p>
</div>
""", unsafe_allow_html=True)

# Create a two-column layout for the main content
col1, col2 = st.columns([3, 7])

# Input column - make it compact
with col1:
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    
    # API Key in main panel - MANDATORY
    st.markdown("<h4>👑 OpenAI API Key (Required)</h4>", unsafe_allow_html=True)
    api_key = st.text_input("Enter your OpenAI API Key:", 
                           value=st.session_state.api_key,
                           type="password",
                           key="api_key_input",
                           help="Required for DALL-E image generation")
    
    if api_key:
        st.session_state.api_key = api_key
        st.success("API Key saved!")
    
    # Input form
    with st.form(key="inspiration_form", clear_on_submit=False):
        st.markdown("<h4>Create Your Mandala</h4>", unsafe_allow_html=True)
        
        # Input fields
        inspiration = st.text_input("Inspiration (1-5 words):", 
                                  placeholder="harmony peace nature",
                                  help="Words that inspire your mandala")
        
        # Add black and white option
        bw_option = st.checkbox("Black & white (for coloring)", 
                              help="Perfect for printing and coloring by hand")
        
        # Submit button
        generate_button = st.form_submit_button("✨ Generate Mandala")
    
    # Download information
    st.markdown("""
    <div style="background-color: rgba(255, 192, 203, 0.2); padding: 10px; border-radius: 5px; margin-top: 10px;">
      <p style="margin: 0; font-size: 18px !important; color: #E91E63 !important;">
        <strong>💾 All generated mandalas can be downloaded</strong> for printing, coloring, or digital use!
      </p>
    </div>
    """, unsafe_allow_html=True)
    
    # About section - collapsed by default
    with st.expander("ℹ️ About Mandalas"):
        st.markdown("""
        <div style="font-size: 18px !important; color: #E91E63 !important;">
        Mandalas are sacred symbols representing cosmic harmony and wholeness. Creating and coloring them reduces
        stress while encouraging mindfulness.
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Output column
with col2:
    # Generate art when the button is clicked
    if generate_button:
        if not api_key:
            st.error("API key is required! Please enter your OpenAI API key.")
        elif not inspiration:
            st.warning("Please enter at least one word for inspiration.")
        else:
            words = inspiration.strip().split()
            if len(words) > 5:
                st.warning("Please limit your inspiration to 5 words maximum.")
            else:
                # Generate the mandala art
                result = generate_mandala(inspiration, st.session_state.api_key, bw_option)
                if result:
                    # Add to session state
                    st.session_state.images.insert(0, result)  # Add new image to the beginning
                    
                    # If we have too many images, remove the oldest ones
                    if len(st.session_state.images) > 5:  # Reduced from 10 to 5 for better fit
                        st.session_state.images = st.session_state.images[:5]
    
    # Display generated images in a compact format
    if st.session_state.images:
        latest_img = st.session_state.images[0]  # Get the most recent image
        
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        
        # Display image with compact layout
        is_bw = latest_img.get("bw", False)
        bw_label = " (Printable)" if is_bw else ""
        
        image_col, info_col = st.columns([3, 2])
        
        with image_col:
            st.image(latest_img["image"], caption=f"Inspired by: {latest_img['inspiration']}{bw_label}")
            
            # Download button with emphasis
            st.markdown("""
            <div style="text-align: center; margin: 10px 0;">
                <p style="margin-bottom: 5px; font-size: 18px !important; color: #E91E63 !important;"><strong>Click below to download your mandala:</strong></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(get_image_download_link(
                latest_img["image"], 
                f"mandala_{latest_img['id']}.png", 
                "💾 Download Mandala",
                is_bw
            ), unsafe_allow_html=True)
        
        with info_col:
            st.markdown("#### Rate this art")
            
            # Compact rating display
            st.markdown('<div class="compact-rating">', unsafe_allow_html=True)
            rate_cols = st.columns(5)
            for j in range(5):
                rating_value = j+1
                if rate_cols[j].button(f"{rating_value}⭐", key=f"{latest_img['id']}_{j}"):
                    rate_image(latest_img['id'], rating_value)
            
            # Show rating descriptions in a more compact way
            for r in range(1, 6):
                st.markdown(f'<p class="rating-label">{r}⭐: {rating_descriptions[r]}</p>', unsafe_allow_html=True)
            
            # Show current rating if available
            if latest_img['id'] in st.session_state.ratings:
                current_rating = st.session_state.ratings[latest_img['id']]['rating']
                st.markdown(f"""
                <div style="background-color: #FCE4EC; padding: 8px; border-radius: 5px; margin-top: 10px;">
                    <p style="margin:0; font-size:18px !important; color: #C2185B !important;"><strong>Your rating:</strong> {current_rating}⭐</p>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Previous images section (tabs or dropdown)
        if len(st.session_state.images) > 1:
            st.markdown("<hr style='margin: 15px 0; border-color: #F8BBD0;'>", unsafe_allow_html=True)
            st.markdown("<h4 style='font-size: 22px !important;'>Previous Creations</h4>", unsafe_allow_html=True)
            
            # Create a horizontal scrollable area for previous images
            prev_cols = st.columns(min(4, len(st.session_state.images)-1))
            for i, col in enumerate(prev_cols):
                if i < len(st.session_state.images)-1:  # Skip the first (current) image
                    prev_img = st.session_state.images[i+1]
                    with col:
                        st.image(prev_img["image"], width=150)  # Small thumbnail
                        st.caption(f"{prev_img['inspiration'][:10]}...")
                        # Small download button
                        st.markdown(get_image_download_link(
                            prev_img["image"], 
                            f"mandala_{prev_img['id']}.png", 
                            "💾 Download",
                            prev_img.get("bw", False)
                        ), unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Placeholder when no images are generated yet
        st.markdown("""
        <div class="glass-container" style="height: 400px; display: flex; align-items: center; justify-content: center; text-align: center;">
            <div>
                <h3 style="font-size: 26px !important; color: #C2185B !important;">Your mandala art will appear here</h3>
                <p style="font-size: 20px !important; color: #E91E63 !important;">Enter inspiration words and click "Generate Mandala" to begin your creative journey</p>
                <p style="font-style: italic; font-size: 20px !important; color: #F06292 !important;">Try words like "serenity", "ocean", or "joy"</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Minimal footer
st.markdown("<div style='text-align: center; margin-top: 10px;'><p style='font-size: 18px !important; color: #E91E63 !important;'>Made with ❤️ and Streamlit</p></div>", unsafe_allow_html=True)