import streamlit as st
import requests
from PIL import Image
from io import BytesIO
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Your existing API keys
UNSPLASH_API_KEY = "2oU_fkWIgXdcC7pvnQoksHJtWSTscfpP-TVBUyWzAww"
GENIE_API_KEY = "AIzaSyBzB-FbuQimtmUEoaXUwYdGoxUwTXvMO3I"

# Using all your original functions
def get_gemini_response(question):
    headers = {'Content-Type': 'application/json', 'x-goog-api-key': GENIE_API_KEY}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": question}
                ]
            }
        ]
    }
    response = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent", json=data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    else:
        return f"Error: {response.status_code}, {response.text}"

def clean_script(script):
    script = script.replace("**", "")
    script = script.replace("##", "")
    script = script.replace("*", "")
    script = script.replace("\n", "")
    return script

def group_sentences(script):
    grouped_sentences = [group.strip() for group in script.split("-x-x-x-x-x") if group.strip()]
    print("Grouped Sentences:", grouped_sentences)
    return grouped_sentences

def generate_unique_context(group, existing_contexts, topic):
    context_prompt = f"""
    IT SHOULD NEVER BE EMPTY. ALWAYS FOLLOW THIS RULE.
    Given the following description: {group}
    Provide a brief, one-line visual for the above description.
    Ensure it is strictly related to {group} ALWAYS.
    Its image has to be readily available.
    Make it as short as possible. ex: Swinging Pendulum
    Make sure it is strictly related to {topic}
    - Must be a real, photographable scene
    - Should be specific and detailed
    - Avoid abstract concepts
    - Focus on everyday situations
    - Must be different from: {', '.join(existing_contexts)}
    Example format: "Student studying".
    MAKE IT AS CONCISE preferrable in 3-5 words.
    """
    context = get_gemini_response(context_prompt).strip()
    return context.replace('"', '').replace("'", '').split('\n')[0]

def fetch_image_from_unsplash(query):
    url = "https://api.unsplash.com/search/photos"
    headers = {
        "Authorization": f"Client-ID {UNSPLASH_API_KEY}",
    }
    params = {
        "query": query,
        "per_page": 1,
        "orientation": "landscape"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['results']:
            return data['results'][0]['urls']['regular']
        else:
            st.warning(f"No images found for query: {query}")
            return None
    except Exception as e:
        st.error(f"Error fetching image from Unsplash for '{query}': {str(e)}")
        return None

# Streamlit app
st.title("Educational Video Generator")

# Input section
topic = st.text_input("Enter a topic:", "")
difficulty = st.slider("Select difficulty level:", 0.0, 1.0, 0.5)

if st.button("Generate Video"):
    if topic:
        st.info("Generating educational content...")
        
        # Generate the script using your prompt
        prompt = f"""
        Please write a detailed educational script about {topic}. The script should be structured with the following sections:
        1. **Introduction**: Provide the basic idea in 12 lines, divided into 3 sections of 4 sentences each. 200 words minimum for each section. END EACH SECTION BY USING -x-x-x-x-x(Section 1 introduce any related concepts to {topic}. Here in simple words we are introduced to the basic concepts of {topic}. We then go in detail to learn in detail. In section 3, explain its relevance and importance in daily life.)

        2. **Definition**: A clear, concise definition in 3 lines and only one section. END EACH SECTION BY USING -x-x-x-x-x. 100 words per section.(In This section in 3 lines give the scientific as well as mathematical definition of the concept.)

        3. **Real-Life Examples**: Describe real-life applications or examples in 6 lines, divided into 3 sections of 2 sentences each. 50 words per section. END EACH SECTION BY USING -x-x-x-x-x(In each of 3 sections, first, mention the application/real life use and in second line Explain how {topic} is used in this example.)

        4. **Formula and Sum**: If applicable, explain the formula or sum in 2 lines. END EACH SECTION BY USING -x-x-x-x-x(100 words)

        Do not include any additional word such as sections.
        Explain it from basics.
        """
        
        script = get_gemini_response(prompt)
        
        if script:
            # Clean and group the script
            cleaned_script = clean_script(script)
            grouped_script = group_sentences(cleaned_script)
            
            # Progress bar
            progress_bar = st.progress(0)
            
            # Lists to store paths
            all_imgs = []
            all_audios = []
            
            # Generate contexts and create video segments
            for idx, group in enumerate(grouped_script):
                progress = (idx + 1) / len(grouped_script)
                progress_bar.progress(progress)
                
                # Generate unique context
                context = generate_unique_context(group, [], topic)
                
                # Fetch image
                image_url = fetch_image_from_unsplash(context)
                
                if image_url:
                    # Create video segment
                    try:
                        # Download and process the image
                        response = requests.get(image_url)
                        img = Image.open(BytesIO(response.content))
                        
                        if img.mode != 'RGB':
                            img = img.convert('RGB')

                        # Resize image
                        target_height = 720
                        aspect_ratio = img.width / img.height
                        target_width = int(target_height * aspect_ratio)
                        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                        
                        # Save temporary image
                        temp_image_path = f"temp_image_{idx}.jpg"
                        img.save(temp_image_path)
                        all_imgs.append(temp_image_path)
                        
                        # Generate audio
                        temp_audio_path = f"temp_audio_{idx}.mp3"
                        tts = gTTS(text=group, lang='en', tld='co.in')
                        tts.save(temp_audio_path)
                        all_audios.append(temp_audio_path)
                        
                    except Exception as e:
                        st.error(f"Error processing segment {idx}: {str(e)}")

            # Create final video
            if all_imgs and all_audios:
                try:
                    st.info("Creating final video...")
                    output_path = "final_video.mp4"
                    
                    video_clips = []
                    for img_path, audio_path in zip(all_imgs, all_audios):
                        image_clip = ImageClip(img_path)
                        audio_clip = AudioFileClip(audio_path)
                        video_clip = image_clip.set_duration(audio_clip.duration)
                        video_clip = video_clip.set_audio(audio_clip)
                        video_clips.append(video_clip)

                    final_video = concatenate_videoclips(video_clips, method="compose")
                    final_video.write_videofile(
                        output_path,
                        codec="libx264",
                        audio_codec="aac",
                        fps=24,
                        threads=4,
                        preset='ultrafast',
                        ffmpeg_params=["-strict", "-2"]
                    )
                    
                    # Clean up
                    final_video.close()
                    for clip in video_clips:
                        clip.close()
                        
                    # Provide download link
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="Download Video",
                            data=file,
                            file_name="educational_video.mp4",
                            mime="video/mp4"
                        )
                        
                except Exception as e:
                    st.error(f"Error creating final video: {str(e)}")
                
                # Clean up temporary files
                for path in all_imgs + all_audios:
                    if os.path.exists(path):
                        os.remove(path)
                
                if os.path.exists(output_path):
                    os.remove(output_path)
                    
        else:
            st.error("Failed to generate script. Please try again.")
    else:
        st.warning("Please enter a topic.")