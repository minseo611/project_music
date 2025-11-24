# ai_engine.py
# -----------------------------------------------------
# Audiveris & music21 백엔드 엔진 (Final Version)
# -----------------------------------------------------

import subprocess  # 1차 엔진(Audiveris) 실행용
import music21     # 2/3차 엔진(음악 처리)용
import os
import tempfile    # 임시 파일/폴더 관리용
import base64      # 결과 파일을 텍스트로 인코딩하기 위함

# =================================================================
# 롤 1: OMR & 인프라 엔지니어 담당 영역 (Audiveris)
# =================================================================
def run_audiveris(image_bytes: bytes) -> str:
    """
    1차 엔진: Audiveris를 실행하여 이미지로부터 MusicXML을 추출
    
    :param image_bytes: 업로드된 이미지의 원본 바이트
    :return: 생성된 MusicXML 파일의 '내용' (텍스트)
    """
    
    # 1. Audiveris가 파일을 읽고 출력할 임시 작업 공간(폴더) 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        input_image_path = os.path.join(temp_dir, "input_image.png")
        
        # 2. 업로드된 이미지 바이트를 임시 파일로 저장
        with open(input_image_path, "wb") as f:
            f.write(image_bytes)
            
        # 3. Audiveris 실행 명령어 정의 (macOS .app 기준)
        app_folder = "/Applications/Audiveris.app/Contents/app"
        
        # Classpath: 메인 jar와 그 폴더의 모든 라이브러리 로드
        classpath = f"{app_folder}/audiveris.jar:{app_folder}/*"
        
        # 진짜 메인 클래스
        main_class = "org.audiveris.omr.Main"
        
        command = [
            "java",
            "-cp", classpath,           # 모든 부품 로드
            main_class,                 # 메인 클래스 실행
            "-batch",                   # UI 없이 실행
            "-output", temp_dir,        # 출력 폴더 지정
            "-export",                  # 내보내기 활성화
            input_image_path            # 입력 파일 (맨 뒤에!)
        ]
        
        print(f"Audiveris 실행 (최대 120초): {' '.join(command)}")

        try:
            # 4. Audiveris 실행
            result = subprocess.run(
                command, 
                check=True, 
                timeout=120, 
                capture_output=True, 
                text=True
            )
            print("Audiveris OMR 성공.")
            # 로그가 너무 길 수 있으니 앞부분만 출력
            print(f"STDOUT 일부: {result.stdout[:200]}...") 

        except subprocess.CalledProcessError as e:
            error_message = f"\n--- STDOUT ---\n{e.stdout}\n--- STDERR ---\n{e.stderr}"
            print(f"Audiveris 실행 실패. 오류:{error_message}")
            raise Exception(f"Audiveris OMR 실패: {error_message}")
        except subprocess.TimeoutExpired as e:
            print(f"Audiveris 처리 시간 초과: {e}")
            raise Exception("Audiveris 처리 시간 초과 (120초)")

        # 5. [수정됨] 결과물 찾기 (탐정 모드 🕵️)
        # Audiveris는 하위 폴더를 만들거나 확장자를 .mxl로 바꿀 수 있습니다.
        # 따라서 폴더 전체를 뒤져서 악보 파일을 찾아냅니다.
        
        found_file_path = None
        print(f"DEBUG: 결과 파일 검색 중... (위치: {temp_dir})")
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".musicxml") or file.endswith(".mxl"):
                    found_file_path = os.path.join(root, file)
                    print(f"DEBUG: 악보 파일 발견! -> {file}")
                    break
            if found_file_path:
                break

        if not found_file_path:
            raise Exception(f"악보 파일을 찾을 수 없습니다. Audiveris 로그를 확인하세요.")

        # 6. [수정됨] MusicXML 내용 읽기
        # .mxl은 압축 파일이라 그냥 open()으로 못 읽습니다.
        # music21을 이용해서 안전하게 내용을 텍스트로 변환합니다.
        try:
            print("DEBUG: music21로 파일 변환 및 읽기 시도...")
            c = music21.converter.parse(found_file_path)
            
            # 임시 XML 파일로 다시 써서 순수 텍스트를 얻음
            temp_xml = os.path.join(temp_dir, "converted_final.musicxml")
            c.write('musicxml', fp=temp_xml)
            
            with open(temp_xml, "r", encoding="utf-8") as f:
                music_xml_content = f.read()
                
        except Exception as e:
            raise Exception(f"파일 읽기 변환 실패: {e}")
            
        return music_xml_content


# =================================================================
# 롤 2: 음악 알고리즘 엔지니어 담당 영역 (music21)
# =================================================================
def simplify_and_generate(music_xml_content: str) -> dict:
    """
    2/3차 엔진: MusicXML을 '단순화'하고 '새 파일(MIDI/PNG)'로 생성
    """
    
    # 1. MusicXML 텍스트 파싱
    try:
        score = music21.converter.parse(music_xml_content, format='musicxml')
    except Exception as e:
        print(f"MusicXML 파싱 실패: {e}")
        raise Exception(f"music21 파싱 실패: {e}")

    # 2. 단순화 알고리즘 (핵심 로직)
    print("단순화 알고리즘 실행...")
    simplified_score = music21.stream.Score(id='simplified')
    main_part = music21.stream.Part(id='main')
    
    for element in score.flatten().notesAndRests:
        new_element = None
        
        if element.isChord:
            # 화음 -> 가장 높은 음, 4분음표
            highest_pitch = element.pitches[-1]
            new_element = music21.note.Note(highest_pitch)
            new_element.duration.quarterLength = 1.0 
        elif element.isNote:
            # 단일 음 -> 4분음표
            new_element = music21.note.Note(element.pitch)
            new_element.duration.quarterLength = 1.0
            
        if new_element:
            main_part.append(new_element)

    simplified_score.insert(0, main_part)

    # 3. 파일 생성 (MIDI & PNG)
    output_files = {}
    
    # 3-1. MIDI 생성
    try:
        midi_fp = simplified_score.write('midi')
        with open(midi_fp, 'rb') as f:
            output_files["simplified_midi_base64"] = base64.b64encode(f.read()).decode('utf-8')
        os.remove(midi_fp)
        print("MIDI 생성 성공.")
    except Exception as e:
        print(f"MIDI 생성 실패: {e}")
        output_files["simplified_midi_base64"] = None

    # 3-2. PNG 생성 (MuseScore 필요 - 없으면 실패 로그만 남기고 통과)
    try:
        png_fp = simplified_score.write('musicxml.png')
        with open(png_fp, 'rb') as f:
            output_files["simplified_image_base64"] = base64.b64encode(f.read()).decode('utf-8')
        os.remove(png_fp)
        print("PNG 생성 성공.")
    except Exception as e:
        print(f"PNG 생성 실패 (MuseScore 미설치 등): {e}")
        output_files["simplified_image_base64"] = None

    return output_files