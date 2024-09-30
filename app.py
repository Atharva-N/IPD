from flask import Flask, render_template, request, url_for, send_from_directory, send_file
from moviepy.editor import VideoFileClip, concatenate_videoclips
import requests
import google.generativeai as genai
import os
import re
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

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
        app.logger.error(f"Error in get_gemini_response: {str(e)}")
        return None

def sanitize_keyword(keyword):
    return re.sub(r'[^\w\s]', '', keyword).strip()

def get_videos(keyword, num_results=1):
    headers = {"Authorization": PEXELS_API_KEY}
    clean_keyword = sanitize_keyword(keyword)
    videos_url = "https://api.pexels.com/videos/search"
    params = {"query": clean_keyword, "per_page": num_results}
    try:
        response = requests.get(videos_url, headers=headers, params=params)
        response.raise_for_status()
        videos = [video["video_files"][0]["link"] for video in response.json().get("videos", [])]
        app.logger.debug(f"Retrieved videos for '{clean_keyword}': {videos}")
        return videos
    except Exception as e:
        app.logger.error(f"Error in get_videos for '{clean_keyword}': {str(e)}")
        return []

def download_video(video_url, index):
    video_path = f"temp_video_{index}.mp4"
    try:
        response = requests.get(video_url)
        response.raise_for_status()
        with open(video_path, "wb") as f:
            f.write(response.content)
        app.logger.debug(f"Downloaded video to {video_path}")
        return video_path
    except Exception as e:
        app.logger.error(f"Error downloading video {video_url}: {str(e)}")
        return None

def create_combined_compilation(video_urls, output_file):
    clips = []

    for idx, video_url in enumerate(video_urls):
        video_path = download_video(video_url, idx)
        if video_path:
            try:
                video_clip = VideoFileClip(video_path)
                clips.append(video_clip)
                app.logger.debug(f"Added video clip {idx} to compilation")
            except Exception as e:
                app.logger.error(f"Error processing video {idx}: {str(e)}")
                continue

    if clips:
        try:
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(output_file, fps=24)
            app.logger.info(f"Video compilation saved to {output_file}")
        except Exception as e:
            app.logger.error(f"Error creating video compilation: {str(e)}")
            return None
    else:
        app.logger.warning("No clips to compile into video")
        return None
    
    # Clean up temporary files
    for idx in range(len(video_urls)):
        video_path = f"temp_video_{idx}.mp4"
        if os.path.exists(video_path):
            os.remove(video_path)
            app.logger.debug(f"Removed temporary file {video_path}")
    
    return output_file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home.html', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        topic = request.form.get('topic')
        difficulty = float(request.form.get('difficulty', 0.5))
        
        if not topic:
            return render_template('home.html', error="Please enter a topic.")

        difficulty_text = "easy" if difficulty < 0.5 else "hard"
        prompt = f"Write a 1200-word educational script for a video that explains the topic of '{topic}' at a {difficulty_text} difficulty level. Use clear and engaging language suitable for teenagers. Include at least two real-life examples to illustrate key concepts. Ensure the explanation is concise and maintains the audience's interest throughout the script. After the script, provide a list of relevant keywords which can be used as input to another video generating API to create a video as background with the script as caption. List real-life examples separately which will serve as an input to another video generation api so make sure to generalize them."
        
        script = get_gemini_response(prompt)

        if not script:
            return render_template('home.html', error="Failed to generate the script.")

        examples = []
        if "Real-Life Examples:" in script:
            parts = script.split("Real-Life Examples:")
            script_content = parts[0].strip()
            examples_part = parts[1].strip()
            examples = [example.strip() for example in examples_part.split("\n") if example.strip()]
        else:
            script_content = script
            examples = re.findall(r'\bExample\b[^:]*:\s*(.*)', script, re.IGNORECASE)

        video_urls = []
        for example in examples:
            videos = get_videos(example)
            if videos:
                video_urls.append(videos[0])

        video_url = None
        if video_urls:
            output_file = os.path.join(app.static_folder, f"combined_compilation_{topic.replace(' ', '_')}.mp4")
            if create_combined_compilation(video_urls, output_file):
                video_url = url_for('static', filename=f"combined_compilation_{topic.replace(' ', '_')}.mp4")

        return render_template('home.html', script_content=script_content, examples=examples, video_url=video_url)

    return render_template('home.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)