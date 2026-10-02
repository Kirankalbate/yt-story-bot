"""Story-page photos -> OCR -> voice-over -> video -> YouTube upload.

Layout:  stories/<story-name>/1.jpg 2.jpg ...  (+ optional title.txt, description.txt)
Each run uploads ONE new story folder (the next one not in state.json).
"""
import asyncio, json, os, pathlib, subprocess, sys

import edge_tts
import pytesseract
from PIL import Image

ROOT = pathlib.Path(__file__).parent
STORIES, OUT, STATE = ROOT / "stories", ROOT / "out", ROOT / "state.json"
VOICE = os.getenv("TTS_VOICE", "hi-IN-SwaraNeural")   # pa-IN voices: none; use hi-IN or en-IN
OCR_LANG = os.getenv("OCR_LANG", "hin+eng")           # add +pan for Punjabi
PRIVACY = os.getenv("PRIVACY", "private")             # private / unlisted / public
CHANNEL_TAG = os.getenv("TITLE_SUFFIX", " | Hasti Duniya")


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ocr(img_path):
    text = pytesseract.image_to_string(Image.open(img_path), lang=OCR_LANG)
    return " ".join(text.split())


async def tts(text, out):
    await edge_tts.Communicate(text, VOICE).save(str(out))


def make_clip(img, audio, out):
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,format=yuv420p")
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", "5", "-i", str(img), "-i", str(audio),
         "-vf", vf, "-c:v", "libx264", "-tune", "stillimage", "-r", "5",
         "-c:a", "aac", "-ar", "44100", "-shortest", str(out)])


def build_video(story_dir):
    work = OUT / story_dir.name
    work.mkdir(parents=True, exist_ok=True)
    imgs = sorted(p for p in story_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not imgs:
        raise SystemExit(f"No images in {story_dir}")
    clips, full_text = [], []
    for i, img in enumerate(imgs):
        text = ocr(img)
        full_text.append(text)
        if len(text) < 20:  # blank / cover page: show 3s of silence
            audio = work / f"{i}.mp3"
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                 "-t", "3", str(audio)])
        else:
            audio = work / f"{i}.mp3"
            asyncio.run(tts(text, audio))
        clip = work / f"{i}.mp4"
        make_clip(img, audio, clip)
        clips.append(clip)
    listfile = work / "list.txt"
    listfile.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    final = work / "final.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(final)])
    return final, " ".join(full_text)


def upload(video, title, desc):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    yt = build("youtube", "v3", credentials=creds)
    body = {"snippet": {"title": title[:100], "description": desc[:4900],
                        "categoryId": "22", "tags": ["story", "Hasti Duniya", "Nirankari"]},
            "status": {"privacyStatus": PRIVACY, "selfDeclaredMadeForKids": False}}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def main():
    done = json.loads(STATE.read_text()) if STATE.exists() else []
    todo = [d for d in sorted(STORIES.iterdir()) if d.is_dir() and d.name not in done]
    if not todo:
        print("Nothing new to upload."); return
    story = todo[0]
    video, text = build_video(story)
    tfile, dfile = story / "title.txt", story / "description.txt"
    title = (tfile.read_text().strip() if tfile.exists() else story.name.replace("-", " ")) + CHANNEL_TAG
    desc = dfile.read_text().strip() if dfile.exists() else text[:600]
    vid = upload(video, title, desc)
    done.append(story.name)
    STATE.write_text(json.dumps(done, indent=2))
    print("Uploaded:", f"https://youtu.be/{vid}")


if __name__ == "__main__":
    sys.exit(main())
