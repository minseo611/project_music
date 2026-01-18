# backend/ai_engine.py
# =========================================================
# EasyScore 2.0 - [최종 통합] 화질개선 + 시각화보정 + 경로호환성 완벽 적용
# =========================================================

import subprocess
import music21
import os
import tempfile
import base64
import platform
import shutil
import io
from typing import Optional, List
from PIL import Image, ImageEnhance, ImageFilter

# =========================================================
# 🕵️ OS 자동 감지 및 경로 설정 (동료 코드 반영)
# =========================================================

CURRENT_OS = platform.system()
IS_WINDOWS = CURRENT_OS == "Windows"
IS_MAC = CURRENT_OS == "Darwin"

print(f"🖥️ 현재 운영체제 감지: {CURRENT_OS}")

# 🔥 [동료 코드 반영] Windows 사용자를 위한 강제 경로 지정
# Mac에서는 이 경로가 없으므로 무시됩니다 (에러 안 남)
USER_MUSESCORE_PATH = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"

def find_musescore() -> str:
    """OS에 따라 MuseScore 실행 파일을 찾습니다. (통합 버전)"""
    
    # 1. [동료 코드] 강제 지정 경로 확인 (Windows용)
    if IS_WINDOWS and USER_MUSESCORE_PATH and os.path.exists(USER_MUSESCORE_PATH):
        print(f"✅ MuseScore Studio 찾음 (강제 지정): {USER_MUSESCORE_PATH}")
        return USER_MUSESCORE_PATH

    # 2. 통합 검색 경로 (Windows 'Studio' 버전 + Mac 포함)
    search_paths = []
    
    if IS_WINDOWS:
        search_paths = [
            r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe",
            r"C:\Program Files (x86)\MuseScore 4\bin\MuseScore4.exe",
            r"C:\Program Files\MuseScore Studio 4\bin\MuseScore4.exe", # 동료가 수정한 부분
            r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe",
        ]
    elif IS_MAC:
        search_paths = [
            '/Applications/MuseScore 4.app/Contents/MacOS/mscore',
            '/Applications/MuseScore Studio 4.app/Contents/MacOS/mscore', # Mac도 Studio 이름 가능성 대비
            '/Applications/MuseScore 3.app/Contents/MacOS/mscore'
        ]

    for path in search_paths:
        if os.path.exists(path):
            print(f"✅ MuseScore 발견: {path}")
            return path
            
    # 3. 시스템 명령어 확인
    cmd = "MuseScore4" if IS_WINDOWS else "mscore"
    if shutil.which(cmd): return shutil.which(cmd)

    print("⚠️ MuseScore를 찾을 수 없습니다.")
    return ""

def find_audiveris_info() -> dict:
    if IS_WINDOWS:
        search_roots = [
            r"C:\Program Files\Audiveris",
            r"C:\Program Files (x86)\Audiveris",
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
# 🖼️ 이미지 전처리 (내 코드 기능 - 정확도 향상)
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
# 🚀 Audiveris OMR 실행 (내 코드 기능 - 압축 파일 처리)
# =========================================================
def run_audiveris(image_bytes: bytes) -> str:
    with tempfile.TemporaryDirectory() as temp_dir:
        input_image_path = os.path.join(temp_dir, "input.png")
        
        # 전처리 이미지 저장
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
            "-batch", 
            "-output", temp_dir, 
            "-export",
            input_image_path
        ]
        
        try:
            subprocess.run(
                command, check=True, timeout=180, 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                shell=IS_WINDOWS 
            )
        except Exception as e:
            raise RuntimeError(f"Audiveris 실행 실패: {e}")

        found_file = None
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".musicxml") or file.endswith(".mxl"):
                    found_file = os.path.join(root, file)
                    break
            if found_file: break

        if not found_file: raise RuntimeError("변환된 악보 없음")

        try:
            score = music21.converter.parse(found_file)
            clean_xml_path = os.path.join(temp_dir, "clean_output.musicxml")
            score.write('musicxml', fp=clean_xml_path)
            
            with open(clean_xml_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"❌ 파일 파싱 에러: {e}")
            raise RuntimeError("악보 파일 파싱 중 오류가 발생했습니다.")


# =========================================================
# 🎨 이미지/악보 처리 유틸
# =========================================================

def render_png_with_musescore(xml_path: str) -> str:
    ms_path = find_musescore()
    if not ms_path: return ""
    base, _ = os.path.splitext(xml_path)
    out_path = base + ".png"
    try:
        subprocess.run([ms_path, "-o", out_path, xml_path], check=True, timeout=60, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=IS_WINDOWS)
    except: pass
    
    if os.path.exists(out_path): return out_path
    if os.path.exists(f"{base}-1.png"): return f"{base}-1.png"
    return ""

def png_white_background(png_path: str) -> str:
    if not png_path or not os.path.exists(png_path): return ""
    try:
        img = Image.open(png_path).convert("RGBA")
        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        merged = Image.alpha_composite(white, img).convert("RGB")
        out_path = png_path.replace(".png", "_white.png")
        merged.save(out_path, "PNG")
        return out_path
    except: return png_path

def _choose_time_signature(score, mode):
    ts_list = score.recurse().getElementsByClass(music21.meter.TimeSignature)
    ts = ts_list[0] if ts_list else None
    if ts is None: return music21.meter.TimeSignature("4/4")
    if mode == "super_easy":
        if ts.denominator == 8 and ts.numerator in [6, 9, 12]:
            return music21.meter.TimeSignature("4/4")
    return music21.meter.TimeSignature(ts.ratioString)

def _quantize_duration(q, grid, min_q, max_q):
    if q is None: return 1.0
    val = max(min_q, min(max_q, float(q)))
    return min(grid, key=lambda g: abs(g - val))

def _clamp_midi(m, lo, hi):
    return max(lo, min(hi, m))

def _build_score_feel_preserving(score_in, mode: str):
    """
    [내 코드 기능] 시각적 보정(MakeMeasures) 포함
    """
    ts = _choose_time_signature(score_in, mode)
    rh = music21.stream.Part()
    lh = music21.stream.Part()
    
    rh.insert(0, music21.clef.TrebleClef())
    rh.insert(0, ts)
    lh.insert(0, music21.clef.BassClef())
    
    flat_notes = score_in.flat.notes
    for el in flat_notes:
        off = el.offset
        dur = el.duration.quarterLength
        
        if mode == "super_easy":
            dur = _quantize_duration(dur, [1.0, 2.0, 4.0], 1.0, 4.0)
            off = round(off) 
        else:
            dur = _quantize_duration(dur, [0.5, 1.0, 2.0, 4.0], 0.5, 4.0)
            off = round(off * 2) / 2 
            
        new_n = None
        if isinstance(el, music21.chord.Chord):
            if el.pitches: new_n = music21.note.Note(el.pitches[-1]) 
        elif isinstance(el, music21.note.Note):
            new_n = music21.note.Note(el.pitch)
            
        if new_n:
            new_n.duration.quarterLength = dur
            new_n.pitch.midi = _clamp_midi(new_n.pitch.midi, 48, 84) 
            rh.insert(off, new_n)
            
            if mode == "easy" and int(off) % 2 == 0:
                bass_n = new_n.transpose('-P8') 
                bass_n.duration.quarterLength = 2.0
                lh.insert(off, bass_n)

    # ✅ 시각적 보정 (마디 나누기) - 여기가 악보 예쁘게 나오는 핵심!
    out_score = music21.stream.Score()
    for p in [rh, lh]:
        if not p.flat.notes: continue 
        p.makeMeasures(inPlace=True)
        p.makeTies(inPlace=True)
        p.makeNotation(inPlace=True)
        out_score.insert(0, p)
        
    return out_score

def simplify_and_generate(music_xml_content: str) -> dict:
    setup_music21()
    
    if isinstance(music_xml_content, bytes):
        try:
            music_xml_content = music_xml_content.decode('utf-8')
        except:
            music_xml_content = music_xml_content.decode('latin-1')

    score_in = music21.converter.parse(music_xml_content, format="musicxml")
    
    easy_score = _build_score_feel_preserving(score_in, mode="easy")
    super_score = _build_score_feel_preserving(score_in, mode="super_easy")
    
    def _to_midi(sc):
        try:
            fp = sc.write("midi")
            with open(fp, "rb") as f: return base64.b64encode(f.read()).decode()
        except: return None
        
    def _to_png(sc):
        try:
            with tempfile.TemporaryDirectory() as temp:
                xml = os.path.join(temp, "temp.musicxml")
                sc.write("musicxml", xml) 
                
                png = render_png_with_musescore(xml)
                png_white = png_white_background(png)
                
                if png_white:
                    with open(png_white, "rb") as f: return base64.b64encode(f.read()).decode()
        except Exception as e: 
            print(f"PNG 생성 실패: {e}")
            pass
        return None

    out = {}
    out["easy_midi_base64"] = _to_midi(easy_score)
    out["easy_image_base64"] = _to_png(easy_score)
    out["super_easy_midi_base64"] = _to_midi(super_score)
    out["super_easy_image_base64"] = _to_png(super_score)
    
    out["simplified_midi_base64"] = out["easy_midi_base64"]
    out["simplified_image_base64"] = out["easy_image_base64"]
    
    return out