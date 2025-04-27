from openai import OpenAI
import openai
import json
# from create_captions import create_captions
import requests
from moviepy import *
import dotenv
import base64
import os
from create_captions import create_captions
import cv2
from create_thumbnail_from_video_add_quote import extract_frame

if not os.path.exists("./intermediate/image_gen"):
    os.makedirs("./intermediate/image_gen",exist_ok=True)
if not os.path.exists("./intermediate/tiktok"):
        os.makedirs("./intermediate/tiktok",exist_ok=True)

def image_generator(client, prompt, idx):
    
    result = client.images.generate(
        model="gpt-image-1",
        size = "1024x1536",
        prompt=prompt
    )

    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    
    with open(f"./intermediate/image_gen/{idx}.png", "wb") as f:
        f.write(image_bytes)

def crop_video(clip):  
    target_width = 600
    target_height = 945
    ratio = target_width/target_height


    crop_width = min(target_width, clip.w)   
    crop_height = min(target_height, clip.h)


    center_x = clip.w / 2

    center_y = clip.h / 2

    cc=clip.cropped(x_center=center_x,
                    y_center=center_y,
                    width=crop_width,
                    height=crop_height
                    )
    if clip.w < target_width or clip.h<target_height:
        target_width = 600
        target_height = 360
        crop_width = target_width# min(target_width, clip.w)   
        crop_height = target_height #min(target_height, clip.h)
    # Resize proportionally (preserve aspect ratio)
    # clip = clip.resized(height=target_height)
    # if clip.w > target_width:
    #     clip = clip.resized(width=target_width)

    clip = cc.resized((target_width, target_height))
    return clip

def crop_video(clip, smallest_dims):
    height = clip.h
    width = clip.w

    new_width = int(height * 600 / 945)
    
    center_x = clip.w / 2

    center_y = clip.h / 2

    cc=clip.cropped(x_center=center_x,
                    y_center=center_y,
                    width=new_width,
                    height=height
                    )
    #clip = cc.resized((target_width, target_height))
    if smallest_dims[0] > new_width:
        smallest_dims = (new_width, height)
    return cc, smallest_dims


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
            model="o4-mini",
            messages=messages,
        )
        
        # Save assistant reply
        assistant_reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_reply})
        
        
        data = json.loads(assistant_reply)
        output_list.append(data)
        if not os.path.exists("./intermediate/tiktokscript"):
            os.makedirs("./intermediate/tiktokscript")
       
        with open(f'./intermediate/tiktokscript/output_{idx}.json', 'w') as json_file:
            json.dump(data, json_file, indent=4)
    return output_list

def vid2croppedclip(clips, path, smallest_dims) -> list[VideoFileClip]:
    clips_out = []
    for c in clips:
        if c["index"]!=-1:
            try:
                filename = f"statement_{c['index']}_final.mp4"
                filepath = path +'/'+filename
                clip = VideoFileClip(filepath)
            except:
                filename = f"statement_{c['index']}_rough.mp4"
                filepath = path +'/'+filename
                clip = VideoFileClip(filepath)            
            # start = clips_times[c["index"]]["start"]
            # end = clips_times[c["index"]]["end"]            
            clip_final_sub, smallest_dims = crop_video(clip, smallest_dims)
            # clip_final_sub = clip_final_sub.subclipped(start, end) 
            clips_out.append(clip_final_sub)
    return clips_out, smallest_dims 

from  moviepy.video.fx import FadeOut

def concatenate_videos(clip_list, nameout, lenny_indices ,smallest_dims):

    effect= FadeOut(2)
    for idx, clip in enumerate(clip_list):
        clip_list[idx] = clip.resized(smallest_dims)
    for index in lenny_indices:
        clip_list[index] = effect.copy().apply(clip_list[index]) 
    clipfinal = concatenate_videoclips(clip_list)
    if ".mp4" in nameout:
        clipfinal.write_videofile(nameout,
                                   codec="libx264",
                                     fps=50,
                                     audio_codec="aac")
    else:
        print("Error, missing extension.")
    for c in clip_list:
        c.close()
    clipfinal.close()

def img2vid(image_path, duration, text, smallest_dims):
    if os.path.exists("tmp.mp3"):
        os.remove("tmp.mp3")
    text_to_speech(text)
    audio = AudioFileClip("tmp.mp3")
    # Get the duration in seconds
    duration = audio.duration
    clip = ImageClip(image_path)
    zoom_clip = clip.with_duration(duration)
    zoom_clip, smallest_dims = crop_video(zoom_clip, smallest_dims)
    zoom_clip = zoom_clip.with_audio(audio)
    return zoom_clip, smallest_dims

def text_to_speech(text, voice="nova", model="tts-1"):
    response = openai.audio.speech.create(
        model=model,
        voice=voice,
        input=text  # ← Just pass German text here
    )
    
    with open("tmp.mp3", "wb") as f:
        f.write(response.content)
    

    return response.content

def create_video_Topic(client,topic_path,topic_name):

    with open('./text_mining/tiktok_script_generation_prompt.txt', 'r') as f:
        system_text = f.read()

    with open(topic_path+topic_name+"/"+topic_name+".jsonl", 'r') as f:
        clips = json.load(f)
    summary=f"{clips['topic']}: {clips['explanation']}"
    output_lists = script_generator(client, system_text, clips["statements"], summary)


    #TODO: HERE ADD PAUL'S FUNCTION
    for idx, vids2gen in enumerate(output_lists[1]):
         image_generator(client, vids2gen["description"], idx) # Replace with Paul
        # image_generator(client, summary, idx) # Replace with Paul

    smallest_dims = (float("inf"), float("inf"))

    re_vids, smallest_dims = vid2croppedclip(output_lists[0], topic_path+topic_name, smallest_dims)

    # get_aiids(output_lists)
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
        # ai_vid = img2vid(f"./intermediate/image_gen/{idx}.png", dct["duration"], texts["narrator"])
        ai_vid, smallest_dims = img2vid(f"./intermediate/image_gen/{idx}.png", dct["duration"], texts["narrator"],smallest_dims)
        ai_vids.append(ai_vid)

    lenny_indices = []
    for idx, dct in enumerate(output_lists[0]):
        if dct["index"] != -1:
            vid = re_vids[c_re]
            c_re+=1
        else:
            vid = ai_vids[c_ai]
            c_ai+=1
            lenny_indices.append(idx)
        vids.append(vid)


    concatenate_videos(vids,f"./intermediate/tiktok/{topic_name}.mp4", lenny_indices,smallest_dims)
    captioned_video_path = create_captions(f"./intermediate/tiktok/{topic_name}.mp4", "./output/tiktok/")
    print("--- Caption Generation Successful ---")
    print(f"Output video saved to: {captioned_video_path}")

    extract_frame(topic_name,captioned_video_path, topic_path+topic_name+"/"+topic_name+".jsonl",client)
    # extracted_frame = extract_frame(captioned_video_path, topic_path+topic_name+"/"+topic_name+".jsonl",client)
    # output_filename = os.path.join("./output/tiktok/", f"{topic_name}_frame.jpg")

    # try:
    #     cv2.imwrite(output_filename, extracted_frame)
    #     print(f"Frame successfully saved as {output_filename}")
    # except Exception as e:
    #     print(f"Error saving frame: {e}")
    #     print("Failed to save frame.")


def create_all_videos(client,path: str, topics):
    print("Generating videos... ")
    for t in topics:
        print("Generating Topic video ",t)
        create_video_Topic(client,path,t)
    print("Thanks, now enjoy...")


if __name__ == "__main__":
    dotenv.load_dotenv()

    client = OpenAI()

    topics_dir = "./intermediate/shorts_draft/"

    for topic_name in os.listdir(topics_dir):
        if topic_name == '.DS_Store':
            continue
        create_video_Topic(client, topics_dir, topic_name)
