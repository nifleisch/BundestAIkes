import dotenv
from openai import OpenAI
import os
from video_processing.blue_box import create_video_Topic

dotenv.load_dotenv()

client = OpenAI()

topics_dir = "./intermediate/shorts_draft/"

for topic_name in os.listdir(topics_dir):
    if topic_name == '.DS_Store':
        continue
    create_video_Topic(client, topics_dir, topic_name)
