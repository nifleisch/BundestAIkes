from openai import OpenAI
import openai
import json
import requests
from moviepy import *

def crop_video(clip):
    target_width = 600
    target_height = 945
    center_x = clip.w / 2

    center_y = clip.h / 2
    crop_width = min(target_width, clip.w)   

    crop_height = min(target_height, clip.h)

    cc=clip.cropped(x_center=center_x,
                    y_center=center_y,
                    width=crop_width,
                    height=crop_height
                    )
    clip = cc.resized((target_width, target_height))
    return clip

def script_generator(client, system_text, clips, summary):
    output_list = []
    # Initialize the conversation
    messages = [{"role": "system", "content": system_text}]

    # Define user prompts in order
    user_prompts = [
        f"Here is the session summary:{summary} and here are the clips: {clips}",
        "Now, based on the script you just generated, please:\n"
        "- Provide in-depth descriptions of images for each section where there will not be clips and only the narrator (for generating them using dall-e) in json format, similar to the one you got with the clips (duration and description)"
        "Please ONLY reply with a valid JSON array or object, without any explanations, markdown formatting, or extra text."
    ] #"- Suggest relevant hashtags that describe the video content\n"

    # Loop through each user prompt
    for idx, prompt in enumerate(user_prompts):
        # Add user message
        messages.append({"role": "user", "content": prompt})
        
        # Get assistant response
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            temperature=0.5,
            max_tokens=1000
        )
        
        # Save assistant reply
        assistant_reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_reply})
        
        
        data = json.loads(assistant_reply)
        output_list.append(data)
        with open(f'./data/output/output_{idx}.json', 'w') as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Succesful reply {idx}")
    return output_list

#TODO: REPLACE WITH PAUL
def image_generator(client, prompt, idx):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )

    # Step 2: Get the URL
    image_url = response.data[0].url

    # Step 3: Download the image
    image_data = requests.get(image_url).content

    # Step 4: Save the image
    with open(f"./data/output/{idx}.png", "wb") as f:
        f.write(image_data)

    #print("Image successfully saved as 'generated_image.png'!")

#NOTE: NOT NEEDED SINCE WE GET CLIPS, WE JUST HAVE TO CROP NILS CLIPS
def vid2croppedclip(clips, clips_times, path) -> list[VideoFileClip]:
    clips_out = []
    clip = VideoFileClip(path)
    for c in clips:
        if c["index"]!=-1:
            start = clips_times[c["index"]]["start"]
            end = clips_times[c["index"]]["end"]            
            clip_final_sub = crop_video(clip)
            clip_final_sub = clip_final_sub.subclipped(start, end) 
            clips_out.append(clip_final_sub)
    return clips_out

def concatenate_videos(clip_list, nameout):
    clipfinal = concatenate_videoclips(clip_list)
    if ".mp4" in nameout:
        clipfinal.write_videofile(nameout,
                                   codec="libx264",
                                     fps=50)
    else:
        print("Error, missing extension.")
    for c in clip_list:
        c.close()
    clipfinal.close()

def img2vid(image_path, duration, text):
    text_to_speech(text)
    audio = AudioFileClip("tmp.mp3")
    clip = ImageClip(image_path)
    zoom_clip = clip.with_duration(duration)
    zoom_clip = crop_video(zoom_clip)
    audio = audio.subclipped(0, zoom_clip.duration)
    zoom_clip = zoom_clip.with_audio(audio)
    return zoom_clip

def text_to_speech(text, voice="nova", model="tts-1"):
    response = openai.audio.speech.create(
        model=model,
        voice=voice,
        input=text  # ← Just pass German text here
    )
    
    with open("tmp.mp3", "wb") as f:
        f.write(response.content)
    

    return response.content


if __name__ == "__main__":
    client = OpenAI()

    # Read system prompt
    with open('./data/system/prompt.txt', 'r') as f:
        system_text = f.read()

    # Read clips
    with open('./data/user/clips.json', 'r') as f:
        clips = json.load(f)

    # Read markdown
    with open('./data/user/summary.md', 'r') as f:
        summary = f.read()
    
    output_lists = script_generator(client, system_text, clips, summary)

    #TODO: HERE ADD PAUL'S FUNCTION
    #for idx, vids2gen in enumerate(output_lists[1]):
    #    image_generator(client, vids2gen["description"], idx) # Replace with Paul
    
    #TODO: REPLACE WITH NILS VIDEOS
    re_vids = vid2croppedclip(output_lists[0], clips, "./data/input/video.mp4")
    

    ai_vids = []
    vids = []
    c_ai = 0
    c_re = 0

    for idx, dct in enumerate(output_lists[1]):
        counter = 0
        for texts in output_lists[0]:
            if texts["index"] ==-1:
                if idx == counter:
                    break
                counter+=1
        print(texts["narrator"])
        ai_vid = img2vid(f"./data/output/{idx}.png", dct["duration"], texts["narrator"])
        ai_vids.append(ai_vid)

    for dct in output_lists[0]:
        if dct["index"] != -1:
            vid = re_vids[c_re]
            c_re+=1
        else:
            vid = ai_vids[c_ai]
            c_ai+=1
        vids.append(vid)
    
    concatenate_videos(vids,"./data/output/tiktok.mp4")