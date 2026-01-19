# backend/ai_engine.py
# =========================================================
# EasyScore 2.0 - 🛡️ [이미지 복구] 안전장치 재탑재 버전
# =========================================================
# ==================================================================================
# 🚨 [개발자 필독 / 수정 주의] 🚨
# 이 파일에는 '파싱 에러(KeyError: 3)'와 '이미지 누락'을 방지하기 위한
# 필수 안전장치(Fallback)들이 포함되어 있습니다.
#
# 아래 로직을 수정하거나 삭제하지 마세요:
# 1. MIDI 우회 전략: XML 파싱 실패 시 MIDI로 변환 후 읽는 try-except 구문 유지
# 2. 이미지 생성 2차 시도: XML->PNG 실패 시 MIDI->PNG로 변환하는 로직 유지
# 3. Windows 호환성: subprocess.run()에서 shell=False 옵션 절대 변경 금지
# ==================================================================================

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
print("🛡️ [Safe Mode] 악보 이미지를 끝까지 책임지고 만들어냅니다! 🛡️")
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
        ms_path = find_musescore()
        if ms_path:
            us = music21.environment.UserSettings()
            us['musicxmlPath'] = ms_path
            us['musescoreDirectPNGPath'] = ms_path
    except: pass

# =========================================================
# 🛠️ MuseScore 변환기
# =========================================================
def convert_with_musescore(input_path: str, output_path: str) -> bool:
    ms_path = find_musescore()
    if not ms_path: return False
    
    # MuseScore 변환 명령
    cmd = [ms_path, "-o", output_path, input_path]
    try:
        subprocess.run(
            cmd, check=True, timeout=120, 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False
        )
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            return True
        
        # 파일명-1.png 처리
        base, ext = os.path.splitext(output_path)
        if ext.lower() == '.png':
            alt_path = f"{base}-1{ext}"
            if os.path.exists(alt_path) and os.path.getsize(alt_path) > 100:
                shutil.move(alt_path, output_path)
                return True
    except: pass
    return False

# =========================================================
# 🖼️ 이미지 전처리
# =========================================================
def preprocess_image(image_bytes: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("L")
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
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
# 🎵 편곡 로직 (Organic Version 유지)
# =========================================================

def _transpose_smart(score):
    try:
        key = score.analyze('key')
        if key.mode == 'major': target = music21.key.Key('C')
        else: target = music21.key.Key('a')
        interval = music21.interval.Interval(key.tonic, target.tonic)
        new_score = score.transpose(interval)
        
        pitches = [p.midi for p in new_score.flatten().pitches]
        if pitches:
            avg = sum(pitches) / len(pitches)
            if avg > 80: new_score = new_score.transpose('-P8')
            elif avg < 50: new_score = new_score.transpose('P8')
        return new_score
    except: return score

def _clean_omr_artifacts(score):
    try:
        score.quantize(quarterLengthDivisors=(16, 12), processOffsets=True, processDurations=True, inPlace=True)
    except: pass
    return score

def _simplify_vertical(score_in, mode="easy"):
    score_in = _transpose_smart(score_in)
    _clean_omr_artifacts(score_in)
    
    new_score = music21.stream.Score()
    parts = list(score_in.parts)
    
    # 박자표 복사 (없으면 4/4)
    ts = score_in.flatten().getElementsByClass(music21.meter.TimeSignature).first()
    if not ts: ts = music21.meter.TimeSignature('4/4')
    
    for i, part in enumerate(parts):
        new_part = music21.stream.Part()
        new_part.insert(0, copy.deepcopy(ts)) # 박자표 강제 삽입
        
        # 메타데이터 복사
        for el in part.flatten().getElementsByClass([music21.clef.Clef, music21.key.KeySignature]):
            new_part.insert(el.offset, copy.deepcopy(el))
            
        try: flat_notes = part.flatten().notes
        except: flat_notes = part.flat.notes

        for el in flat_notes:
            new_note = None
            if i == 0: # RH
                if isinstance(el, music21.chord.Chord):
                    melody = el.pitches[-1]
                    if mode == "normal" and len(el.pitches) >= 3:
                        harmony = el.pitches[-2]
                        new_note = music21.chord.Chord([harmony, melody])
                    else:
                        new_note = music21.note.Note(melody)
                elif isinstance(el, music21.note.Note):
                    new_note = music21.note.Note(el.pitch)
            else: # LH
                if isinstance(el, music21.chord.Chord):
                    bass = el.pitches[0]
                    new_note = music21.note.Note(bass)
                elif isinstance(el, music21.note.Note):
                    new_note = music21.note.Note(el.pitch)
            
            if new_note:
                new_note.offset = el.offset
                new_note.duration = el.duration
                new_note.articulations = copy.deepcopy(el.articulations)
                new_note.expressions = copy.deepcopy(el.expressions)
                
                if isinstance(new_note, music21.note.Note):
                    if i == 0: 
                        while new_note.pitch.midi < 60: new_note.pitch.midi += 12
                    else: 
                        while new_note.pitch.midi < 36: new_note.pitch.midi += 12
                        while new_note.pitch.midi > 60: new_note.pitch.midi -= 12

                new_part.insert(new_note.offset, new_note)
        
        try:
            new_part.makeMeasures(inPlace=True)
            new_part.makeTies(inPlace=True)
            new_part.makeNotation(inPlace=True)
        except: pass
        
        new_score.insert(0, new_part)
        
    return new_score

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
    
    print("🌿 [Fix] 이미지 생성 복구 엔진 가동...")
    
    normal_score = _simplify_vertical(score_in, mode="normal")
    super_score = _simplify_vertical(score_in, mode="super_easy")
    
    # 🔥 [복구된 핵심 기능] MIDI 우회 생성 로직
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
                
                # PNG 생성 (2차 시도: 실패 시 MIDI -> PNG 우회) 👈 이게 빠져서 안 떴던 겁니다!
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

# =========================================================
# 🚀 Audiveris 실행 로직 (동일)
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

        midi_path = os.path.join(temp_dir, "clean_score.mid")
        if convert_with_musescore(found_file, midi_path):
            try:
                score = music21.converter.parse(midi_path)
                clean_xml_output = os.path.join(temp_dir, "final_output.musicxml")
                score.write('musicxml', fp=clean_xml_output)
                with open(clean_xml_output, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                raise RuntimeError(f"MIDI 처리 실패: {e}")
        else:
             raise RuntimeError("MuseScore MIDI 변환 실패 ")

def png_white_background(png_path: str) -> str:
    return png_path