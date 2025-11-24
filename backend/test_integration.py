# test_integration.py
import ai_engine
import base64
import os
import time

# 테스트할 이미지 파일 이름 (고화질 파일!)
TEST_IMAGE = "ex.png"

def run_full_process():
    print(f"🚀 [통합 테스트 시작] 파일: {TEST_IMAGE}")
    
    # 1. 이미지 읽기
    if not os.path.exists(TEST_IMAGE):
        print("❌ 에러: 테스트 이미지가 없습니다.")
        return

    with open(TEST_IMAGE, "rb") as f:
        image_bytes = f.read()

    try:
        # ==========================================
        # 1단계: 1차 엔진 (Audiveris) - OMR 수행
        # ==========================================
        start_time = time.time()
        print("\n--- 1단계: 악보 인식 (Audiveris) 진행 중... ---")
        music_xml_content = ai_engine.run_audiveris(image_bytes)
        print(f"✅ 1단계 성공! (MusicXML 추출 완료, 길이: {len(music_xml_content)}자)")

        # ==========================================
        # 2단계: 2/3차 엔진 (music21) - 단순화 및 생성
        # ==========================================
        print("\n--- 2단계: 악보 단순화 및 파일 생성 (music21) 진행 중... ---")
        result_files = ai_engine.simplify_and_generate(music_xml_content)
        
        end_time = time.time()
        print(f"✅ 2단계 성공! (총 소요 시간: {end_time - start_time:.2f}초)")
        
        # ==========================================
        # 3단계: 결과물 저장 (눈으로 확인하기 위해)
        # ==========================================
        print("\n--- 3단계: 결과 파일 저장 중... ---")
        
        # 3-1. MIDI 파일 저장 (소리)
        midi_b64 = result_files.get("simplified_midi_base64")
        if midi_b64:
            with open("RESULT_simple.mid", "wb") as f:
                f.write(base64.b64decode(midi_b64))
            print("🎹 MIDI 파일 저장 완료: RESULT_simple.mid (들어서 확인해보세요!)")
        else:
            print("⚠️ MIDI 파일이 생성되지 않았습니다.")

        # 3-2. PNG 파일 저장 (이미지)
        png_b64 = result_files.get("simplified_image_base64")
        if png_b64:
            with open("RESULT_simple.png", "wb") as f:
                f.write(base64.b64decode(png_b64))
            print("🖼️ PNG 파일 저장 완료: RESULT_simple.png (열어서 확인해보세요!)")
        else:
            print("⚠️ PNG 파일이 생성되지 않았습니다. (MuseScore 설정이 필요할 수 있음)")
            print("   -> 하지만 MIDI가 나왔다면 로직은 성공한 것입니다!")

    except Exception as e:
        print(f"\n❌ 통합 테스트 실패: {e}")

if __name__ == "__main__":
    run_full_process()