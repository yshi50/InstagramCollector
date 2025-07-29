import os
import json
import requests
import time
import random
import unicodedata
import sys
from dotenv import load_dotenv
from instagrapi import Client
from datetime import datetime

load_dotenv()
username = os.getenv("username")
password = os.getenv("password")
webhook = os.getenv("webhook")
session_file = "session.json"
json_file = "targets.json"

cl = Client()
cl.delay_range = [0, 5]

def notify(msg):
    data = {
        "content": msg
    }
    try:
        response = requests.post(webhook, json=data)
        response.raise_for_status()
        print("Discord Notification Sent")
    except Exception as e:
        print(f"Failed to Send Discord Notification: {e}")

def termination():
    if webhook:
        notify("Program Stopped")
    sys.exit(1)

def safe_delay(min_s=15, max_s=30):
    delay = random.uniform(min_s, max_s)
    print(f"Safe Delay: {delay:.2f} Seconds")
    time.sleep(delay)

def login():
    if os.path.exists(session_file):
        try:
            cl.load_settings(session_file)
            cl.login(username, password)
            print("Session Loaded Successfully")
            return
        except Exception as e:
            print(f"Failed to Load Session: {e}")
            termination()
    else:
        try:
            cl.login(username, password)
            cl.dump_settings(session_file)
            print("Logged in and Session Saved")
        except Exception as e:
            print(f"Failed to Login: {e}")
            termination()

def should_skip_file(filename):
    if os.path.exists(filename):
        print(f"Skipped (Already Exists): {filename}")
        return True
    return False

def download_file(url, filename, use_headers=False):
    if not url:
        print(f"Skipping Download, URL is None for {filename}")
        return
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        } if use_headers else {}

        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"Error Downloading {filename}: {e}")
        termination()

def sanitize_filename(name):
    result = []
    for char in name:
        if char.isalnum() or char in " _-":
            result.append(char)
        else:
            try:
                description = unicodedata.name(char).lower().replace(" ", "_")
                result.append(f"[{description}]")
            except ValueError:
                result.append(f"[U+{ord(char):04X}]")
    return "".join(result).strip()

def download_highlights(username):
    user_id = cl.user_id_from_username(username)
    safe_delay()
    try:
        highlights = cl.user_highlights(user_id)
        print(f"Fetched {len(highlights)} Highlights")
        if not highlights:
            print("No Highlights Found")
            return
    except Exception as e:
        print(f"Error Fetching Highlights for {username}: {e}")
        termination()

    base_folder = os.path.join(os.path.dirname(__file__), "data", username, "highlights")
    os.makedirs(base_folder, exist_ok=True)

    for index, highlight in enumerate(highlights):
        highlight_name = highlight.title.strip() if highlight.title else f"highlight_{index+1}"
        highlight_name = sanitize_filename(highlight_name)
        highlight_folder = os.path.join(base_folder, highlight_name)
        os.makedirs(highlight_folder, exist_ok=True)

        print(f"\nProcessing Highlight: {highlight.title} ({highlight.id})")
        highlight_id_numeric = highlight.id.split(":")[-1]

        try:
            highlight_items = cl.highlight_info(highlight_id_numeric).items
            print(f"Highlight {highlight.id} Contains {len(highlight_items)} Stories")
        except Exception as e:
            print(f"Error Fetching Stories for Highlight {highlight.id}: {e}")
            termination()

        for i, item in enumerate(highlight_items):
            timestamp = item.taken_at.strftime("%Y-%m-%d_%H-%M-%S")
            media_url = item.video_url if item.video_url else item.thumbnail_url
            ext = ".mp4" if item.video_url else ".jpg"
            filename = os.path.join(highlight_folder, f"{timestamp}{ext}")

            if not media_url or should_skip_file(filename):
                continue

            download_file(media_url, filename, use_headers=True)
            safe_delay()

def download_posts(username):
    save_folder = os.path.join(os.path.dirname(__file__), "data", username, "posts")
    safe_delay()
    user_id = cl.user_id_from_username(username)
    safe_delay()

    try:
        posts = [m for m in cl.user_medias(user_id) if m.media_type != 2]
    except KeyError as e:
        print(f"KeyError Encountered: {e}")
        posts = []

    if not posts:
        print(f"No Posts Found for {username}")
        return

    os.makedirs(save_folder, exist_ok=True)

    for post in posts:
        timestamp = post.taken_at.strftime("%Y-%m-%d_%H-%M-%S")

        if post.media_type == 1:
            media_url = post.thumbnail_url or post.image_versions2['candidates'][0]['url']
            ext = ".jpg"
            filename = os.path.join(save_folder, f"{timestamp}{ext}")
            if should_skip_file(filename):
                continue
            download_file(media_url, filename)
            safe_delay()

        elif post.media_type == 8:
            for media_index, resource in enumerate(post.resources, start=1):
                timestamp = (getattr(resource, "taken_at", post.taken_at)).strftime("%Y-%m-%d_%H-%M-%S")
                ext = ".mp4" if resource.video_url else ".jpg"
                media_url = resource.video_url if ext == ".mp4" else resource.thumbnail_url
                filename = os.path.join(save_folder, f"{timestamp}_{media_index}{ext}")
                if should_skip_file(filename):
                    continue
                download_file(media_url, filename)
                safe_delay()

def download_stories(username):
    save_folder = os.path.join(os.path.dirname(__file__), "data", username, "stories")
    os.makedirs(save_folder, exist_ok=True)

    try:
        user_id = cl.user_id_from_username(username)
        safe_delay()
        stories = cl.user_stories(user_id)
    except Exception as e:
        print(f"Error Fetching Stories for {username}: {e}")
        termination()

    if not stories:
        print(f"No Stories Found for {username}")
        return

    print(f"Found {len(stories)} Stories for {username}")

    for index, story in enumerate(stories, start=1):
        timestamp = story.taken_at.strftime("%Y-%m-%d_%H-%M-%S")
        ext = ".mp4" if story.media_type == 2 else ".jpg"
        media_url = story.video_url if ext == ".mp4" else story.thumbnail_url
        filename = os.path.join(save_folder, f"{timestamp}{ext}")
        if not media_url or should_skip_file(filename):
            continue
        download_file(media_url, filename, use_headers=True)
        safe_delay()

def download_reels(username):
    save_folder = os.path.join(os.path.dirname(__file__), "data", username, "reels")
    os.makedirs(save_folder, exist_ok=True)

    try:
        user_id = cl.user_id_from_username(username)
        safe_delay()
        reels = cl.user_clips(user_id, amount=0)
    except Exception as e:
        print(f"Error Fetching Reels for {username}: {e}")
        termination()

    print(f"Total Reels to Download for {username}: {len(reels)}")

    for idx, reel in enumerate(reels, start=1):
        media_url = reel.video_url
        if not media_url:
            print(f"Skipping Reel {idx}, No Video URL Found")
            continue

        timestamp = reel.taken_at.strftime("%Y-%m-%d_%H-%M-%S")
        ext = ".mp4"
        filename = os.path.join(save_folder, f"{timestamp}{ext}")

        if should_skip_file(filename):
            continue

        download_file(media_url, filename)
        safe_delay()

def main():
    print("0: Download All (Posts + Highlights + Stories + Reels)")
    print("1: Download Only Posts")
    print("2: Download Only Highlights")
    print("3: Download Only Stories")
    print("4: Download Only Reels")
    choice = input("Choose: ").strip()

    print("1: Update Existing from targets.json")
    print("2: Download Single User")
    sub_choice = input("Sub-Menu Choose: ").strip()

    if sub_choice == "1":
        if not os.path.exists(json_file):
            print(f"{json_file} Not Found")
            return
        with open(json_file, "r", encoding="utf-8") as f:
            user_list = json.load(f)
        for user in user_list:
            if choice in ("0", "1"):
                download_posts(user)
            if choice in ("0", "2"):
                download_highlights(user)
            if choice in ("0", "3"):
                download_stories(user)
            if choice in ("0", "4"):
                download_reels(user)
            safe_delay(50, 70)

    elif sub_choice == "2":
        user_list = []
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                user_list = json.load(f)
            print("\nSelect Target:")
            for idx, name in enumerate(user_list):
                print(f"{idx + 1}. {name}")

        raw_input_val = input("Input: ").strip()

        if raw_input_val.isdigit():
            idx = int(raw_input_val) - 1
            if 0 <= idx < len(user_list):
                target = user_list[idx]
            else:
                print("Invalid Number")
                return
        else:
            target = raw_input_val

        if choice in ("0", "1"):
            download_posts(target)
        if choice in ("0", "2"):
            download_highlights(target)
        if choice in ("0", "3"):
            download_stories(target)
        if choice in ("0", "4"):
            download_reels(target)
    else:
        print("Invalid Sub-Choice")

if __name__ == "__main__":
    login()
    main()
    if webhook:
        notify("Program Finished")