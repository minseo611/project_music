# backend/ai_engine.py
# =========================================================
# EasyScore 2.0 - [최종 수정] 셋잇단음표(Triplet) 보존 + 에러 해결
# =========================================================

import subprocess
import music21
import os
import tempfile
import base64
import platform
import shutil
import io
import copy
from typing import Optional, List
from PIL import Image, ImageEnhance, ImageFilter

print("\n" + "="*50)
print("🛡️ [System] EasyScore AI Engine 가동")
print("   - Easy: 원본 리듬 유지 (셋잇단음표 복구)")
print("   - Super Easy: 왼손 정박만 연주 (2번 칠 거 1번 치기)")
print("   - Smart Quantize: 에러 방지 + 셋잇단음표 호환")
print("="*50 + "\n")

# =========================================================
# 🕵️ OS 자동 감지 및 경로 설정
# =========================================================

CURRENT_OS = platform.system()
IS_WINDOWS = CURRENT_OS == "Windows"
IS_MAC = CURRENT_OS == "Darwin"

USER_MUSESCORE_PATH = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"

def find_musescore() -> str:
    if IS_WINDOWS and USER_MUSESCORE_PATH and os.path.exists(USER_MUSESCORE_PATH):
        return USER_MUSESCORE_PATH

    search_paths = []
    if IS_WINDOWS:
        search_paths = [
            r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe",
            r"C:\Program Files (x86)\MuseScore 4\bin\MuseScore4.exe",
            r"C:\Program Files\MuseScore Studio 4\bin\MuseScore4.exe",
        ]
    elif IS_MAC:
        search_paths = [
            '/Applications/MuseScore 4.app/Contents/MacOS/mscore',
            '/Applications/MuseScore Studio 4.app/Contents/MacOS/mscore',
        ]

    for path in search_paths:
        if os.path.exists(path): return path

    cmd = "MuseScore4" if IS_WINDOWS else "mscore"
    if shutil.which(cmd): return shutil.which(cmd)
    return ""

def find_audiveris_info() -> dict:
    if IS_WINDOWS:
        search_roots = [
            r"C:\Program Files\Audiveris",
            r"C:\Audiveris",
            os.path.expanduser(r"~\AppData\Local\Audiveris")
        ]
    else:
        search_roots = ["/Applications/Audiveris.app", "/usr/local/share/audiveris"]

    for root_dir in search_roots:
        if not os.path.exists(root_dir): continue
        jar_path = None
        for current_root, dirs, files in os.walk(root_dir):
            if "audiveris.jar" in files:
                jar_path = os.path.join(current_root, "audiveris.jar")
                break
        if jar_path:
            install_root = os.path.dirname(os.path.dirname(jar_path))
            bundled_java = os.path.join(install_root, "runtime", "bin", "java.exe")
            if not os.path.exists(bundled_java):
                 bundled_java = os.path.join(install_root, "bin", "runtime", "bin", "java.exe")
            final_java = bundled_java if os.path.exists(bundled_java) else "java"
            return { "jar": jar_path, "root": install_root, "java_cmd": final_java }
    
    raise RuntimeError("Audiveris를 찾을 수 없습니다.")

def setup_music21():
    try:
        ms = find_musescore()
        if ms:
            us = music21.environment.UserSettings()
            us['musicxmlPath'] = ms
            us['musescoreDirectPNGPath'] = ms
    except: pass

setup_music21()

# =========================================================
# 🛠️ MuseScore 변환기 (안전장치 3: shell=False 유지)
# =========================================================
def convert_with_musescore(input_path: str, output_path: str) -> bool:
    ms_path = find_musescore()
    if not ms_path: return False

    cmd = [ms_path, "-o", output_path, input_path]
    try:
        # 🚨 [수정 금지] Windows 호환성을 위해 shell=False 유지
        subprocess.run(
            cmd, check=True, timeout=120, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False 
        )

        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            return True

        base, ext = os.path.splitext(output_path)
        alt = f"{base}-1{ext}"
        if os.path.exists(alt):
            shutil.move(alt, output_path)
            return True
    except: pass
    return False

# =========================================================
# 🖼️ 이미지 전처리
# =========================================================
def preprocess_image(image_bytes: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)
        
        if img.width < 1000:
             new_size = (img.width * 2, img.height * 2)
             img = img.resize(new_size, Image.Resampling.LANCZOS)
             
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except:
        return image_bytes

# =========================================================
# 🎵 [스마트] 박자 강제 세탁기 (여기가 수정됨!)
# =========================================================
def _force_clean_durations(score):
    """
    MusicXML 에러를 막으면서 셋잇단음표(Triplet)는 살립니다.
    """
    try:
        # quarterLengthDivisors=(4, 12):
        # 4 -> 16분음표 허용
        # 12 -> 3(셋잇단)과 4(16분)의 최소공배수 -> 셋잇단음표 허용!
        score.quantize(
            quarterLengthDivisors=(4, 12), 
            processOffsets=True, 
            processDurations=True, 
            inPlace=True
        )
    except:
        pass
    return score

# =========================================================
# 🎵 편곡 로직
# =========================================================
def _transpose_smart(score):
    try:
        key = score.analyze("key")
        target = music21.key.Key("C") if key.mode == "major" else music21.key.Key("a")
        interval = music21.interval.Interval(key.tonic, target.tonic)
        score = score.transpose(interval)

        pitches = [p.midi for p in score.flatten().pitches]
        if pitches:
            avg = sum(pitches) / len(pitches)
            if avg > 80: score = score.transpose("-P8")
            elif avg < 50: score = score.transpose("P8")
    except: pass
    return score

def _clean_omr_artifacts(score):
    try:
        # 여기서도 셋잇단음표를 살리기 위해 12 추가
        score.quantize(quarterLengthDivisors=(4, 12, 16), processOffsets=True, processDurations=True, inPlace=True)
    except: pass
    return score

def _simplify_vertical(score_in, mode="easy"):
    # 1. 기본 정리
    score_in = _clean_omr_artifacts(score_in)
    score_in = _force_clean_durations(score_in)
    score_in = _transpose_smart(score_in)
    
    new_score = music21.stream.Score()
    parts = list(score_in.parts)
    
    ts = score_in.flatten().getElementsByClass(music21.meter.TimeSignature).first()
    if not ts: ts = music21.meter.TimeSignature('4/4')
    
    for i, part in enumerate(parts):
        new_part = music21.stream.Part()
        new_part.insert(0, copy.deepcopy(ts))
        
        for el in part.flatten().getElementsByClass([music21.clef.Clef, music21.key.KeySignature]):
            new_part.insert(el.offset, copy.deepcopy(el))
            
        try: flat_notes = part.flatten().notes
        except: flat_notes = part.flat.notes

        for el in flat_notes:
            new_note = None
            
            # --- 오른손 (Melody) ---
            if i == 0: 
                if isinstance(el, music21.chord.Chord):
                    melody = el.pitches[-1]
                    if mode == "normal" and len(el.pitches) >= 3:
                        harmony = el.pitches[-2]
                        new_note = music21.chord.Chord([harmony, melody])
                    else:
                        new_note = music21.note.Note(melody)
                elif isinstance(el, music21.note.Note):
                    new_note = music21.note.Note(el.pitch)

            # --- 왼손 (Accompaniment) ---
            else: 
                # 🔥 [Super Easy] 정박(1.0, 2.0) 아니면 생략 (2번 칠 거 1번 치기)
                if mode == "super_easy":
                    # offset이 정수가 아니면(엇박자면) 건너뜀
                    if el.offset % 1.0 != 0:
                        continue 

                if isinstance(el, music21.chord.Chord):
                    bass = el.pitches[0]
                    new_note = music21.note.Note(bass)
                elif isinstance(el, music21.note.Note):
                    new_note = music21.note.Note(el.pitch)

            # --- 노트 추가 ---
            if new_note:
                new_note.offset = el.offset
                
                # Super Easy는 무조건 4분음표(1박자)로 통일
                if mode == "super_easy" and i > 0:
                     new_note.duration.type = 'quarter'
                     new_note.duration.quarterLength = 1.0
                else:
                     # Easy 모드는 원본 길이 유지 (셋잇단음표도 유지됨)
                     new_note.duration = el.duration
                
                try: new_note.articulations = copy.deepcopy(el.articulations)
                except: pass
                
                if isinstance(new_note, music21.note.Note):
                    if i == 0: 
                        while new_note.pitch.midi < 60: new_note.pitch.midi += 12
                    else: 
                        while new_note.pitch.midi < 36: new_note.pitch.midi += 12
                        while new_note.pitch.midi > 60: new_note.pitch.midi -= 12

                new_part.insert(new_note.offset, new_note)
        
        # 마지막으로 박자 정리
        new_part = _force_clean_durations(new_part)
        new_score.insert(0, new_part)
        
    return new_score

# =========================================================
# 🚀 메인 엔진 1: Audiveris (안전장치 1 유지)
# =========================================================
def run_audiveris(image_bytes: bytes) -> str:
    with tempfile.TemporaryDirectory() as temp_dir:
        input_image_path = os.path.join(temp_dir, "input.png")
        processed_bytes = preprocess_image(image_bytes)
        with open(input_image_path, "wb") as f:
            f.write(processed_bytes)
            
        info = find_audiveris_info()
        separator = ";" if IS_WINDOWS else ":"
        cp_list = [
            info["jar"],
            os.path.join(info["root"], "lib", "*"),
            os.path.join(info["root"], "app", "*"),
            os.path.join(info["root"], "*")
        ]
        
        command = [
            info["java_cmd"],
            "-cp", separator.join(cp_list), 
            "org.audiveris.omr.Main",
            "-batch", "-output", temp_dir, "-export", input_image_path
        ]
        
        print("⚙️ Audiveris 엔진 가동...")
        try:
            # 🚨 [수정 금지] shell=False 유지
            subprocess.run(
                command, check=True, timeout=180, 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False 
            )
        except subprocess.CalledProcessError as e:
            if "JavaFX" not in e.stderr: print(f"⚠️ Audiveris 경고: {e.stderr}")

        found_file = None
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".musicxml") or file.endswith(".mxl"):
                    found_file = os.path.join(root, file)
                    break
            if found_file: break

        if not found_file: raise RuntimeError("변환된 악보 파일을 찾을 수 없습니다.")

        # 🔥 [안전장치 1 유지] XML 파싱 실패 시 MIDI 우회
        midi_path = os.path.join(temp_dir, "clean_score.mid")
        if convert_with_musescore(found_file, midi_path):
            try:
                score = music21.converter.parse(midi_path)
                
                # 📌 [FIX] 스마트 박자 세탁기 (셋잇단음표 유지)
                score = _force_clean_durations(score)
                
                clean_xml_output = os.path.join(temp_dir, "final_output.musicxml")
                score.write('musicxml', fp=clean_xml_output)
                with open(clean_xml_output, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"❌ MIDI 우회 실패 원인: {e}")
                raise RuntimeError(f"악보 변환 중 치명적 오류 발생: {e}")
        else:
             raise RuntimeError("MuseScore MIDI 변환 실패")

# =========================================================
# 🚀 메인 엔진 2: 단순화 및 파일 생성 (안전장치 2 유지)
# =========================================================
def simplify_and_generate(music_xml_content: str) -> dict:
    setup_music21()
    
    if isinstance(music_xml_content, bytes):
        try: music_xml_content = music_xml_content.decode('utf-8')
        except: music_xml_content = music_xml_content.decode('latin-1')

    with tempfile.NamedTemporaryFile(delete=False, suffix=".musicxml", mode='w', encoding='utf-8') as tmp:
        tmp.write(music_xml_content)
        tmp_path = tmp.name
        
    try: score_in = music21.converter.parse(tmp_path)
    finally:
        try: os.unlink(tmp_path)
        except: pass
    
    print("🌿 [Processing] 편곡 및 이미지 생성 시작...")
    
    normal_score = _simplify_vertical(score_in, mode="normal")
    super_score = _simplify_vertical(score_in, mode="super_easy")
    
    # 🔥 [안전장치 2 유지] 2중 변환 로직
    def _generate_outputs(score_obj):
        out_midi = None
        out_png = None
        try:
            with tempfile.TemporaryDirectory() as temp:
                xml_path = os.path.join(temp, "score.musicxml")
                score_obj.write("musicxml", xml_path)
                
                # MIDI 생성
                midi_path = os.path.join(temp, "score.mid")
                if convert_with_musescore(xml_path, midi_path):
                    with open(midi_path, "rb") as f:
                        out_midi = base64.b64encode(f.read()).decode()
                
                # PNG 생성 (1차 시도: XML -> PNG)
                png_path = os.path.join(temp, "score.png")
                success = convert_with_musescore(xml_path, png_path)
                
                # PNG 생성 (2차 시도: 실패 시 MIDI -> PNG 우회)
                if not success and out_midi:
                    print("⚠️ XML->PNG 변환 실패. MIDI->PNG 우회 전략 실행!")
                    midi_temp = os.path.join(temp, "temp_fallback.mid")
                    with open(midi_temp, "wb") as f:
                        f.write(base64.b64decode(out_midi))
                    success = convert_with_musescore(midi_temp, png_path)

                if success:
                    img = Image.open(png_path).convert("RGBA")
                    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
                    merged = Image.alpha_composite(white, img).convert("RGB")
                    final_png = os.path.join(temp, "final.png")
                    merged.save(final_png, "PNG")
                    with open(final_png, "rb") as f:
                        out_png = base64.b64encode(f.read()).decode()
        except Exception as e:
            print(f"❌ 출력 생성 중 오류: {e}")
            pass
        return out_midi, out_png

    norm_midi, norm_png = _generate_outputs(normal_score)
    super_midi, super_png = _generate_outputs(super_score)
    
    return {
        "easy_midi_base64": norm_midi,
        "easy_image_base64": norm_png,
        "super_easy_midi_base64": super_midi,
        "super_easy_image_base64": super_png,
        "simplified_midi_base64": norm_midi,
        "simplified_image_base64": norm_png
    }