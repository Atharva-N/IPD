from flask import Flask, render_template, request, url_for, send_from_directory, send_file
from PIL import Image
from io import BytesIO
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import requests
import google.generativeai as genai
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Replace these with your actual API keys
UNSPLASH_API_KEY = "2oU_fkWIgXdcC7pvnQoksHJtWSTscfpP-TVBUyWzAww"
GENIE_API_KEY = "AIzaSyBzB-FbuQimtmUEoaXUwYdGoxUwTXvMO3I"
def is_similar_context(new_context, existing_contexts, similarity_threshold=0.6):
    """Check if the new context is too similar to existing contexts"""
    new_words = set(new_context.lower().split())
    for context in existing_contexts:
        existing_words = set(context.lower().split())
        intersection = len(new_words.intersection(existing_words))
        union = len(new_words.union(existing_words))
        if union == 0:
            continue
        similarity = intersection / union
        if similarity > similarity_threshold:
            return True
    return False
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
    script = script.replace("Introduction", "Introduction\n")
    script = script.replace("Definition", "Definition\n")
    script = script.replace("Real-Life Examples", "Real-Life Examples\n")
    script = script.replace("Formula and Sum", "Formula and Sum\n")
    script = script.replace("1.","")
    script = script.replace("2.","")
    script = script.replace("3.","")
    script = script.replace("4.","")
    script = script.replace("5.","")
    script = script.replace("6.","")
    script = script.replace("7.","")
    script = script.replace("8.","")
    script = script.replace("9.","")
    script = script.replace("10.","")
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
        Provide a brief, one-line visual which is easily photographable readily available for the above description.
        Ensure it is stictly related to {group} ALWAYS.
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
        ex: ML Algorithms.
        Ball thrown from building.
        Swinging Pendulum.
        People in Queue.
        """
    context = get_gemini_response(context_prompt).strip()
    while is_similar_context(context, existing_contexts, 0.6):
        context = get_gemini_response(context_prompt).strip()
    return context.replace('"', '').replace("'", '').split('\n')[0]

def fetch_image_from_unsplash(query):
    # url = "https://api.unsplash.com/search/photos"
    # headers = {
    #     "Authorization": f"Client-ID {UNSPLASH_API_KEY}",
    # }
    # params = {
    #     "query": query,
    #     "per_page": 1,
    #     "orientation": "landscape"
    # }
    
    # try:
    #     response = requests.get(url, headers=headers, params=params)
    #     response.raise_for_status()
    #     data = response.json()
        
    #     if data['results']:
    #         return data['results'][0]['urls']['regular']
    #     else:
    #         app.logger.warning(f"No images found for query: {query}")
    #         return None
    # except Exception as e:
    #     app.logger.error(f"Error fetching image from Unsplash for '{query}': {str(e)}")
    #     return None
    # PEXELS_API_KEY = "Y1t6RmtPK7um7a165YSVk0hASGXHwVhuY67Qq7pOIe6Kr7skdZnBF68D"
    # PEXELS_API_URL = "https://api.pexels.com/v1/search"
    # headers = {"Authorization": PEXELS_API_KEY}
    # params = {"query": query, "per_page": 1}
    # response = requests.get(PEXELS_API_URL, headers=headers, params=params)
    # if response.status_code == 200:
    #     photos = response.json().get('photos', [])
    #     if photos:
    #         return photos[0]['src']['large']
    # print(f"Failed to fetch image for query: {query}. Error: {response.status_code}")
    # return None
    GOOGLE_API_KEY = "AIzaSyCT6MlLUxY0GvRrYLYCpBTyIWOnBqhmNDw"
    GOOGLE_CSE_ID = "92732cfef429a46b9"
    GOOGLE_API_URL = "https://www.googleapis.com/customsearch/v1"
    headers = {}
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "searchType": "image",
        "per_page": 1  # Matches your original code's per_page parameter
    }
    
    response = requests.get(GOOGLE_API_URL, headers=headers, params=params)
    
    if response.status_code == 200:
        photos = response.json().get('items', [])
        if photos:
            return photos[0]['link']
    
    print(f"Failed to fetch image for query: {query}. Error: {response.status_code}")
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home.html', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        topic = request.form.get('topic')
        difficulty = float(request.form.get('difficulty', 0.5))
        level = "easy"
        experience = "new"
        if difficulty > 0.5:
            level = "hard"
            experience = "high"
        if not topic:
            return render_template('home.html', error="Please enter a topic.")

        # Generate the script using your prompt
        prompt = f"""
        Please write a detailed educational script about {topic}. The script should be structured with the following sections:
        1. **Introduction:- **: Provide the basic idea in 12 lines, divided into 3 sections of 4 sentences each. 200 words MINUIMUM for each section. END EACH SECTION BY USING -x-x-x-x-x(Section 1 introduce any related concepts to {topic}. Here in simple words we are introduced to the basic concepts of {topic}. We then go in detail to learn in detail. In section 3, explain its relevance and importance in daily life.)

        2. **Definition:- **: A clear, concise definition in 3 lines and only one section. END EACH SECTION BY USING -x-x-x-x-x. 100 words per section MINUIMUM.(In This section in 3 lines give the scientific as well as mathematical definition of the concept.)

        3. **Real-Life Examples:- **: Describe real-life applications or examples in 6 lines, divided into 3 sections of 2 sentences each. 50 words per section MINUIMUM. END EACH SECTION BY USING -x-x-x-x-x(In each of 3 sections, first, mention the application/real life use and in second line Explain how {topic} is used in this example.)

        4. **Formula and Sum:- **: If applicable, explain the formula or sum in 2 lines. END EACH SECTION BY USING -x-x-x-x-x(100 words)

        Do not include any additional word such as sections.
        DO NOT USE SHORTCUTS.
        Explain it from basics.
        ALWAYS INCLUDE ALL SECTIONS.
        ALWAYS MAKE SURE YOU MEET THE MINUIMUM NUMBER OF SENTENCES.
        Make sure that the script is {level} as user experience is {experience}
        """
        
        script = get_gemini_response(prompt)
        if not script:
            return render_template('home.html', error="Failed to generate the script.")

        # Clean and group the script
        cleaned_script = clean_script(script)
        grouped_script = group_sentences(cleaned_script)

        # Lists to store paths
        all_imgs = []
        all_audios = []
        all_contexts = []
        # Generate contexts and create video segments
        for idx, group in enumerate(grouped_script):
            # Generate unique context
            context = generate_unique_context(group, all_contexts, topic)
            all_contexts.append(context)
            app.logger.info(f"Group {idx + 1}: {group}")
            app.logger.info(f"Generated Context for Group {idx + 1}: {context}")
            # Fetch image
            image_url = fetch_image_from_unsplash(context)
            
            if image_url:
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
                    app.logger.error(f"Error processing segment {idx}: {str(e)}")

        # Create final video
        video_url = None
        if all_imgs and all_audios:
            try:
                output_file = os.path.join(app.static_folder, f"educational_video_{topic.replace(' ', '_')}.mp4")
                
                video_clips = []
                for img_path, audio_path in zip(all_imgs, all_audios):
                    image_clip = ImageClip(img_path)
                    audio_clip = AudioFileClip(audio_path)
                    video_clip = image_clip.set_duration(audio_clip.duration)
                    video_clip = video_clip.set_audio(audio_clip)
                    video_clips.append(video_clip)

                final_video = concatenate_videoclips(video_clips, method="compose")
                final_video.write_videofile(
                    output_file,
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
                
                video_url = url_for('static', filename=f"educational_video_{topic.replace(' ', '_')}.mp4")
                
            except Exception as e:
                app.logger.error(f"Error creating final video: {str(e)}")
            
            # Clean up temporary files
            for path in all_imgs + all_audios:
                if os.path.exists(path):
                    os.remove(path)

        # Format the script sections for display
        formatted_sections = []
        section_titles = ["Introduction:- ", "Definition:- ", "Real-Life Examples:- ", "Formula and Sum:- "]
        current_section = 0
        current_group = []
        
        for group in grouped_script:
            current_group.append(group)
            if len(current_group) >= 3 and current_section == 0:  # Introduction has 3 parts
                formatted_sections.append(("Introduction", current_group[:]))
                current_group = []
                current_section += 1
            elif len(current_group) >= 1 and current_section == 1:  # Definition has 1 part
                formatted_sections.append(("Definition", current_group[:]))
                current_group = []
                current_section += 1
            elif len(current_group) >= 3 and current_section == 2:  # Examples have 3 parts
                formatted_sections.append(("Real-Life Examples", current_group[:]))
                current_group = []
                current_section += 1
            elif current_group and current_section == 3:  # Formula section
                formatted_sections.append(("Formula and Sum", current_group[:]))
                current_group = []

        return render_template('home.html', 
                            formatted_sections=formatted_sections,
                            video_url=video_url, show_script=True, grouped_script=grouped_script, script = cleaned_script)

    return render_template('home.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)