# test_music21.py
import music21

def test_music21_parsing():
    print("--- 2단계: music21 파싱 테스트 시작 ---")

    # 1. 가상의 MusicXML 데이터 (Audiveris가 성공했다고 가정하고 만든 샘플)
    # (도-레-미-파 4분음표 멜로디입니다)
    dummy_musicxml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1">
      <part-name>Music</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
"""
    print("1. 샘플 MusicXML 데이터 준비 완료.")

    try:
        # 2. music21로 데이터 읽어들이기 (Parsing)
        print("2. music21로 데이터 해석 중...")
        score = music21.converter.parse(dummy_musicxml, format='musicxml')
        
        print("\n✅ 파싱 성공! 악보 내용을 분석합니다:")
        print("-" * 30)

        # 3. 분석 결과 출력 (음표 하나하나 꺼내보기)
        # 악보 안의 모든 요소를 평평하게(flatten) 펼쳐서 음표(Note)만 찾습니다.
        notes = score.flatten().notes
        
        for i, element in enumerate(notes):
            if element.isNote:
                print(f"  [음표 {i+1}] 계이름: {element.nameWithOctave}, 길이: {element.duration.type}")
            elif element.isChord:
                print(f"  [화음 {i+1}] 구성음: {element.pitches}, 길이: {element.duration.type}")
        
        print("-" * 30)
        print("--- ✅ 2단계 테스트 완료! music21이 정상 작동합니다. ---")

    except Exception as e:
        print(f"\n--- ❌ 테스트 실패 ---")
        print(f"music21 오류 발생: {e}")
        print("pip3 install music21 명령어로 라이브러리가 설치되었는지 확인하세요.")

if __name__ == "__main__":
    test_music21_parsing()