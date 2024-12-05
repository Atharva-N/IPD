import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips
import requests
import os
import re  # Import the re module for regular expressions

# Replace these with your actual API keys
PEXELS_API_KEY = "Oe8LHdq5GMhzMQHbgjJfgaFWycoe70Vm061rCg36wDYLf3d52t2SLoPi"
GENIE_API_KEY = "AIzaSyBzB-FbuQimtmUEoaXUwYdGoxUwTXvMO3I"

def get_gemini_response(question):
    try:
        from google.cloud import generative_ai as genai
        genai.configure(api_key=GENIE_API_KEY)
        
        # Example of how you might call the API (adjust based on actual API documentation)
        response = genai.generate_text(prompt=question)
        
        # Adjust this line according to the actual response structure
        if response.candidates:
            return response.candidates[0].output.strip()
        else:
            return 'No response text available.'
    except Exception as e:
        st.error(f"Error occurred in get_gemini_response: {e}")
        return None

def extract_keywords(text):
    """Extract keywords or example phrases from the script."""
    if text:
        return re.findall(r'\b\w+\b', text)
    return []

def get_videos(topic, num_results=5):
    headers = {"Authorization": PEXELS_API_KEY}
    
    # Fetch videos based on the topic
    videos_url = "https://api.pexels.com/videos/search"
    params = {"query": topic, "per_page": num_results}
    try:
        response = requests.get(videos_url, headers=headers, params=params)
        response.raise_for_status()
        videos = [video["video_files"][0]["link"] for video in response.json().get("videos", [])]
    except Exception as e:
        st.error(f"Error fetching videos: {e}")
        videos = []

    return videos

def download_video(video_url, index):
    video_path = f"temp_video_{index}.mp4"
    try:
        response = requests.get(video_url)
        response.raise_for_status()
        with open(video_path, "wb") as f:
            f.write(response.content)
        return video_path
    except Exception as e:
        st.error(f"Error downloading video {video_url}: {e}")
        return None

def create_compilation(videos, output_file='compilation.mp4'):
    clips = []

    # Add video clips
    for idx, video_url in enumerate(videos):
        video_path = download_video(video_url, idx)
        if video_path:
            try:
                video_clip = VideoFileClip(video_path)
                clips.append(video_clip)
            except Exception as e:
                st.error(f"Error processing video {video_url}: {e}")

    if clips:
        try:
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(output_file, fps=24)
        except Exception as e:
            st.error(f"Error creating video compilation: {e}")
    else:
        st.error("No clips to compile.")

    # Clean up temporary files
    for idx in range(len(videos)):
        video_path = f"temp_video_{idx}.mp4"
        if os.path.exists(video_path):
            os.remove(video_path)

# Streamlit app UI
st.title("Educational Script Generator")
st.write("Welcome")
st.write("Learn any topic easily")

# Input for the topic
topic = st.text_input("Enter the topic to learn")

# Buttons for difficulty levels
difficulty = None
if st.button("Beginner"):
    difficulty = "beginner"
elif st.button("Amateur"):
    difficulty = "amateur"
elif st.button("Advanced"):
    difficulty = "advanced"

# Button to submit
submit = st.button("Submit")

if submit:
    if topic and difficulty:
        st.write("Generating script, please wait...")

        # Prompt construction
        prompt = f"Write a 300-word educational script for a video that explains the topic of '{topic}' at a {difficulty} difficulty level. Use clear and engaging language suitable for teenagers. Include at least two real-life examples to illustrate key concepts. Ensure the explanation is concise and maintains the audience's interest throughout the script."

        # Get the response from the Gemini model
        script = get_gemini_response(prompt)
        st.write(script)

        # Extract keywords for relevant videos
        keywords = extract_keywords(script)

        # Get relevant videos
        videos = get_videos(topic)
        st.write(f"Found {len(videos)} videos")

        # Create a compilation video
        st.write("Creating a video compilation, please wait...")
        create_compilation(videos)
        
        # Display the video compilation
        if os.path.exists("compilation.mp4"):
            st.write("### Compilation Video")
            st.video("compilation.mp4")
        else:
            st.write("No video compilation found.")
    else:
        st.write("Please enter a valid topic and select a difficulty level.")
