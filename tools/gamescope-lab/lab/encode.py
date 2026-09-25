"""Turn the recorded frames (+ output audio) into an MP4."""
import json, subprocess
r = json.load(open("/lab/demo/result.json"))
frames = r["frames"]
with open("/lab/demo/list.txt", "w") as f:
    for (t, path), (t2, _) in zip(frames, frames[1:] + [(frames[-1][0] + 1.5, None)]):
        f.write(f"file '{path}'\nduration {max(0.01, t2 - t):.3f}\n")
    f.write(f"file '{frames[-1][1]}'\n")
cmd = ["ffmpeg", "-y", "-loglevel", "error",
       "-f", "concat", "-safe", "0", "-i", "/lab/demo/list.txt",
       "-i", "/lab/demo/tv_hdmi.wav", "-i", "/lab/demo/headset.wav",
       "-filter_complex", "[1:a][2:a]amix=inputs=2:normalize=0,volume=0.35[a];[0:v]fps=30,format=yuv420p[v]",
       "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "23",
       "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", "/lab/demo/hearth-demo.mp4"]
subprocess.run(cmd, check=True)
print("frames", len(frames), "length", round(frames[-1][0], 1), "s")

# Frames aren't needed once the video exists.
import glob, os
for f in glob.glob("/lab/demo/f*.png"):
    os.remove(f)
