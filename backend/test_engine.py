# test_engine.py

import ai_engine  # 👈 우리가 만든 '엔진룸' 임포트
import time

# --- 테스트 설정 ---
TEST_IMAGE_FILE = "ex.png"  # 👈 1. 준비한 악보 이미지 파일 이름
# --------------------

def test_1st_engine():
    print(f"--- 1차 엔진(Audiveris) 테스트 시작 ---")
    print(f"테스트 파일: {TEST_IMAGE_FILE}")
    
    try:
        # 1. 테스트용 이미지를 바이트로 읽기
        with open(TEST_IMAGE_FILE, "rb") as f:
            image_bytes = f.read()
            
        print("이미지 파일 로드 성공.")

        # 2. 'run_audiveris' 함수 호출!
        start_time = time.time()
        music_xml = ai_engine.run_audiveris(image_bytes)
        end_time = time.time()

        print(f"\n--- ✅ 테스트 성공! (소요 시간: {end_time - start_time:.2f}초) ---")
        
        # 3. 결과 확인 (MusicXML 텍스트의 앞 500자만 출력)
        print("생성된 MusicXML (앞부분 500자):")
        print(music_xml[:500] + "...")
        
        # 4. 결과 파일로도 저장 (확인용)
        with open("TEST_OUTPUT.musicxml", "w", encoding="utf-8") as f:
            f.write(music_xml)
        print("\n(결과 전체를 'TEST_OUTPUT.musicxml' 파일로 저장했습니다.)")

    except FileNotFoundError:
        print(f"\n--- ❌ 테스트 실패 ---")
        print(f"오류: 테스트 이미지 파일({TEST_IMAGE_FILE})을 찾을 수 없습니다.")
        print("ai_engine.py와 같은 폴더에 악보 이미지를 넣어주세요.")
        
    except Exception as e:
        print(f"\n--- ❌ 테스트 실패 ---")
        print(f"오류 발생: {e}")

# --- 스크립트 실행 ---
if __name__ == "__main__":
    test_1st_engine()