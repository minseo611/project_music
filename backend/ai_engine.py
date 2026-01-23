import subprocess
import music21
import os
import base64
import platform
import shutil
import io
import copy
from datetime import datetime
from typing import Optional, List
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

print("\n" + "="*50)
print("🛡️ [System] EasyScore AI Engine (Persistent Storage Mode)")
print("   - 모든 변환 파일이 './saved_results' 폴더에 영구 저장됩니다.")
print("   - 임시 폴더(tempfile) 사용을 중단했습니다.")
print("="*50 + "\n")

# =========================================================
# 📂 1. 저장 경로 강제 설정 (절대 사라지지 않음)
# =========================================================
BASE_OUTPUT_DIR = os.path.join(os.getcwd(), "saved_results")
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)

# =========================================================
# 🕵️ OS 및 경로 설정
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
# MuseScore 변환기
# =========================================================
def convert_with_musescore(input_path: str, output_path: str) -> bool:
    ms_path = find_musescore()
    if not ms_path: return False
    cmd = [ms_path, "-o", output_path, input_path]
    try:
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
# 이미지 전처리
# =========================================================
def preprocess_image(image_bytes: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        target_width = 2500
        if img.width < target_width:
            ratio = target_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.5) 
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        img = img.point(lambda x: 0 if x < 140 else 255, '1')
        
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except:
        return image_bytes

# =========================================================
# 박자 및 편곡 로직 (기존 로직 유지)
# =========================================================
def _force_clean_durations(score):
    try: score.quantize(quarterLengthDivisors=(4, 12), processOffsets=True, processDurations=True, inPlace=True)
    except: pass
    return score
def _clean_omr_artifacts(score):
    try: score.quantize(quarterLengthDivisors=(4, 12, 16), processOffsets=True, processDurations=True, inPlace=True)
    except: pass
    return score
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

def _simplify_vertical(score_in, mode="easy"):
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
            new_element_list = [] 
            if mode == "hard":
                if isinstance(el, music21.note.Note) or isinstance(el, music21.chord.Chord):
                    if isinstance(el, music21.chord.Chord):
                        pitches = sorted(el.pitches)
                        top_p = pitches[-1]; bot_p = pitches[0]  
                    else: top_p = el.pitch; bot_p = el.pitch
                    if i > 0 and el.duration.quarterLength >= 1.0:
                        n1 = music21.note.Note(bot_p)
                        p2 = copy.deepcopy(bot_p); p2.midi += 7; n2 = music21.note.Note(p2)
                        p3 = copy.deepcopy(bot_p); p3.midi += 12; n3 = music21.note.Note(p3)
                        n4 = music21.note.Note(p2)
                        dur = el.duration.quarterLength / 4.0
                        for n in [n1, n2, n3, n4]: n.duration.quarterLength = dur
                        n1.offset = el.offset; n2.offset = el.offset + dur
                        n3.offset = el.offset + (dur * 2); n4.offset = el.offset + (dur * 3)
                        new_element_list = [n1, n2, n3, n4]
                    else:
                        if i == 0: 
                            p_main = copy.deepcopy(top_p)
                            p_sub = copy.deepcopy(top_p); p_sub.midi -= 12
                            p_thd = copy.deepcopy(top_p); p_thd.midi -= 4 
                            chord = music21.chord.Chord([p_sub, p_thd, p_main])
                        else:
                            p_main = copy.deepcopy(bot_p)
                            p_sub = copy.deepcopy(bot_p); p_sub.midi -= 12
                            chord = music21.chord.Chord([p_sub, p_main])
                        chord.offset = el.offset; chord.duration = copy.deepcopy(el.duration)
                        new_element_list = [chord]
            else:
                new_element = None
                if i == 0: 
                    if isinstance(el, music21.chord.Chord):
                        melody = el.pitches[-1]
                        if mode == "easy" and len(el.pitches) >= 3:
                            harmony = el.pitches[-2]; new_element = music21.chord.Chord([harmony, melody])
                        else: new_element = music21.note.Note(melody)
                    elif isinstance(el, music21.note.Note): new_element = music21.note.Note(el.pitch)
                else:
                    if mode == "super_easy":
                        if el.offset % 1.0 != 0: continue
                    if isinstance(el, music21.chord.Chord):
                        bass = el.pitches[0]; new_element = music21.note.Note(bass)
                    elif isinstance(el, music21.note.Note): new_element = music21.note.Note(el.pitch)
                if new_element:
                    new_element.offset = el.offset
                    if mode == "super_easy" and i > 0:
                        new_element.duration.type = 'quarter'; new_element.duration.quarterLength = 1.0
                    else: new_element.duration = copy.deepcopy(el.duration)
                    try: new_element.articulations = copy.deepcopy(el.articulations)
                    except: pass
                    if i == 0: 
                        if new_element.isChord: pass 
                        else:
                            while new_element.pitch.midi < 60: new_element.pitch.midi += 12
                    else: 
                        target_pitches = new_element.pitches if new_element.isChord else [new_element.pitch]
                        for p in target_pitches:
                            while p.midi < 36: p.midi += 12
                            while p.midi > 60: p.midi -= 12
                    new_element_list = [new_element]
            for item in new_element_list: new_part.insert(item.offset, item)
        try:
            if mode == "hard": new_part.makeBeams(inPlace=True)
        except: pass
        new_score.insert(0, new_part)
    new_score = _force_clean_durations(new_score)
    return new_score

# =========================================================
# 🔥 [핵심 수정] Audiveris 실행 (영구 저장 모드)
# =========================================================
def run_audiveris(image_bytes: bytes) -> str:
    # 1. 오늘 날짜/시간으로 폴더 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join(BASE_OUTPUT_DIR, f"run_{timestamp}")
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"📂 작업 폴더 생성됨: {save_dir}")

    # 2. 전처리된 이미지 저장
    input_image_path = os.path.join(save_dir, "input.png")
    processed_bytes = preprocess_image(image_bytes)
    with open(input_image_path, "wb") as f:
        f.write(processed_bytes)
    
    # 디버그용 원본 저장 (선택 사항)
    # with open(os.path.join(save_dir, "original_input.png"), "wb") as f:
    #     f.write(image_bytes)
        
    info = find_audiveris_info()
    separator = ";" if IS_WINDOWS else ":"
    cp_list = [
        info["jar"],
        os.path.join(info["root"], "lib", "*"),
        os.path.join(info["root"], "app", "*"),
        os.path.join(info["root"], "*")
    ]
    
    command = [
        info["java_cmd"], "-cp", separator.join(cp_list), "org.audiveris.omr.Main",
        "-batch", "-output", save_dir, "-export", input_image_path
    ]
    
    print("⚙️ Audiveris 엔진 가동...")
    try:
        subprocess.run(command, check=True, timeout=180, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False)
    except subprocess.CalledProcessError as e:
        if "JavaFX" not in e.stderr: print(f"⚠️ Audiveris 경고: {e.stderr}")

    found_file = None
    for root, _, files in os.walk(save_dir):
        for file in files:
            if file.endswith(".musicxml") or file.endswith(".mxl"):
                found_file = os.path.join(root, file)
                break
        if found_file: break

    if not found_file: raise RuntimeError("변환된 악보 파일을 찾을 수 없습니다.")

    # MIDI 및 XML 저장 (영구 보존)
    midi_path = os.path.join(save_dir, "clean_score.mid")
    if convert_with_musescore(found_file, midi_path):
        try:
            score = music21.converter.parse(midi_path)
            score = _force_clean_durations(score)
            
            clean_xml_output = os.path.join(save_dir, "final_output.musicxml")
            score.write('musicxml', fp=clean_xml_output)
            print(f"✅ 최종 XML 저장됨: {clean_xml_output}")
            
            with open(clean_xml_output, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"{e}")
    else:
         raise RuntimeError("MuseScore MIDI 변환 실패")

# =========================================================
# 🔥 [핵심 수정] 편곡 및 결과 생성 (영구 저장 모드)
# =========================================================
def simplify_and_generate(music_xml_content: str) -> dict:
    setup_music21()
    
    # 작업 폴더는 가장 최근에 생성된 폴더를 사용 (run_audiveris에서 만든 폴더)
    latest_dirs = sorted([d for d in os.listdir(BASE_OUTPUT_DIR) if d.startswith("run_")], reverse=True)
    if latest_dirs:
        work_dir = os.path.join(BASE_OUTPUT_DIR, latest_dirs[0])
    else:
        # 만약 폴더가 없으면 새로 생성 (비상용)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_fallback")
        work_dir = os.path.join(BASE_OUTPUT_DIR, f"run_{timestamp}")
        os.makedirs(work_dir, exist_ok=True)

    if isinstance(music_xml_content, bytes):
        try: music_xml_content = music_xml_content.decode('utf-8')
        except: music_xml_content = music_xml_content.decode('latin-1')

    # 입력 XML 파일로 저장
    input_xml_path = os.path.join(work_dir, "source_input.musicxml")
    with open(input_xml_path, "w", encoding='utf-8') as f:
        f.write(music_xml_content)
        
    score_in = music21.converter.parse(input_xml_path)
    
    print("🌿 [Processing] 3단계 난이도 생성 중...")
    
    hard_score = _simplify_vertical(score_in, mode="hard")
    normal_score = _simplify_vertical(score_in, mode="easy")
    super_score = _simplify_vertical(score_in, mode="super_easy")
    
    def _generate_outputs(score_obj, suffix):
        out_midi = None
        out_png = None
        
        # 파일명 구분: hard / easy / super_easy
        base_name = f"result_{suffix}"
        xml_path = os.path.join(work_dir, f"{base_name}.musicxml")
        midi_path = os.path.join(work_dir, f"{base_name}.mid")
        png_path = os.path.join(work_dir, f"{base_name}.png")
        final_png_path = os.path.join(work_dir, f"{base_name}_final.png")
        
        try:
            # 1. XML 저장
            score_obj.write("musicxml", xml_path)
            
            # 2. MIDI 변환 및 저장
            if convert_with_musescore(xml_path, midi_path):
                with open(midi_path, "rb") as f:
                    out_midi = base64.b64encode(f.read()).decode()
            
            # 3. PNG 변환 및 저장
            success = convert_with_musescore(xml_path, png_path)
            if not success and out_midi:
                # MIDI 백업본으로 시도
                midi_temp = os.path.join(work_dir, f"{base_name}_temp.mid")
                with open(midi_temp, "wb") as f:
                    f.write(base64.b64decode(out_midi))
                success = convert_with_musescore(midi_temp, png_path)

            if success:
                # 배경 투명화 처리
                img = Image.open(png_path).convert("RGBA")
                white = Image.new("RGBA", img.size, (255, 255, 255, 255))
                merged = Image.alpha_composite(white, img).convert("RGB")
                merged.save(final_png_path, "PNG")
                
                print(f"   ✨ [{suffix}] 변환 완료: {final_png_path}")
                with open(final_png_path, "rb") as f:
                    out_png = base64.b64encode(f.read()).decode()
        except Exception as e:
            print(f"❌ [{suffix}] 생성 중 오류: {e}")
            pass
        return out_midi, out_png

    hard_midi, hard_png = _generate_outputs(hard_score, "HARD")
    norm_midi, norm_png = _generate_outputs(normal_score, "EASY")
    super_midi, super_png = _generate_outputs(super_score, "SUPER_EASY")
    
    return {
        "hard_midi_base64": hard_midi,
        "hard_image_base64": hard_png,
        "easy_midi_base64": norm_midi,
        "easy_image_base64": norm_png,
        "super_easy_midi_base64": super_midi,
        "super_easy_image_base64": super_png,
        "simplified_midi_base64": norm_midi,
        "simplified_image_base64": norm_png
    }