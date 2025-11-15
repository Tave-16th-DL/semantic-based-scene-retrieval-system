from pathlib import Path
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg
from scenedetect.scene_manager import save_images

drive_base = Path('/content/drive/MyDrive/TAVE 16th/data/split_scenes')  # 드라이브에 보존
clip_dir   = drive_base / 'clips'
thumb_dir  = drive_base / 'thumbnails'
for d in (clip_dir, thumb_dir):
    d.mkdir(parents=True, exist_ok=True)

video_path = '/content/drive/MyDrive/TAVE 16th/data/기생충.PARASITE.2019.1080p.FHDRip.H264.AAC-NonDRM.mp4'  
video = open_video(video_path)


content_detector = ContentDetector(
    threshold=20.0,
    min_scene_len=30,
    luma_only=False,
    kernel_size=None
)

# Scene Manager 생성
scene_manager = SceneManager()
scene_manager.add_detector(content_detector)
# Scene Detect 수행
scene_manager.detect_scenes(video, show_progress=True)


# 장면 분할 결과 확인
scene_list = scene_manager.get_scene_list()
print()
for scene in scene_list:
  start, end = scene
  print(start, "~", end)


# 클립 생성
# 영상 자르기 (파일로 저장)
split_video_ffmpeg(
    video_path,
    scene_list,
    output_dir=str(clip_dir),
    show_progress=True
)


# 각 장면 별 썸네일 생성 (jpg 파일로 저장)
save_images(
    scene_list, # 장면 리스트 [(시작, 끝)]
    video, 
    num_images=1, # 각 장면 당 이미지 개수
    image_name_template='$SCENE_NUMBER', 
    output_dir=str(thumb_dir))
