import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import music21 as m21
import os
import subprocess
from copy import deepcopy

# Define the output directory
OUTPUT_DIR = r"F:\EUCLIDO\Tasks\__new_tasks\audio\files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_music(x, y, duration=10):
    stream = m21.stream.Stream()
    mm = m21.tempo.MetronomeMark(number=90)
    stream.append(mm)

    piano_part = m21.stream.Part()
    piano_part.append(m21.instrument.Piano())
    synth_part = m21.stream.Part()
    synth_part.append(m21.instrument.ElectricGuitar())

    distances = np.sqrt(x**2 + y**2)
    angles = np.angle(x + 1j*y) % (2*np.pi)
    
    norm_dist = (distances - np.min(distances)) / np.ptp(distances)
    norm_angles = angles / (2*np.pi)
    
    chords = [
        m21.chord.Chord(['C4', 'E4', 'G4']),
        m21.chord.Chord(['A3', 'C4', 'E4']),
        m21.chord.Chord(['F3', 'A3', 'C4']),
        m21.chord.Chord(['G3', 'B3', 'D4'])
    ]
    
    points = len(x)
    base_duration = duration / points * 4
    
    for i in range(points):
        pitch = 60 + int(norm_dist[i]*24)
        note = m21.note.Note(pitch)
        note.quarterLength = base_duration * (0.5 + norm_angles[i]*1.5)
        note.volume.velocity = 60 + int(norm_dist[i]*40)
        
        harmony_pitch = pitch + 4
        harmony_note = m21.note.Note(harmony_pitch)
        harmony_note.quarterLength = note.quarterLength
        harmony_note.volume.velocity = note.volume.velocity - 20
        
        piano_part.append(note)
        synth_part.append(harmony_note)
        
        if i % 8 == 0:
            original_chord = chords[i % len(chords)]
            new_chord = deepcopy(original_chord)
            new_chord.quarterLength = base_duration * 2
            synth_part.append(new_chord)
    
    stream.append(piano_part)
    stream.append(synth_part)
    
    return stream

def midi_to_wav_fluidsynth(midi_path, wav_path, soundfont):
    try:
        subprocess.run([
            'fluidsynth', 
            '-T', 'wav', 
            '-F', wav_path, 
            '-i', soundfont, 
            midi_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FluidSynth conversion failed: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        print("FluidSynth not found. Install from https://www.fluidsynth.org/")
        return False

def create_snowflake_animation_and_music(max_order=4, fps=30, duration=15):
    print("Creating animation...")
    fig, anim, total_frames, x, y = create_animation(max_order, fps, duration)
    
    animation_path = os.path.join(OUTPUT_DIR, "snowflake_animation.mp4")
    print(f"Saving animation to {animation_path}...")
    anim.save(animation_path, fps=fps, extra_args=['-vcodec', 'libx264'])
    plt.close(fig)
    
    print("Generating music...")
    stream = generate_music(x, y, duration)
    
    midi_path = os.path.join(OUTPUT_DIR, "snowflake_music.mid")
    print(f"Saving MIDI to {midi_path}...")
    stream.write('midi', fp=midi_path)
    
    wav_path = os.path.join(OUTPUT_DIR, "snowflake_music.wav")
    print("Attempting to convert MIDI to WAV...")
    
    soundfont_path = r"F:\EUCLIDO\Tasks\__new_tasks\audio\FluidR3_GM.sf2"
    
    if midi_to_wav_fluidsynth(midi_path, wav_path, soundfont_path):
        print("FluidSynth conversion successful")
    else:
        print("Creating silent WAV placeholder...")
        try:
            subprocess.run([
                'ffmpeg', 
                '-f', 'lavfi', 
                '-i', f'anullsrc=r=44100:cl=stereo:d={duration}', 
                '-ac', '2', 
                wav_path
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            print(f"FFmpeg failed: {str(e)}")
    
    # Verify files exist before merging
    if not os.path.exists(animation_path):
        raise FileNotFoundError(f"Missing animation file: {animation_path}")
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"Missing audio file: {wav_path}")
    
    # Get file durations
    try:
        audio_duration = float(subprocess.check_output([
            'ffprobe', '-i', wav_path, 
            '-show_entries', 'format=duration', 
            '-v', 'quiet', '-of', 'csv=p=0'
        ]).decode().strip())
        
        video_duration = float(subprocess.check_output([
            'ffprobe', '-i', animation_path, 
            '-show_entries', 'format=duration', 
            '-v', 'quiet', '-of', 'csv=p=0'
        ]).decode().strip())
        
        print(f"\nAudio duration: {audio_duration:.2f}s")
        print(f"Video duration: {video_duration:.2f}s")
        print(f"Difference: {abs(audio_duration - video_duration):.2f}s")
    except Exception as e:
        print("Duration check failed. Proceeding with merge...")
    
    output_path = os.path.join(OUTPUT_DIR, "snowflake_with_sound.mp4")
    print(f"\nMerging audio and video to {output_path}...")
    
    try:
        cmd = [
            'ffmpeg',
            '-y',
            '-i', animation_path,
            '-i', wav_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            '-fflags', '+shortest',
            '-max_interleave_delta', '100M',
            output_path
        ]
        
        print(f"\nRunning FFmpeg command:")
        print(' '.join(cmd))
        
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        
        print("\nFFmpeg output:")
        print(result.stdout.decode())
        print("\nMerge successful!")
        
    except subprocess.CalledProcessError as e:
        print("\nMerge failed. FFmpeg output:")
        print(e.stdout.decode())
        print(e.stderr.decode())
    
    return {
        "animation_path": animation_path,
        "midi_path": midi_path,
        "wav_path": wav_path if os.path.exists(wav_path) else None,
        "output_path": output_path if os.path.exists(output_path) else None
    }

def koch_curve(order, scale=10):
    def _koch_curve_complex(order):
        if order == 0:
            angles = np.array([0, 90, 180, 270]) * np.pi / 180
            return scale * np.exp(angles * 1j)
        else:
            prev = _koch_curve_complex(order - 1)
            n = len(prev)
            result = np.zeros(n * 4, dtype=complex)
            
            for i in range(n):
                a, b = prev[i], prev[(i + 1) % n]
                c = a + (b - a) / 3
                d = a + (b - a) / 2 + (b - a) / 6 * np.exp(1j * np.pi / 3)
                e = a + 2 * (b - a) / 3
                result[4 * i] = a
                result[4 * i + 1] = c
                result[4 * i + 2] = d
                result[4 * i + 3] = e
            
            return result
    
    points = _koch_curve_complex(order)
    x, y = points.real, points.imag
    return x, y

def create_animation(max_order=4, fps=30, duration=10):
    fig, ax = plt.subplots(figsize=(10, 10), facecolor='white')
    plt.title("The Sound of a Snowflake", fontsize=20, color='white')
    plt.text(0, -13, "Adapted from Patrick Georges, GSPIA, University of Ottawa", 
             ha='center', fontsize=12, color='white')
    ax.set_facecolor('darkred')
    ax.set_aspect('equal')
    ax.axis('off')
    
    x, y = koch_curve(max_order)
    koch_line, = ax.plot(x, y, lw=1.5, color='red')
    point, = ax.plot([], [], 'go', markersize=8)
    center_to_point, = ax.plot([], [], 'k--', lw=1.5, alpha=0.7)
    
    margin = 2
    ax.set_xlim(np.min(x) - margin, np.max(x) + margin)
    ax.set_ylim(np.min(y) - margin, np.max(y) + margin)
    
    total_frames = fps * duration
    
    def update(frame):
        t = frame / total_frames
        index = int(t * len(x))
        if index >= len(x):
            index = len(x) - 1
        
        point.set_data([x[index]], [y[index]])
        center_to_point.set_data([0, x[index]], [0, y[index]])
        
        return point, center_to_point
    
    anim = FuncAnimation(fig, update, frames=total_frames, 
                       interval=1000/fps, blit=True)
    
    return fig, anim, total_frames, x, y

if __name__ == "__main__":
    print(f"Files will be saved to: {OUTPUT_DIR}")
    results = create_snowflake_animation_and_music(max_order=4, fps=30, duration=15)
    
    print("\nResults:")
    for key, value in results.items():
        print(f"{key}: {value}")
