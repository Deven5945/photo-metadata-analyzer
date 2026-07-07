# photo-metadata-analyzer
사진 메타데이터 분석기 (Python + CustomTkinter)

이 프로젝트는 이미지의 공통 EXIF 메타데이터를 읽어 보여주는 간단한 데스크톱 앱입니다. 
학습용으로 유지보수하기 쉬운 구조를 우선하며, GUI와 메타데이터 처리 로직을 분리해 두었습니다.

## 기능
- 이미지 파일 선택
- 기본 이미지 정보 표시(파일명, 크기, 포맷)
- 공통 EXIF 필드 표시
- 메타데이터가 없는 이미지에 대한 graceful 처리

## 필요 패키지
- `customtkinter`
- `Pillow`
- `piexif`
- `exifread`

## 설치
```bash
python -m pip install -r requirements.txt
```

## 실행
```bash
python main.py
```

## 테스트
```bash
python -m unittest discover -s tests -v
```
