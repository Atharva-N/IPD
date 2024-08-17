import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips
import requests
import google.generativeai as genai
import os
import re

# Replace these with your actual API keys
PEXELS_API_KEY = "Oe8LHdq5GMhzMQHbgjJfgaFWycoe70Vm061rCg36wDYLf3d52t2SLoPi"
GENIE_API_KEY = "AIzaSyBzB-FbuQimtmUEoaXUwYdGoxUwTXvMO3I"

def get_gemini_response(question):
    try:
        genai.configure(api_key=GENIE_API_KEY)
        model = genai.GenerativeModel("gemini-pro")
        chat = model.start_chat()
        response = chat.send_message(question, stream=True)

        response_text = ""
        for message in response:
            response_text += message.text

        return response_text

    except Exception as e:
        st.error(f"Error occurred: {e}")
        return None

def sanitize_keyword(keyword):
    """Sanitize keyword by removing special characters and unnecessary spaces."""
    return re.sub(r'[^\w\s]', '', keyword).strip()

def get_videos(keyword, num_results=1):
    headers = {"Authorization": PEXELS_API_KEY}
    
    # Sanitize the keyword
    clean_keyword = sanitize_keyword(keyword)
    
    # Fetch videos based on the sanitized keyword
    videos_url = "https://api.pexels.com/videos/search"
    params = {"query": clean_keyword, "per_page": num_results}
    try:
        response = requests.get(videos_url, headers=headers, params=params)
        response.raise_for_status()
        videos = [video["video_files"][0]["link"] for video in response.json().get("videos", [])]
    except Exception as e:
        st.error(f"Error fetching videos for '{clean_keyword}': {e}")
        videos = []

    return videos

def download_video(video_url, index, keyword):
    video_path = f"temp_video_{keyword}_{index}.mp4"
    try:
        response = requests.get(video_url)
        response.raise_for_status()
        with open(video_path, "wb") as f:
            f.write(response.content)
        return video_path
    except Exception as e:
        st.error(f"Error downloading video {video_url}: {e}")
        return None

def create_combined_compilation(video_urls, output_file):
    clips = []

    for idx, (video_url, keyword) in enumerate(video_urls):
        video_path = download_video(video_url, idx, keyword)
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
        st.error(f"No clips to compile.")

    # Clean up temporary files
    for idx in range(len(video_urls)):
        video_path = f"temp_video_{video_urls[idx][1]}_{idx}.mp4"
        if os.path.exists(video_path):
            os.remove(video_path)

# Streamlit app UI
st.title("Educational Script Generator")
st.write("Welcome")
st.write("Learn any topic easily")

# Input for the topic
topic = st.text_input("Enter the topic to learn")

# Slider for difficulty
difficulty = st.slider("Select 0 for easy and 1 for Hard", 0.0, 1.0, 0.0)

# Button to submit
submit = st.button("Submit")

if submit:
    if topic:
        st.write("Generating script, please wait...")

        difficulty_text = "easy" if difficulty < 0.5 else "hard"

        # Prompt construction
        prompt = f"Write a 1200-word educational script for a video that explains the topic of '{topic}' at a {difficulty_text} difficulty level. Use clear and engaging language suitable for teenagers. Include at least two real-life examples to illustrate key concepts. Ensure the explanation is concise and maintains the audience's interest throughout the script. After the script, provide a list of relevant keywords which can be used as input to another video generating API to create a video as background with the script as caption. List real-life examples separately which will serve as an input to another video generation api so make sure to generalize them. For example if velocity is a keyword then instead of only returning a single word velocity return a sentence like Plane flying in sky to demonstrate velocity"

        # Get the response from the Gemini model
        script = get_gemini_response(prompt)

        if script:
            # Extract script content and real-life examples
            examples = []

            # Attempt to find "Real-Life Examples:" section
            if "Real-Life Examples:" in script:
                parts = script.split("Real-Life Examples:")
                script_content = parts[0].strip()
                examples_part = parts[1].strip()
                examples = [example.strip() for example in examples_part.split("\n") if example.strip()]
            else:
                # Fallback if Real-Life Examples section is not found
                script_content = script
                st.warning("Real-Life Examples section not found. Attempting to extract examples from the script.")

                # Extract examples based on known patterns
                example_matches = re.findall(r'\bExample\b[^:]*:\s*(.*)', script, re.IGNORECASE)
                examples.extend([match.strip() for match in example_matches])

            st.write("Educational Script:\n", script_content)
            st.write("Real-Life Examples:\n", examples)

            # Process examples to get videos
            video_urls = []
            for example in examples:
                if len(example) > 2:
                    st.write(f"Processing example: {example}")

                    # Get one relevant video for each example
                    videos = get_videos(example)
                    if videos:
                        video_urls.append((videos[0], example))
                    else:
                        st.error(f"No videos found for '{example}'.")

            if video_urls:
                st.write("Creating a combined video compilation, please wait...")
                output_file = "combined_compilation.mp4"
                create_combined_compilation(video_urls, output_file)

                # Display the combined video compilation
                if os.path.exists(output_file):
                    st.write(f"### Combined Compilation Video")
                    st.video(output_file)
                else:
                    st.error("No combined video compilation found.")
            else:
                st.error("No videos found for the examples.")
        else:
            st.error("Failed to generate the script.")
    else:
        st.error("Please enter a topic.")